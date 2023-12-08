from os.path import isfile, join

import inspect
import re
import requests
import subprocess
from ovos_bus_client.message import Message, dig_for_message
from ovos_bus_client.session import SessionManager
from ovos_config import Configuration
from ovos_config.locations import get_xdg_cache_save_path
from ovos_utils import classproperty
from ovos_utils import resolve_resource_file
from ovos_utils.enclosure.api import EnclosureAPI
from ovos_utils.file_utils import get_cache_directory
from ovos_utils.lang.visimes import VISIMES
from ovos_utils.log import LOG, deprecated
from ovos_utils.messagebus import FakeBus as BUS
from ovos_utils.metrics import Stopwatch
from ovos_utils.process_utils import RuntimeRequirements
from pathlib import Path
from queue import Queue
from threading import Thread

from ovos_plugin_manager.g2p import OVOSG2PFactory, find_g2p_plugins
from ovos_plugin_manager.templates.g2p import OutOfVocabulary
from ovos_plugin_manager.utils.config import get_plugin_config
from ovos_plugin_manager.utils.tts_cache import TextToSpeechCache, hash_sentence

EMPTY_PLAYBACK_QUEUE_TUPLE = (None, None, None, None, None)
SSML_TAGS = re.compile(r'<[^>]*>')


class TTSContext:
    _caches = {}

    def __init__(self, plugin_id: str, lang: str, voice: str):
        self.plugin_id = plugin_id
        self.lang = lang
        self.voice = voice

    @property
    def tts_id(self):
        return join(self.plugin_id, self.voice, self.lang)

    def get_cache(self, audio_ext="wav", cache_config=None):
        cache_config = cache_config or {
            "min_free_percent": 75,
            "persist_cache": False,
            "persist_thresh": 1,
            "preloaded_cache": f"{get_xdg_cache_save_path()}/{self.tts_id}"
        }
        if self.tts_id not in TTSContext._caches:
            TTSContext._caches[self.tts_id] = TextToSpeechCache(
                cache_config, self.tts_id, audio_ext
            )
        return self._caches[self.tts_id]

    def get_from_cache(self, sentence, audio_ext="wav", cache_config=None):
        sentence_hash = hash_sentence(sentence)
        phonemes = None
        cache = self.get_cache(audio_ext, cache_config)
        if sentence_hash not in cache:
            raise FileNotFoundError(f"sentence is not cached, {sentence_hash}.{audio_ext}")
        audio_file, pho_file = cache.cached_sentences[sentence_hash]
        LOG.info(f"Found {audio_file.name} in TTS cache")
        if pho_file:
            phonemes = pho_file.load()
        return audio_file, phonemes


