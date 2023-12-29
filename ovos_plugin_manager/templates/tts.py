"""
this module is meant to enable usage of mycroft plugins inside and outside
mycroft, importing from here will make things work as planned in mycroft,
but if outside mycroft things will still work

The main use case is for plugins to be used across different projects

## Differences from upstream

TTS:
- added automatic guessing of phonemes/visime calculation, enabling mouth
movements for all TTS engines (only mimic implements this in upstream)
- playback start call has been omitted and moved to init method
- init is called by mycroft, but non mycroft usage wont call it
- outside mycroft the enclosure is not set, bus is dummy and playback thread is not used
    - playback queue is not wanted when some module is calling get_tts
    - if playback was started on init then python scripts would never stop
        from mycroft.tts import TTSFactory
        engine = TTSFactory.create()
        engine.get_tts("hello world", "hello_world." + engine.audio_ext)
        # would hang here
        engine.playback.stop()
"""
import inspect
import random
import re
import subprocess
from os.path import isfile, join
from pathlib import Path
from queue import Queue
from threading import Thread
import requests
from ovos_bus_client.message import Message, dig_for_message
from ovos_config import Configuration
from ovos_plugin_manager.g2p import OVOSG2PFactory, find_g2p_plugins
from ovos_plugin_manager.templates.g2p import OutOfVocabulary
from ovos_plugin_manager.utils.config import get_plugin_config
from ovos_plugin_manager.utils.tts_cache import TextToSpeechCache, hash_sentence
from ovos_utils import classproperty
from ovos_utils.file_utils import resolve_resource_file
from ovos_bus_client.apis.enclosure import EnclosureAPI
from ovos_utils.file_utils import get_cache_directory
from ovos_utils.lang.visimes import VISIMES
from ovos_utils.log import LOG
from ovos_utils.messagebus import FakeBus as BUS
from ovos_utils.metrics import Stopwatch
from ovos_utils.process_utils import RuntimeRequirements

EMPTY_PLAYBACK_QUEUE_TUPLE = (None, None, None, None, None)
SSML_TAGS = re.compile(r'<[^>]*>')


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


