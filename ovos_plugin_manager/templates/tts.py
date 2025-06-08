import abc
import asyncio
import inspect
import os.path
import re
import shutil
import subprocess
import sys
from os.path import isfile, join
from pathlib import Path
from queue import Queue
from typing import AsyncIterable, List, Dict, Set

import quebra_frases
from ovos_bus_client.apis.enclosure import EnclosureAPI
from ovos_bus_client.message import Message, dig_for_message
from ovos_bus_client.session import SessionManager
from ovos_plugin_manager.utils.tts_cache import TextToSpeechCache, hash_sentence
from ovos_utils import classproperty
from ovos_utils.fakebus import FakeBus
from ovos_utils.lang import standardize_lang_tag
from ovos_utils.lang.visimes import VISIMES
from ovos_utils.log import LOG
from ovos_utils.metrics import Stopwatch
from ovos_utils.process_utils import RuntimeRequirements

from ovos_config import Configuration
from ovos_config.locations import get_xdg_cache_save_path

EMPTY_PLAYBACK_QUEUE_TUPLE = (None, None, None, None, None)
SSML_TAGS = re.compile(r'<[^>]*>')


class TTSContext:
    """
    A context manager for handling Text-To-Speech (TTS) operations and caching.

    Attributes:
        plugin_id (str): Identifier for the TTS plugin being used.
        lang (str): Language code for the TTS operation.
        voice (str): Identifier for the voice type in use.
        synth_kwargs (dict): Optional dictionary containing additional keyword arguments for the TTS synthesizer.

    Class Attributes:
        _caches (dict): A class-level dictionary acting as a cache store for different TTS contexts.
    """

    _caches: Dict[str, TextToSpeechCache] = {}

    def __init__(self, plugin_id: str, lang: str, voice: str, synth_kwargs: dict = None):
        """
        Initializes the TTSContext instance.

        Parameters:
            plugin_id (str): The unique identifier for the TTS plugin.
            lang (str): The language in which the text will be synthesized.
            voice (str): The voice model to be used for text synthesis.
            synth_kwargs (dict, optional): Additional keyword arguments for the synthesizer.
        """
        self.plugin_id = plugin_id
        self.lang = standardize_lang_tag(lang)
        self.voice = voice
        self.synth_kwargs = synth_kwargs or {}

    @property
    def tts_id(self):
        """
        Constructs a unique identifier for the TTS context based on plugin, voice, and language.

        Returns:
            str: A unique identifier that represents the TTS context.
        """
        return join(self.plugin_id, self.voice, self.lang).strip("/")

    def get_cache(self, audio_ext="wav", cache_config=None):
        """
        Retrieves or creates a cache instance for the current TTS context.

        Parameters:
            audio_ext (str, optional): The file extension for the audio files (default is 'wav').
            cache_config (dict, optional): Configuration settings for the cache, including parameters like
                                          minimum free percent, persistence settings, and cache directory path.

        Returns:
            TextToSpeechCache: The cache instance associated with the current TTS context.
        """
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
        """
        Retrieves an audio file and phoneme data from the cache, based on the input sentence.

        Parameters:
            sentence (str): The sentence for which to retrieve audio data.
            audio_ext (str, optional): The file extension of the audio file (default is 'wav').
            cache_config (dict, optional): Configuration settings for the cache.

        Returns:
            tuple: A tuple containing the path to the cached audio file and optionally the phoneme data.

        Raises:
            FileNotFoundError: If the sentence is not found in the cache.
        """
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

    @classmethod
    def curate_caches(cls):
        for cache in TTSContext._caches.values():
            cache.curate()