class TTS:
    """TTS abstract class to be implemented by all TTS engines.

    It aggregates the minimum required parameters and exposes
    ``execute(sentence)`` and ``validate_ssml(sentence)`` functions.

    Arguments:
        lang (str):
        config (dict): Configuration for this specific tts engine
        validator (TTSValidator): Used to verify proper installation
        phonetic_spelling (bool): Whether to spell certain words phonetically
        ssml_tags (list): Supported ssml properties. Ex. ['speak', 'prosody']
    """
    queue = None
    playback = None

    def __init__(self, lang=None, config=None, validator=None,
                 audio_ext='wav', phonetic_spelling=True, ssml_tags=None):
        self.log_timestamps = False

        self.config = config or get_plugin_config(config, "tts")

        self.stopwatch = Stopwatch()
        self.tts_name = self.__class__.__name__
        self.bus = BUS()  # initialized in "init" step
        if lang:
            self.lang = lang

        self.validator = validator or TTSValidator(self)
        self.phonetic_spelling = phonetic_spelling
        self.audio_ext = audio_ext
        self.ssml_tags = ssml_tags or []
        self.log_timestamps = self.config.get("log_timestamps", False)

        self.enable_cache = self.config.get("enable_cache", True)

        if TTS.queue is None:
            TTS.queue = Queue()

        self.spellings = self.load_spellings()
        self._init_g2p()

        self.add_metric({"metric_type": "tts.init"})

    # methods for individual plugins to override
    @classproperty
    def runtime_requirements(self):
        """ skill developers should override this if they do not require connectivity
         some examples:
         IOT plugin that controls devices via LAN could return:
            scans_on_init = True
            RuntimeRequirements(internet_before_load=False,
                                 network_before_load=scans_on_init,
                                 requires_internet=False,
                                 requires_network=True,
                                 no_internet_fallback=True,
                                 no_network_fallback=False)
         online search plugin with a local cache:
            has_cache = False
            RuntimeRequirements(internet_before_load=not has_cache,
                                 network_before_load=not has_cache,
                                 requires_internet=True,
                                 requires_network=True,
                                 no_internet_fallback=True,
                                 no_network_fallback=True)
         a fully offline plugin:
            RuntimeRequirements(internet_before_load=False,
                                 network_before_load=False,
                                 requires_internet=False,
                                 requires_network=False,
                                 no_internet_fallback=True,
                                 no_network_fallback=True)
        """
        return RuntimeRequirements()

    @property
    def available_languages(self) -> set:
        """Return languages supported by this TTS implementation in this state
        This property should be overridden by the derived class to advertise
        what languages that engine supports.
        Returns:
            set: supported languages
        """
        return set()

    def get_tts(self, sentence, wav_file, lang=None):
        """Abstract method that a tts implementation needs to implement.

        Should get data from tts.

        Arguments:
            sentence(str): Sentence to synthesize
            wav_file(str): output file
            lang(str): requested language (optional), defaults to self.lang

        Returns:
            tuple: (wav_file, phoneme)
        """
        return "", None

    def get_voice(self, gender, lang=None):
        """ map a language and gender to a valid voice for this TTS engine """
        lang = lang or self.lang
        return gender

    def _preprocess_sentence(self, sentence):
        """Default preprocessing is no preprocessing.

        This method can be overridden to create chunks suitable to the
        TTS engine in question.

        Arguments:
            sentence (str): sentence to preprocess

        Returns:
            list: list of sentence parts
        """
        # TODO - make public
        return [sentence]

    def modify_tag(self, tag):
        """Override to modify each supported ssml tag.

        Arguments:
            tag (str): SSML tag to check and possibly transform.
        """
        return tag

    def handle_metric(self, metadata=None):
        """ receive timing metrics for diagnostics
        does nothing by default but plugins might use it, eg, NeonCore"""

    # properties that reflect live config changes
    @property
    def voice(self):
        return self.config.get("voice") or "default"

    @voice.setter
    def voice(self, val):
        self.config["voice"] = val

    @property
    def lang(self):
        return self.config.get("lang") or 'en-us'

    @lang.setter
    def lang(self, val):
        self.config["lang"] = val

    # SSML helpers
    @staticmethod
    def remove_ssml(text):
        """Removes SSML tags from a string.

        Arguments:
            text (str): input string

        Returns:
            str: input string stripped from tags.
        """
        return re.sub('<[^>]*>', '', text).replace('  ', ' ')

    @staticmethod
    def format_speak_tags(sentence: str, include_tags: bool = True) -> str:
        """
        Cleans up SSML tags for speech synthesis and ensures the phrase is
        wrapped in 'speak' tags and any excluded text is
        removed.
        Args:
            sentence: Input sentence to be spoken
            include_tags: Flag to include <speak> tags in returned string
        Returns:
            Cleaned sentence to pass to TTS
        """
        # Wrap sentence in speak tag if no tags present
        if "<speak>" not in sentence and "</speak>" not in sentence:
            to_speak = f"<speak>{sentence}</speak>"
        # Assume speak starts at the beginning of the sentence
        elif "<speak>" not in sentence:
            to_speak = f"<speak>{sentence}"
        # Assume speak ends at the end of the sentence
        elif "</speak>" not in sentence:
            to_speak = f"{sentence}</speak>"
        else:
            to_speak = sentence

        # Trim text outside of speak tags
        if not to_speak.startswith("<speak>"):
            to_speak = f"<speak>{to_speak.split('<speak>', 1)[1]}"

        if not to_speak.endswith("</speak>"):
            to_speak = f"{to_speak.split('</speak>', 1)[0]}</speak>"

        if to_speak == "<speak></speak>":
            return ""

        if include_tags:
            return to_speak
        else:
            return to_speak.lstrip("<speak>").rstrip("</speak>")

    def validate_ssml(self, utterance):
        """Check if engine supports ssml, if not remove all tags.

        Remove unsupported / invalid tags

        Arguments:
            utterance (str): Sentence to validate

        Returns:
            str: validated_sentence
        """

        # Validate speak tags
        if not self.ssml_tags or "speak" not in self.ssml_tags:
            self.format_speak_tags(utterance, False)
        elif self.ssml_tags and "speak" in self.ssml_tags:
            self.format_speak_tags(utterance)

        # if ssml is not supported by TTS engine remove all tags
        if not self.ssml_tags:
            return self.remove_ssml(utterance)

        # find ssml tags in string
        tags = SSML_TAGS.findall(utterance)

        for tag in tags:
            if any(supported in tag for supported in self.ssml_tags):
                utterance = utterance.replace(tag, self.modify_tag(tag))
            else:
                # remove unsupported tag
                utterance = utterance.replace(tag, "")

        # return text with supported ssml tags only
        return utterance.replace("  ", " ")

    # init helpers
    def _init_g2p(self):
        cfg = Configuration()
        g2pm = self.config.get("g2p_module")
        if g2pm:
            if g2pm in find_g2p_plugins():
                cfg.setdefault("g2p", {})
                globl = cfg["g2p"].get("module") or g2pm
                if globl != g2pm:
                    LOG.info(f"TTS requested {g2pm} explicitly, ignoring global module {globl} ")
                cfg["g2p"]["module"] = g2pm
            else:
                LOG.warning(f"TTS selected {g2pm}, but it is not available!")

        try:
            self.g2p = OVOSG2PFactory.create(cfg)
        except:
            LOG.debug("G2P plugin not loaded, there will be no mouth movements")
            self.g2p = None

    def init(self, bus=None, playback=None):
        """ Performs intial setup of TTS object.

        Arguments:
            bus:    OpenVoiceOS messagebus connection
        """
        self.bus = bus or BUS()
        if playback is None:
            LOG.warning("PlaybackThread should be inited by ovos-audio, initing via plugin has been deprecated, "
                        "please pass playback=PlaybackThread() to TTS.init")
            if TTS.playback:
                playback.shutdown()
            playback = PlaybackThread(TTS.queue, self.bus)  # compat
            playback.start()
        self._init_playback(playback)
        self.add_metric({"metric_type": "tts.setup"})

    def _init_playback(self, playback):
        TTS.playback = playback
        TTS.playback.set_bus(self.bus)
        TTS.playback.attach_tts(self)
        if not TTS.playback.enclosure:
            TTS.playback.enclosure = EnclosureAPI(self.bus)

        if not TTS.playback.is_running:
            TTS.playback.start()

    def load_spellings(self, config=None):
        """Load phonetic spellings of words as dictionary."""
        path = join('text', self.lang.lower(), 'phonetic_spellings.txt')
        try:
            spellings_file = resolve_resource_file(path, config=config or Configuration())
        except:
            LOG.debug('Failed to locate phonetic spellings resource file.')
            return {}
        if not spellings_file:
            return {}
        try:
            with open(spellings_file) as f:
                lines = filter(bool, f.read().split('\n'))
            lines = [i.split(':') for i in lines]
            return {key.strip(): value.strip() for key, value in lines}
        except ValueError:
            LOG.exception('Failed to load phonetic spellings.')
            return {}

    ## execution events
    def add_metric(self, metadata=None):
        """ wraps handle_metric to catch exceptions and log timestamps """
        try:
            self.handle_metric(metadata)
            if self.log_timestamps:
                LOG.debug(f"time delta: {self.stopwatch.delta} metric: {metadata}")
        except Exception as e:
            LOG.exception(e)

    def begin_audio(self):
        """Helper function for child classes to call in execute()"""
        self.add_metric({"metric_type": "tts.start"})

    def end_audio(self, listen=False):
        """Helper cleanup function for child classes to call in execute().

        Arguments:
            listen (bool): DEPRECATED: indication if listening trigger should be sent.
        """
        self.add_metric({"metric_type": "tts.end"})
        self.stopwatch.stop()

    def execute(self, sentence, ident=None, listen=False, **kwargs):
        """Convert sentence to speech, preprocessing out unsupported ssml

        The method caches results if possible using the hash of the
        sentence.

        Arguments:
            sentence: (str) Sentence to be spoken
            ident: (str) session_id from Message
            listen: (bool) True if listen should be triggered at the end
                    of the utterance.
        """
        sentence = self.validate_ssml(sentence)
        self.add_metric({"metric_type": "tts.ssml.validated"})
        self._execute(sentence, ident, listen, **kwargs)

    ## synth
    def _replace_phonetic_spellings(self, sentence):
        if self.phonetic_spelling:
            for word in re.findall(r"[\w']+", sentence):
                if word.lower() in self.spellings:
                    spelled = self.spellings[word.lower()]
                    sentence = sentence.replace(word, spelled)
        return sentence

    def _get_visemes(self, phonemes, sentence, ctxt):
        # get visemes/mouth movements
        viseme = []
        if phonemes:
            viseme = self.viseme(phonemes)
        elif self.g2p is not None:
            try:
                viseme = self.g2p.utterance2visemes(sentence, ctxt.lang)
            except OutOfVocabulary:
                pass
            except:
                # this one is unplanned, let devs know all the info so they can fix it
                LOG.exception(f"Unexpected failure in G2P plugin: {self.g2p}")

        if not viseme:
            # Debug level because this is expected in default installs
            LOG.debug(f"no mouth movements available! unknown visemes for {sentence}")
        return viseme

    def _get_ctxt(self, kwargs):
        # get request specific synth params
        message = kwargs.get("message") or dig_for_message()
        lang = kwargs.get("lang")
        voice = kwargs.get("voice")
        if message:
            sess = SessionManager.get(message)
            lang = lang or sess.lang
            voice = voice or sess.tts_preferences["config"].get("voice")
        return TTSContext(plugin_id=self.tts_name,  # TODO this should be the OPM name at some point
                          lang=lang or self.lang,
                          voice=voice or self.voice)

    def _execute(self, sentence, ident, listen, **kwargs):
        self.stopwatch.start()  # start timing metrics

        # pre-process
        sentence = self._replace_phonetic_spellings(sentence)
        chunks = self._preprocess_sentence(sentence)
        # Apply the listen flag to the last chunk, set the rest to False
        chunks = [(chunks[i], listen if i == len(chunks) - 1 else False)
                  for i in range(len(chunks))]

        # metrics timing callback
        self.add_metric({"metric_type": "tts.preprocessed",
                         "n_chunks": len(chunks)})

        # get request specific synth params
        ctxt = self._get_ctxt(kwargs)

        message = kwargs.get("message") or \
                  dig_for_message() or \
                  Message("speak", context={"session": {"session_id": ident}})

        # synth -> queue for playback
        for sentence, l in chunks:
            # load from cache or synth + cache
            audio_file, phonemes = self.synth(sentence, ctxt, **kwargs)

            # get visemes/mouth movements
            viseme = self._get_visemes(phonemes, sentence, ctxt)

            # queue audio for playback
            TTS.queue.put(
                (str(audio_file), viseme, l, ctxt.tts_id, message)
            )

            # metrics timing callback
            self.add_metric({"metric_type": "tts.queued"})

    def synth(self, sentence, ctxt: TTSContext = None, **kwargs):
        """ This method wraps get_tts
        several optional keyword arguments are supported
        sentence will be read/saved to cache"""
        self.add_metric({"metric_type": "tts.synth.start"})
        sentence_hash = hash_sentence(sentence)

        # parse requested language for this TTS request

        ctxt = ctxt or self._get_ctxt(kwargs)
        cache = ctxt.get_cache(self.audio_ext, self.config)

        # load from cache
        if self.enable_cache and sentence_hash in cache:
            audio, phonemes = ctxt.get_from_cache(sentence, cache)
            self.add_metric({"metric_type": "tts.synth.finished", "cache": True})
            return audio, phonemes

        # synth + cache
        audio = cache.define_audio_file(sentence_hash)

        # filter kwargs per plugin, different plugins expose different options
        #   ovos -> lang + voice optional kwargs
        #   neon-core -> message
        kwargs = {k: v for k, v in kwargs.items()
                  if k in inspect.signature(self.get_tts).parameters
                  and k not in ["sentence", "wav_file"]}

        # finally do the TTS synth
        audio.path, phonemes = self.get_tts(sentence, str(audio), **kwargs)
        self.add_metric({"metric_type": "tts.synth.finished"})

        # cache sentence + phonemes
        if self.enable_cache:
            self._cache_sentence(sentence, audio, cache,
                                 phonemes, sentence_hash)
        return audio, phonemes

    def viseme(self, phonemes):
        """Create visemes from phonemes.

        May be implemented to convert TTS phonemes into OpenVoiceOS mouth
        visuals.

        Arguments:
            phonemes (str): String with phoneme data

        Returns:
            list: visemes
        """
        visimes = []
        if phonemes:
            phones = str(phonemes).split(" ")
            for pair in phones:
                if ":" in pair:
                    pho_dur = pair.split(":")  # phoneme:duration
                    if len(pho_dur) == 2:
                        visimes.append((VISIMES.get(pho_dur[0], '4'),
                                        float(pho_dur[1])))
                else:
                    visimes.append((VISIMES.get(pair, '4'),
                                    float(0.2)))
        return visimes or None

    ## cache
    def _cache_phonemes(self, sentence, cache: TextToSpeechCache = None, phonemes=None, sentence_hash=None):
        sentence_hash = sentence_hash or hash_sentence(sentence)
        if not phonemes and self.g2p is not None:
            try:
                phonemes = self.g2p.utterance2arpa(sentence, self.lang)
                self.add_metric({"metric_type": "tts.phonemes.g2p"})
            except Exception as e:
                self.add_metric({"metric_type": "tts.phonemes.g2p.error", "error": str(e)})
        if phonemes:
            phoneme_file = cache.define_phoneme_file(sentence_hash)
            phoneme_file.save(phonemes)
            return phoneme_file
        return None

    def _cache_sentence(self, sentence, audio_file, cache, phonemes=None, sentence_hash=None):
        sentence_hash = sentence_hash or hash_sentence(sentence)
        # RANT: why do you hate strings ChrisV?
        if isinstance(audio_file.path, str):
            audio_file.path = Path(audio_file.path)
        pho_file = self._cache_phonemes(sentence, cache, phonemes, sentence_hash)
        cache.cached_sentences[sentence_hash] = (audio_file, pho_file)
        self.add_metric({"metric_type": "tts.synth.cached"})

    ## shutdown
    def stop(self):
        if TTS.playback:
            try:
                TTS.playback.stop()
            except Exception as e:
                pass
        self.add_metric({"metric_type": "tts.stop"})

    def shutdown(self):
        self.stop()
        if TTS.playback:
            TTS.playback.detach_tts(self)

    def __del__(self):
        self.shutdown()

    # below code is all deprecated and marked for removal in next stable release
    # TODO - update version number in warnings
    @property
    @deprecated("self.enclosure has been deprecated, use EnclosureAPI directly decoupled from the plugin code",
                "0.1.0")
    def enclosure(self):
        if not TTS.playback.enclosure:
            bus = TTS.playback.bus or self.bus
            TTS.playback.enclosure = EnclosureAPI(bus)
        return TTS.playback.enclosure

    @enclosure.setter
    @deprecated("self.enclosure has been deprecated, use EnclosureAPI directly decoupled from the plugin code",
                "0.1.0")
    def enclosure(self, val):
        TTS.playback.enclosure = val

    @property
    @deprecated("self.filename has been deprecated, unused for a long time now",
                "0.1.0")
    def filename(self):
        cache_dir = get_cache_directory(self.tts_name)
        return join(cache_dir, 'tts.' + self.audio_ext)

    @filename.setter
    @deprecated("self.filename has been deprecated, unused for a long time now",
                "0.1.0")
    def filename(self, val):
        pass

    @property
    @deprecated("self.tts_id has been deprecated, use TTSContext().tts_id",
                "0.1.0")
    def tts_id(self):
        return TTSContext().tts_id

    @property
    @deprecated("self.cache has been deprecated, use TTSContext().get_cache",
                "0.1.0")
    def cache(self):
        return TTSContext._caches.get(self.tts_id) or \
            self.get_cache()

    @cache.setter
    @deprecated("self.cache has been deprecated, use TTSContext().get_cache",
                "0.1.0")
    def cache(self, val):
        TTSContext._caches[self.tts_id] = val

    @deprecated("get_cache has been deprecated, use TTSContext().get_cache directly",
                "0.1.0")
    def get_cache(self, voice=None, lang=None):
        return TTSContext().get_cache(self.audio_ext, self.config)

    @deprecated("clear_cache has been deprecated, use TTSContext().get_cache directly",
                "0.1.0")
    def clear_cache(self):
        """ Remove all cached files. """
        cache = TTSContext().get_cache(self.audio_ext, self.config)
        cache.clear()

    @deprecated("save_phonemes has been deprecated, use TTSContext().get_cache directly",
                "0.1.0")
    def save_phonemes(self, key, phonemes):
        """Cache phonemes

        Arguments:
            key (str):        Hash key for the sentence
            phonemes (str):   phoneme string to save
        """
        cache = TTSContext().get_cache(self.audio_ext, self.config)
        phoneme_file = cache.define_phoneme_file(key)
        phoneme_file.save(phonemes)
        return phoneme_file

    @deprecated("load_phonemes has been deprecated, use TTSContext().get_cache directly",
                "0.1.0")
    def load_phonemes(self, key):
        """Load phonemes from cache file.

        Arguments:
            key (str): Key identifying phoneme cache
        """
        cache = TTSContext().get_cache(self.audio_ext, self.config)
        phoneme_file = cache.define_phoneme_file(key)
        return phoneme_file.load()

    @deprecated("get_from_cache has been deprecated, use TTSContext().get_from_cache directly",
                "0.1.0")
    def get_from_cache(self, sentence):
        return TTSContext().get_from_cache(sentence, self.audio_ext, self.config)