class TTSContext:
    """ parses kwargs for valid signatures and extracts voice/lang optional parameters
    it will look for a requested voice in kwargs and inside the source Message data if available.
    voice can also be defined by a combination of language and gender,
    in that case the helper method get_voice will be used to resolve the final voice_id
    """

    def __init__(self, engine):
        self.engine = engine

    def get_message(self, kwargs):
        msg = kwargs.get("message") or dig_for_message()
        if msg and isinstance(msg, Message):
            return msg

    def get_lang(self, kwargs):
        # parse requested language for this TTS request
        # NOTE: this is ovos only functionality, not in mycroft-core!
        lang = kwargs.get("lang")
        message = self.get_message(kwargs)
        if not lang and message:
            # get lang from message object if possible
            lang = message.data.get("lang") or \
                   message.context.get("lang")
        return lang or self.engine.lang

    def get_gender(self, kwargs):
        gender = kwargs.get("gender")
        message = self.get_message(kwargs)
        if not gender and message:
            # get gender from message object if possible
            gender = message.data.get("gender") or \
                     message.context.get("gender")
        return gender

    def get_voice(self, kwargs):
        # parse requested voice for this TTS request
        # NOTE: this is ovos only functionality, not in mycroft-core!
        voice = kwargs.get("voice")
        message = self.get_message(kwargs)
        if not voice and message:
            # get voice from message object if possible
            voice = message.data.get("voice") or \
                    message.context.get("voice")

        if not voice:
            gender = self.get_gender(kwargs)
            if gender:
                lang = self.get_lang(kwargs)
                voice = self.engine.get_voice(gender, lang)

        return voice or self.engine.voice

    def get(self, kwargs=None):
        kwargs = kwargs or {}
        return self.get_lang(kwargs), self.get_voice(kwargs)

    def get_cache(self, kwargs=None):
        lang, voice = self.get(kwargs)
        return self.engine.get_cache(voice, lang)


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

    def __init__(self, lang="en-us", config=None, validator=None,
                 audio_ext='wav', phonetic_spelling=True, ssml_tags=None):
        self.log_timestamps = False

        self.config = config or get_plugin_config(config, "tts")

        self.stopwatch = Stopwatch()
        self.tts_name = self.__class__.__name__
        self.bus = BUS()  # initialized in "init" step
        self.lang = lang or self.config.get("lang") or 'en-us'
        self.validator = validator or TTSValidator(self)
        self.phonetic_spelling = phonetic_spelling
        self.audio_ext = audio_ext
        self.ssml_tags = ssml_tags or []
        self.log_timestamps = self.config.get("log_timestamps", False)

        self.enable_cache = self.config.get("enable_cache", True)

        self.voice = self.config.get("voice") or "default"
        # TODO can self.filename be deprecated ? is it used anywhere at all?
        cache_dir = get_cache_directory(self.tts_name)
        self.filename = join(cache_dir, 'tts.' + self.audio_ext)

        random.seed()

        if TTS.queue is None:
            TTS.queue = Queue()

        self.context = TTSContext(self)

        # NOTE: self.playback.start() was moved to init method
        #   playback queue is not wanted if we only care about get_tts
        #   init is called by mycroft, but non mycroft usage wont call it,
        #   outside mycroft the enclosure is not set, bus is dummy and
        #   playback thread is not used
        self.spellings = self.load_spellings()

        self.caches = {
            self.tts_id: TextToSpeechCache(
                self.config, self.tts_id, self.audio_ext
            )}

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
            LOG.exception("G2P plugin not loaded, there will be no mouth movements")
            self.g2p = None

        self.cache.curate()

        self.add_metric({"metric_type": "tts.init"})

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
    def tts_id(self):
        lang, voice = self.context.get()
        return join(self.tts_name, voice, lang)

    @property
    def cache(self):
        return self.caches.get(self.tts_id) or \
            self.get_cache()

    @cache.setter
    def cache(self, val):
        self.caches[self.tts_id] = val

    def get_cache(self, voice=None, lang=None):
        lang = lang or self.lang
        voice = voice or self.voice or "default"
        tts_id = join(self.tts_name, voice, lang)
        if tts_id not in self.caches:
            self.caches[tts_id] = TextToSpeechCache(
                self.config, tts_id, self.audio_ext
            )
        return self.caches[tts_id]

    def handle_metric(self, metadata=None):
        """ receive timing metrics for diagnostics
        does nothing by default but plugins might use it, eg, NeonCore"""

    def add_metric(self, metadata=None):
        """ wraps handle_metric to catch exceptions and log timestamps """
        try:
            self.handle_metric(metadata)
            if self.log_timestamps:
                LOG.debug(f"time delta: {self.stopwatch.delta} metric: {metadata}")
        except Exception as e:
            LOG.exception(e)

    def load_spellings(self, config=None):
        """Load phonetic spellings of words as dictionary."""
        path = join('text', self.lang.lower(), 'phonetic_spellings.txt')
        try:
            spellings_file = resolve_resource_file(path, config=config or Configuration())
        except:
            LOG.debug('Failed to locate phonetic spellings resouce file.')
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

    @property
    def enclosure(self):
        if not TTS.playback.enclosure:
            bus = TTS.playback.bus or self.bus
            TTS.playback.enclosure = EnclosureAPI(bus)
        return TTS.playback.enclosure

    @enclosure.setter
    def enclosure(self, val):
        TTS.playback.enclosure = val

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

    def modify_tag(self, tag):
        """Override to modify each supported ssml tag.

        Arguments:
            tag (str): SSML tag to check and possibly transform.
        """
        return tag

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

    def _preprocess_sentence(self, sentence):
        """Default preprocessing is no preprocessing.

        This method can be overridden to create chunks suitable to the
        TTS engine in question.

        Arguments:
            sentence (str): sentence to preprocess

        Returns:
            list: list of sentence parts
        """
        return [sentence]

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

    def _replace_phonetic_spellings(self, sentence):
        if self.phonetic_spelling:
            for word in re.findall(r"[\w']+", sentence):
                if word.lower() in self.spellings:
                    spelled = self.spellings[word.lower()]
                    sentence = sentence.replace(word, spelled)
        return sentence

    def _execute(self, sentence, ident, listen, **kwargs):
        self.stopwatch.start()
        sentence = self._replace_phonetic_spellings(sentence)
        chunks = self._preprocess_sentence(sentence)
        # Apply the listen flag to the last chunk, set the rest to False
        chunks = [(chunks[i], listen if i == len(chunks) - 1 else False)
                  for i in range(len(chunks))]
        self.add_metric({"metric_type": "tts.preprocessed",
                         "n_chunks": len(chunks)})

        lang, voice = self.context.get(kwargs)
        tts_id = join(self.tts_name, voice, lang)

        # synth -> queue for playback
        for sentence, l in chunks:
            # load from cache or synth + cache
            audio_file, phonemes = self.synth(sentence, **kwargs)

            # get visemes/mouth movements
            viseme = []
            if phonemes:
                viseme = self.viseme(phonemes)
            elif self.g2p is not None:
                try:
                    viseme = self.g2p.utterance2visemes(sentence, lang)
                except OutOfVocabulary:
                    pass
                except:
                    # this one is unplanned, let devs know all the info so they can fix it
                    LOG.exception(f"Unexpected failure in G2P plugin: {self.g2p}")

            if not viseme:
                # Debug level because this is expected in default installs
                LOG.debug(f"no mouth movements available! unknown visemes for {sentence}")

            message = kwargs.get("message") or \
                      dig_for_message() or \
                      Message("speak", context={"session": {"session_id": ident}})
            TTS.queue.put(
                (str(audio_file), viseme, l, tts_id, message)
            )
            self.add_metric({"metric_type": "tts.queued"})

    def synth(self, sentence, **kwargs):
        """ This method wraps get_tts
        several optional keyword arguments are supported
        sentence will be read/saved to cache"""
        self.add_metric({"metric_type": "tts.synth.start"})
        sentence_hash = hash_sentence(sentence)

        # parse requested language for this TTS request
        # NOTE: this is ovos/neon only functionality, not in mycroft-core!
        lang, voice = self.context.get(kwargs)
        kwargs["lang"] = lang
        kwargs["voice"] = voice

        cache = self.get_cache(voice, lang)  # cache per tts_id (lang/voice combo)

        # load from cache
        if self.enable_cache and sentence_hash in cache:
            audio, phonemes = self.get_from_cache(sentence, **kwargs)
            self.add_metric({"metric_type": "tts.synth.finished", "cache": True})
            return audio, phonemes

        # synth + cache
        audio = cache.define_audio_file(sentence_hash)

        # filter kwargs per plugin, different plugins expose different options
        #   mycroft-core -> no kwargs
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
            self._cache_sentence(sentence, audio, phonemes, sentence_hash,
                                 voice=voice, lang=lang)
        return audio, phonemes

    def _cache_phonemes(self, sentence, phonemes=None, sentence_hash=None):
        sentence_hash = sentence_hash or hash_sentence(sentence)
        if not phonemes and self.g2p is not None:
            try:
                phonemes = self.g2p.utterance2arpa(sentence, self.lang)
                self.add_metric({"metric_type": "tts.phonemes.g2p"})
            except Exception as e:
                self.add_metric({"metric_type": "tts.phonemes.g2p.error", "error": str(e)})
        if phonemes:
            return self.save_phonemes(sentence_hash, phonemes)
        return None

    def _cache_sentence(self, sentence, audio_file, phonemes=None, sentence_hash=None,
                        voice=None, lang=None):
        sentence_hash = sentence_hash or hash_sentence(sentence)
        # RANT: why do you hate strings ChrisV?
        if isinstance(audio_file.path, str):
            audio_file.path = Path(audio_file.path)
        pho_file = self._cache_phonemes(sentence, phonemes, sentence_hash)
        cache = self.get_cache(voice=voice, lang=lang)
        cache.cached_sentences[sentence_hash] = (audio_file, pho_file)
        self.add_metric({"metric_type": "tts.synth.cached"})

    def get_from_cache(self, sentence, **kwargs):
        sentence_hash = hash_sentence(sentence)
        phonemes = None
        cache = self.context.get_cache(kwargs)
        audio_file, pho_file = cache.cached_sentences[sentence_hash]
        LOG.info(f"Found {audio_file.name} in TTS cache")
        if not pho_file:
            # guess phonemes from sentence + cache them
            pho_file = self._cache_phonemes(sentence, sentence_hash)
        if pho_file:
            phonemes = pho_file.load()
        return audio_file, phonemes

    def get_voice(self, gender, lang=None):
        """ map a language and gender to a valid voice for this TTS engine """
        lang = lang or self.lang
        return gender

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

    def clear_cache(self):
        """ Remove all cached files. """
        self.cache.clear()

    def save_phonemes(self, key, phonemes):
        """Cache phonemes

        Arguments:
            key (str):        Hash key for the sentence
            phonemes (str):   phoneme string to save
        """
        phoneme_file = self.cache.define_phoneme_file(key)
        phoneme_file.save(phonemes)
        return phoneme_file

    def load_phonemes(self, key):
        """Load phonemes from cache file.

        Arguments:
            key (str): Key identifying phoneme cache
        """
        phoneme_file = self.cache.define_phoneme_file(key)
        return phoneme_file.load()

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

    @property
    def available_languages(self) -> set:
        """Return languages supported by this TTS implementation in this state
        This property should be overridden by the derived class to advertise
        what languages that engine supports.
        Returns:
            set: supported languages
        """
        return set()


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


class RemoteTTS(TTS):
    """
    Abstract class for a Remote TTS engine implementation.
    This class is only provided for backwards compatibility
    Usage is discouraged
    """

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