class TTS:
    """TTS abstract class to be implemented by all TTS engines.

    It aggregates the minimum required parameters and exposes
    ``execute(sentence)`` and ``validate_ssml(sentence)`` functions.

    Attributes:
        queue (Queue): A queue for managing TTS playback tasks.
        playback (PlaybackThread): The playback thread used for TTS audio output.

    Args:
        lang (str): The language code for the TTS engine.
        config (dict): Configuration settings for the specific TTS engine.
        validator (TTSValidator): Validator used to verify proper installation.
        audio_ext (str): The default audio file extension (default is 'wav').
        phonetic_spelling (bool): Whether to spell certain words phonetically.
        ssml_tags (list): Supported SSML properties (e.g., ['speak', 'prosody']).
    """
    queue = None
    playback = None

    def __init__(self, config=None, validator=None,
                 audio_ext='wav', phonetic_spelling=True, ssml_tags=None):
        """
        Initializes the TTS engine with specified parameters.

        Args:
            config (dict): Configuration settings for the TTS engine.
            validator (TTSValidator): Validator for verifying installation.
            audio_ext (str): Default audio file extension (default is 'wav').
            phonetic_spelling (bool): Whether to use phonetic spelling (default is True).
            ssml_tags (list): Supported SSML tags (default is None).
        """
        self.log_timestamps = False
        self.root_dir = os.path.dirname(os.path.abspath(sys.modules[self.__module__].__file__))
        self.config = config or {}

        self.stopwatch = Stopwatch()
        self.tts_name = self.__class__.__name__

        self.validator = validator or TTSValidator(self)
        self.phonetic_spelling = phonetic_spelling
        self.audio_ext = audio_ext
        self.ssml_tags = ssml_tags or []
        self.log_timestamps = self.config.get("log_timestamps", False)

        self.enable_cache = self.config.get("enable_cache", True)

        if TTS.queue is None:
            TTS.queue = Queue()

        self.spellings: Dict[str, dict] = self.load_spellings()
        self.add_metric({"metric_type": "tts.init"})

        # unused by plugins, assigned in init method by ovos-audio,
        # only present for backwards compat reasons
        self.bus = None

        self._plugin_id = ""  # the plugin name
        self._lang = None

    @property
    def lang(self):
        return standardize_lang_tag(self._lang or \
                                    self.config.get("lang") or \
                                    SessionManager.get().lang)
    @lang.setter
    def lang(self, val):
        # backwards compat
        self._lang = standardize_lang_tag(val)

    @property
    def plugin_id(self) -> str:
        """
        Retrieves the plugin ID for the TTS engine.

        Returns:
            str: The plugin ID associated with the TTS engine.
        """
        if not self._plugin_id:
            from ovos_plugin_manager.tts import find_tts_plugins
            for tts_id, clazz in find_tts_plugins().items():
                if isinstance(self, clazz):
                    self._plugin_id = tts_id
                    break
        return self._plugin_id

    # methods for individual plugins to override
    @classproperty
    def runtime_requirements(self):
        """ WIP - currently unused,
        placeholder to allow plugins to request internet/gui before load
        refer to skills to see how it is used"""
        return RuntimeRequirements()

    @classproperty
    @abc.abstractmethod
    def available_languages(cls) -> Set[str]:
        """Return languages supported by this TTS implementation in this state
        This property should be overridden by the derived class to advertise
        what languages that engine supports.
        Returns:
            set: A set of supported language codes.
        """

    @abc.abstractmethod
    def get_tts(self, sentence, wav_file, lang=None, voice=None):
        """Abstract method that a tts implementation needs to implement.

        Args:
            sentence (str): The input sentence to synthesize.
            wav_file (str): The output file path for the synthesized audio.
            lang (str, optional): The requested language (defaults to self.lang).
            voice (str, optional): The requested voice (defaults to self.voice).

        Returns:
            tuple: (wav_file, phoneme)
        """
        return "", None

    def preprocess_sentence(self, sentence: str) -> List[str]:
        """Default preprocessing is a sentence_tokenizer,
        ie. splits the utterance into sub-sentences using quebra_frases

        This method can be overridden to create chunks suitable to the
        TTS engine in question.

        Arguments:
            sentence (str): sentence to preprocess

        Returns:
            list: list of sentence parts
        """
        if self.config.get("sentence_tokenize"):  # TODO default to True on next major release
            return quebra_frases.sentence_tokenize(sentence)
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

    @property
    def voice(self):
        return self.config.get("voice") or "default"

    @voice.setter
    def voice(self, val):
        self.config["voice"] = val

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
    def init(self, bus, playback):
        """ Connects TTS object to PlaybackQueue in ovos-audio.

        This method needs to be called in order for self.execute to do anything

        not needed if using get_tts / synth  methods directly as intended in standalone usage

        Arguments:
            bus:    OpenVoiceOS messagebus connection
        """
        self.bus = bus or FakeBus()
        if playback is None:
            raise ValueError("PlaybackThread should be inited by ovos-audio, "
                             "please pass playback=PlaybackThread() to TTS.init")
        self._init_playback(playback)
        self.add_metric({"metric_type": "tts.setup"})

    def _init_playback(self, playback):
        """
        Initializes the playback functionality for the TTS engine.

        Args:
            playback: PlaybackThread instance.
        """

        TTS.playback = playback
        TTS.playback.set_bus(self.bus)
        if not TTS.playback.enclosure:
            TTS.playback.enclosure = EnclosureAPI(self.bus)

        if not TTS.playback.is_alive():
            TTS.playback.start()

    def load_spellings(self, config=None) -> Dict[str, dict]:
        """
        Loads phonetic spellings of words as a dictionary.

        Args:
            config (dict, optional): Configuration settings.

        Returns:
            dict: A dictionary of phonetic spellings.
        """
        if config:
            LOG.warning("config argument is deprecated and unused!")
        spellings_data = {}
        locale = f"{self.root_dir}/locale"
        if os.path.isdir(locale):
            for lang in os.listdir(locale):
                spellings_file = f"{locale}/{lang}/phonetic_spellings.txt"
                if not os.path.isfile(spellings_file):
                    continue
                try:
                    with open(spellings_file) as f:
                        lines = filter(bool, f.read().split('\n'))
                    lines = [i.split(':') for i in lines]
                    spellings_data[lang] = {key.strip(): value.strip() for key, value in lines}
                except ValueError:
                    LOG.exception(f'Failed to load {lang} phonetic spellings.')
        return spellings_data

    ## execution events
    def add_metric(self, metadata=None):
        """
        Wraps handle_metric to catch exceptions and log timestamps.

        Args:
            metadata (dict, optional): Additional metadata for the metric.
        """
        try:
            self.handle_metric(metadata)
            if self.log_timestamps:
                LOG.debug(f"time delta: {self.stopwatch.delta} metric: {metadata}")
        except Exception as e:
            LOG.exception(e)

    def begin_audio(self):
        """Helper function for child classes to call in execute()"""
        self.stopwatch.start()
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
        self.begin_audio()
        sentence = self.validate_ssml(sentence)
        self.add_metric({"metric_type": "tts.ssml.validated"})
        self._execute(sentence, ident, listen, **kwargs)
        self.end_audio()

    ## synth
    def _replace_phonetic_spellings(self, sentence: str, lang: str) -> str:
        # TODO match lang code
        if self.phonetic_spelling and lang in self.spellings:
            for word in re.findall(r"[\w']+", sentence):
                if word.lower() in self.spellings[lang]:
                    spelled = self.spellings[lang][word.lower()]
                    sentence = sentence.replace(word, spelled)
        return sentence

    def _get_visemes(self, phonemes, sentence, ctxt):
        # get visemes/mouth movements
        viseme = []
        if phonemes:
            viseme = self.viseme(phonemes)
        if not viseme:
            # Debug level because this is expected in default installs
            LOG.debug(f"no mouth movements available! unknown visemes for {sentence}")
        return viseme

    def _get_ctxt(self, kwargs=None) -> TTSContext:
        """create a TTSContext from arbitrary kwargs passed to synth/execute methods
        takes lang from Session into account if a message is present
        """
        # get request specific synth params
        kwargs = kwargs or {}
        message = kwargs.get("message") or dig_for_message()

        # update kwargs from session
        if message and "lang" not in kwargs:
            sess = SessionManager.get(message)
            kwargs["lang"] = sess.lang

        # voice from config
        if "voice" not in kwargs:
            kwargs["voice"] = self.voice

        # filter kwargs accepted by this specific plugin
        kwargs = {k: v for k, v in kwargs.items()
                  if k in inspect.signature(self.get_tts).parameters
                  and k not in ["sentence", "wav_file"]}

        LOG.debug(f"TTS kwargs: {kwargs}")
        return TTSContext(plugin_id=self.plugin_id,
                          lang=kwargs.get("lang") or Configuration().get("lang", "en-US"),
                          voice=kwargs.get("voice", "default"),
                          synth_kwargs=kwargs)

    def _execute(self, sentence, ident, listen, preprocess=True, **kwargs):
        # get request specific synth params
        ctxt = self._get_ctxt(kwargs)

        if preprocess:
            # pre-process
            sentence = self._replace_phonetic_spellings(sentence, ctxt.lang)
            chunks = self.preprocess_sentence(sentence)
            # Apply the listen flag to the last chunk, set the rest to False
            chunks = [(chunks[i], listen if i == len(chunks) - 1 else False)
                      for i in range(len(chunks))]

            # metrics timing callback
            self.add_metric({"metric_type": "tts.preprocessed",
                             "n_chunks": len(chunks)})
        else:
            chunks = [(sentence, listen)]

        message = kwargs.get("message") or \
                  dig_for_message() or \
                  Message("speak", context={"session": {"session_id": ident}})

        # synth -> queue for playback
        for sentence, l in chunks:
            # load from cache or synth + cache
            audio_file, phonemes = self.synth(sentence, ctxt)

            # get visemes/mouth movements
            viseme = self._get_visemes(phonemes, sentence, ctxt)

            # queue audio for playback
            TTS.queue.put(
                (str(audio_file), viseme, l, ctxt.tts_id, message)
            )

            # metrics timing callback
            self.add_metric({"metric_type": "tts.queued"})

    def synth(self, sentence, ctxt: TTSContext = None, **kwargs):
        """
        Synthesizes speech for the given sentence. wraps get_tts

        sentence will be read/saved to cache

        Args:
            sentence (str): The sentence to synthesize.
            ctxt (TTSContext): The TTS context.
            **kwargs: Additional synth arguments for get_tts.

        Returns:
            tuple: A tuple containing the path to the synthesized audio file and phoneme data.
        """
        self.add_metric({"metric_type": "tts.synth.start"})
        sentence_hash = hash_sentence(sentence)

        # parse kwargs for this TTS request
        ctxt = ctxt or self._get_ctxt(kwargs)
        cache = ctxt.get_cache(self.audio_ext, self.config)

        # load from cache
        if self.enable_cache and sentence_hash in cache:
            audio, phonemes = ctxt.get_from_cache(sentence, cache)
            self.add_metric({"metric_type": "tts.synth.finished", "cache": True})
            return audio, phonemes

        # synth + cache
        audio = cache.define_audio_file(sentence_hash)
        # ensure cache dir exists
        base_dir = os.path.dirname(str(audio))
        if base_dir:  # handle empty string
            os.makedirs(base_dir, exist_ok=True)
        audio.path, phonemes = self.get_tts(sentence, str(audio),
                                            **ctxt.synth_kwargs)
        self.add_metric({"metric_type": "tts.synth.finished"})

        # cache sentence + phonemes
        if self.enable_cache:
            self._cache_sentence(sentence, ctxt.lang, audio, cache,
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
    def _cache_phonemes(self, sentence, lang: str, cache: TextToSpeechCache = None, phonemes=None, sentence_hash=None):
        """
        Caches phonemes for the given sentence.

        Args:
            sentence (str): The sentence to cache phonemes for.
            cache (TextToSpeechCache): The cache instance.
            phonemes (str, optional): The phonemes for the sentence.
            sentence_hash (str, optional): The hash of the sentence.
        """
        sentence_hash = sentence_hash or hash_sentence(sentence)
        if phonemes:
            phoneme_file = cache.define_phoneme_file(sentence_hash)
            phoneme_file.save(phonemes)
            return phoneme_file
        return None

    def _cache_sentence(self, sentence, lang: str, audio_file, cache, phonemes=None, sentence_hash=None):
        """
        Caches the sentence along with associated audio and phonemes.

        Args:
            sentence (str): The sentence to cache.
            audio_file (AudioFile): The audio file associated with the sentence.
            cache (TextToSpeechCache): The cache instance.
            phonemes (str, optional): The phonemes for the sentence.
            sentence_hash (str, optional): The hash of the sentence.
        """
        sentence_hash = sentence_hash or hash_sentence(sentence)
        # RANT: why do you hate strings ChrisV?
        if isinstance(audio_file.path, str):
            audio_file.path = Path(audio_file.path)
        pho_file = self._cache_phonemes(sentence, lang, cache, phonemes, sentence_hash)
        cache.cached_sentences[sentence_hash] = (audio_file, pho_file)
        self.add_metric({"metric_type": "tts.synth.cached"})

    ## shutdown
    def stop(self):
        """Stops the TTS playback."""
        if TTS.playback:
            try:
                TTS.playback.stop()
            except Exception as e:
                pass
        self.add_metric({"metric_type": "tts.stop"})

    def shutdown(self):
        """Shuts down the TTS engine."""
        self.stop()

    def __del__(self):
        """Destructor for the TTS object."""
        self.shutdown()


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

    @abc.abstractmethod
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


class StreamingTTSCallbacks:
    """handle the playback of streaming TTS, can be overrided in StreamingTTS"""

    def __init__(self, bus, play_args=None, tts_config=None):
        self.bus = bus
        self.config = tts_config or {}
        if not play_args:
            # Check for the best available player depending on the system's audio server.
            # anything that accepts audio via stdin should work
            # TODO - pw-play only outputs high pitched noise, investigate and add it here for pipewire systems
            player = shutil.which("ffplay") or shutil.which("paplay") or shutil.which("aplay")
            if not player:
                raise RuntimeError(
                    "No audio player found (please install 'ffmpeg', 'pulseaudio-utils' or 'alsa-utils').")
            self.play_args = [player]
            if player.endswith("ffplay"):
                self.play_args += ["-autoexit", "-nodisp"]
            self.play_args += ["-"]
        else:
            self.play_args = play_args
        self._process = None

    def stream_start(self, message=None):
        """prepare anything needed to playback streamed audio
        events:
        - "ovos.common_play.duck"
        - "recognizer_loop:audio_output_start"
        """
        LOG.info(f"TTS stream start: {self.__class__.__name__}")
        message = message or dig_for_message() or Message("speak")

        # we don't use the regular PlaybackThread here, we need to handle recognizer_loop:audio_output_start
        if not self.config.get("pulse_duck", False):
            self.bus.emit(message.forward("ovos.common_play.duck"))
        self.bus.emit(message.forward("recognizer_loop:audio_output_start"))

        if self._process:
            self.stream_stop()
        LOG.debug(f"stream playback command: {self.play_args}")
        self._process = subprocess.Popen(self.play_args, stdin=subprocess.PIPE)

    def stream_chunk(self, chunk):
        """Play streamed chunk of audio"""
        LOG.debug(f"TTS stream chunk: {self.__class__.__name__} - {len(chunk)} bytes")
        if self._process:
            self._process.stdin.write(chunk)
            self._process.stdin.flush()

    def stream_stop(self, listen=False, message=None):
        """got all streamed audio, cleanup state
        events:
        - "ovos.common_play.unduck"
        - "recognizer_loop:audio_output_end"
        - 'mycroft.mic.listen'
        """
        LOG.info(f"TTS stream stop: {self.__class__.__name__}")
        message = message or dig_for_message() or Message("speak")

        if self._process:
            self._process.stdin.close()
            self._process.wait()
        self._process = None

        # we don't use the regular PlaybackThread here, we need to handle recognizer_loop:audio_output_end and listen flag
        if not self.config.get("pulse_duck", False):
            self.bus.emit(message.forward("ovos.common_play.unduck"))
        self.bus.emit(message.forward("recognizer_loop:audio_output_end"))
        if listen:
            self.bus.emit(message.forward('mycroft.mic.listen'))


class StreamingTTS(TTS):
    """
    Abstract class for a Streaming TTS engine implementation.
    Audio is streamed in chunks as it becomes available instead of waiting the full sentence to be synthesized

    this plugin can be used in a synchronous way like any other plugin via self.get_tts(sentence, wav_file)

    to play audio as it becomes available use self.generate_audio(sentence, wav_file)

    NOTE: StreamingTTS does not support phonemes
    """

    def init(self, bus=None, playback=None, callbacks=None):
        """ Performs intial setup of TTS object.

        Arguments:
            bus:    OpenVoiceOS messagebus connection
            playback: PlaybackThread
            callbacks: StreamingTTSCallbacks
        """
        super().init(bus, playback)
        self.callbacks = callbacks or StreamingTTSCallbacks(self.bus,
                                                            tts_config=self.config)

    @abc.abstractmethod
    async def stream_tts(self, sentence, **kwargs) -> AsyncIterable[bytes]:
        """yield chunks of TTS audio as they become available"""
        raise NotImplementedError

    async def generate_audio(self, sentence, wav_file, play_streaming=True,
                             listen=False, message=None, plugin_kwargs=None):
        """save streamed TTS to wav file, if configured also play TTS as it becomes available"""
        plugin_kwargs = plugin_kwargs or {}
        if play_streaming:
            self.callbacks.stream_start(message)
        with open(wav_file, "wb") as f:
            try:
                async for chunk in self.stream_tts(sentence, **plugin_kwargs):
                    f.write(chunk)
                    if play_streaming:
                        self.callbacks.stream_chunk(chunk)
            finally:
                if play_streaming:
                    self.callbacks.stream_stop(listen, message)
        return wav_file

    def _execute(self, sentence, ident, listen, **kwargs):

        if not self.config.get("enable_streaming"):
            # by default use the shared Queue for audio playback
            # use streaming only if explicitly enabled until it is better supported
            super()._execute(sentence, ident, listen, **kwargs)
            return

        # parse requested language for this TTS request
        ctxt = self._get_ctxt(kwargs)
        cache = ctxt.get_cache(self.audio_ext, self.config)

        sentence = self._replace_phonetic_spellings(sentence, ctxt.lang)
        self.add_metric({"metric_type": "tts.preprocessed"})

        sentence_hash = hash_sentence(sentence)

        # if cached, play existing file instead
        if self.enable_cache and sentence_hash in cache:
            super()._execute(sentence, ident, listen,
                             preprocess=False, **ctxt.synth_kwargs)
            return

        wav_file = str(cache.define_audio_file(sentence_hash))

        message = kwargs.get("message") or \
                  dig_for_message() or \
                  Message("speak")

        # filter kwargs accepted by this specific plugin
        ctxt.synth_kwargs = {k: v for k, v in kwargs.items()
                             if k in inspect.signature(self.stream_tts).parameters
                             and k not in ["sentence"]}

        # handle streaming TTS
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            self.add_metric({"metric_type": "tts.stream.start"})
            loop.run_until_complete(
                self.generate_audio(sentence, wav_file,
                                    play_streaming=True,
                                    listen=listen,
                                    message=message,
                                    plugin_kwargs=ctxt.synth_kwargs)
            )
        finally:
            loop.close()
            self.add_metric({"metric_type": "tts.stream.end"})

    def get_tts(self, sentence, wav_file, **kwargs):
        """wrap streaming TTS into sync usage"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            wav_file = loop.run_until_complete(
                self.generate_audio(sentence, wav_file,
                                    play_streaming=False,
                                    plugin_kwargs=kwargs)
            )
        finally:
            loop.close()
        return wav_file, None  # No phonemes