class TTSValidator:
    """TTS Validator abstract class to be implemented by all TTS engines.

    It exposes and implements ``validate(tts)`` function as a template to
    validate the TTS engines.
    """

    def __init__(self, tts):
        self.tts = tts

    def validate(self):
        self.validate_dependencies()
        self.validate_instance()
        self.validate_filename()
        self.validate_lang()
        self.validate_connection()

    def validate_dependencies(self):
        """Determine if all the TTS's external dependencies are satisfied."""
        pass

    def validate_instance(self):
        pass

    def validate_filename(self):
        pass

    def validate_lang(self):
        """Ensure the TTS supports current language."""

    def validate_connection(self):
        """Ensure the TTS can connect to it's backend.

        This can mean for example being able to launch the correct executable
        or contact a webserver.
        """

    def get_tts_class(self):
        """Return TTS class that this validator is for."""


class ConcatTTS(TTS):
    def __init__(self, *args, **kwargs):
        super(ConcatTTS, self).__init__(*args, **kwargs)
        self.time_step = float(self.config.get("time_step", 0.1))
        if self.time_step < 0.1:
            self.time_step = 0.1
        self.sound_files_path = self.config.get("sounds")
        self.channels = self.config.get("channels", "1")
        self.rate = self.config.get("rate", "16000")

    def sentence_to_files(self, sentence):
        """ list of ordered files to concatenate and form final wav file
        return files (list) , phonemes (list)
        """
        raise NotImplementedError

    def concat(self, files, wav_file):
        """ generate output wav file from input files """
        cmd = ["sox"]
        for file in files:
            if not isfile(file):
                continue
            cmd.append("-c")
            cmd.append(self.channels)
            cmd.append("-r")
            cmd.append(self.rate)
            cmd.append(file)

        cmd.append(wav_file)
        cmd.append("channels")
        cmd.append(self.channels)
        cmd.append("rate")
        cmd.append(self.rate)
        LOG.info(subprocess.check_output(cmd))
        return wav_file

    def get_tts(self, sentence, wav_file, lang=None):
        """
            get data from tts.

            Args:
                sentence(str): Sentence to synthesize
                wav_file(str): output file

            Returns:
                tuple: (wav_file, phoneme)
        """
        files, phonemes = self.sentence_to_files(sentence)
        wav_file = self.concat(files, wav_file)
        return wav_file, phonemes


class RemoteTTSException(Exception):
    pass


class RemoteTTSTimeoutException(RemoteTTSException):
    pass


# below classes are deprecated and will be removed in 0.1.0

class RemoteTTS(TTS):
    """
    Abstract class for a Remote TTS engine implementation.
    This class is only provided for backwards compatibility
    Usage is discouraged
    """

    @deprecated("RemoteTTS has been deprecated, please use the regular TTS class",
                "0.1.0")
    def __init__(self, lang, config, url, api_path, validator):
        super(RemoteTTS, self).__init__(lang, config, validator)
        self.api_path = api_path
        self.auth = None
        self.url = config.get('url', url).rstrip('/')

    def build_request_params(self, sentence):
        pass

    def get_tts(self, sentence, wav_file, lang=None):
        r = requests.get(
            self.url + self.api_path, params=self.build_request_params(sentence),
            timeout=10, verify=False, auth=self.auth)
        if r.status_code != 200:
            return None
        with open(wav_file, 'wb') as f:
            f.write(r.content)
        return wav_file, None


class PlaybackThread(Thread):
    """ PlaybackThread moved to ovos_audio.playback
    standalone plugin usage should rely on self.get_tts
    ovos-audio relies on self.execute and needs this class

    this class was only in ovos-plugin-manager in order to
    patch usage of our plugins in mycroft-core"""

    def __new__(self, *args, **kwargs):
        LOG.warning("PlaybackThread moved to ovos_audio.playback")
        try:
            from ovos_audio.playback import PlaybackThread
            return PlaybackThread(*args, **kwargs)
        except ImportError:
            raise ImportError("please install ovos-audio for playback handling")
