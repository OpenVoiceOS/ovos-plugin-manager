"""
This is here to allow importing this module outside mycroft-core, plugins
using this import instead of mycroft can be used

The main use case is for plugins to be used across different projects
"""
import json
from abc import ABCMeta, abstractmethod
from queue import Queue
from threading import Thread, Event
from typing import List, Tuple, Optional, Set, Union
import warnings
from ovos_config import Configuration
from ovos_utils import classproperty
from ovos_utils.lang import standardize_lang_tag
from ovos_utils.log import deprecated, LOG
from ovos_utils.process_utils import RuntimeRequirements

from ovos_plugin_manager.templates.transformers import AudioLanguageDetector
from ovos_plugin_manager.utils.config import get_plugin_config


class STT(metaclass=ABCMeta):
    """ STT Base class, all  STT backends derives from this one. """

    def __init__(self, config=None):
        self.config_core = Configuration()
        self._lang = None
        self._credential = None
        self._keys = None

        self.config = get_plugin_config(config, "stt")

        self.can_stream = False
        self._recognizer = None
        self._detector = None

    def bind(self, detector: AudioLanguageDetector):
        self._detector = detector
        LOG.debug(f"{self.__class__.__name__} - Assigned lang detector: {detector}")

    def detect_language(self, audio, valid_langs: Optional[Union[Set[str], List[str]]] = None) -> Tuple[str, float]:
        if self._detector is None:
            raise NotImplementedError(f"{self.__class__.__name__} does not support audio language detection")
        return self._detector.detect(audio, valid_langs=valid_langs or self.available_languages)

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
    @deprecated("self.recognizer has been deprecated! "
                "if you need it 'from speech_recognition import Recognizer' directly", "1.0.0")
    def recognizer(self):
        warnings.warn(
            "use 'from speech_recognition import Recognizer' directly",
            DeprecationWarning,
            stacklevel=2,
        )
        # only imported here to not drag dependency
        from speech_recognition import Recognizer
        if not self._recognizer:
            self._recognizer = Recognizer()
        return self._recognizer

    @recognizer.setter
    def recognizer(self, val):
        self._recognizer = val

    @property
    def lang(self):
        return standardize_lang_tag(self._lang or \
                                    self.config.get("lang") or \
                                    Configuration().get("lang", "en-US"))

    @lang.setter
    def lang(self, val):
        # backwards compat
        self._lang = standardize_lang_tag(val)

    @property
    @deprecated("self.keys has been deprecated! "
                "implement config handling directly instead", "1.0.0")
    def keys(self):
        warnings.warn(
            "self.keys has been deprecated",
            DeprecationWarning,
            stacklevel=2,
        )
        return self._keys or self.config_core.get("keys", {})

    @keys.setter
    def keys(self, val):
        # backwards compat
        self._keys = val

    @property
    @deprecated("self.credential has been deprecated! "
                "implement config handling directly instead", "1.0.0")
    def credential(self):
        warnings.warn(
            "self.credential has been deprecated",
            DeprecationWarning,
            stacklevel=2,
        )
        return self._credential or self.config.get("credential", {})

    @credential.setter
    def credential(self, val):
        # backwards compat
        self._credential = val

    @staticmethod
    @deprecated("self.init_language has been deprecated! "
                "implement config handling directly instead", "1.0.0")
    def init_language(config_core):
        warnings.warn(
            "implement config handling directly instead",
            DeprecationWarning,
            stacklevel=2,
        )
        lang = config_core.get("lang", "en-US")
        return standardize_lang_tag(lang, macro=True)

    @abstractmethod
    def execute(self, audio, language: Optional[str] = None) -> str:
        # TODO - eventually deprecate this and make transcribe the @abstractmethod
        pass

    def transcribe(self, audio, lang: Optional[str] = None) -> List[Tuple[str, float]]:
        """transcribe audio data to a list of
        possible transcriptions and respective confidences"""
        if lang is not None and lang == "auto":
            try:
                lang, prob = self.detect_language(audio, self.available_languages)
            except Exception as e:
                LOG.error(f"Language detection failed: {e}. Falling back to default language.")
                lang = self.lang  # Fall back to default language
        return [(self.execute(audio, lang), 1.0)]

    @property
    def available_languages(self) -> Set[str]:
        """Return languages supported by this STT implementation in this state
        This property should be overridden by the derived class to advertise
        what languages that engine supports.
        Returns:
            set: supported languages
        """
        return set()


class TokenSTT(STT, metaclass=ABCMeta):
    @deprecated("TokenSTT is deprecated, please subclass from STT directly", "1.0.0")
    def __init__(self, config=None):
        warnings.warn(
            "please subclass from STT directly",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(config)
        self.token = self.credential.get("token")


class GoogleJsonSTT(STT, metaclass=ABCMeta):
    @deprecated("GoogleJsonSTT is deprecated, please subclass from STT directly", "1.0.0")
    def __init__(self, config=None):
        warnings.warn(
            "please subclass from STT directly",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(config)
        if not self.credential.get("json") or self.keys.get("google_cloud"):
            self.credential["json"] = self.keys["google_cloud"]
        self.json_credentials = json.dumps(self.credential.get("json"))


class BasicSTT(STT, metaclass=ABCMeta):
    @deprecated("BasicSTT is deprecated, please subclass from STT directly", "1.0.0")
    def __init__(self, config=None):
        warnings.warn(
            "please subclass from STT directly",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(config)
        self.username = str(self.credential.get("username"))
        self.password = str(self.credential.get("password"))


class KeySTT(STT, metaclass=ABCMeta):

    @deprecated("KeySTT is deprecated, please subclass from STT directly", "1.0.0")
    def __init__(self, config=None):
        warnings.warn(
            "please subclass from STT directly",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(config)
        self.id = str(self.credential.get("client_id"))
        self.key = str(self.credential.get("client_key"))


class StreamThread(Thread, metaclass=ABCMeta):
    """
        ABC class to be used with StreamingSTT class implementations.
    """

    def __init__(self, queue, language):
        super().__init__()
        self.language = standardize_lang_tag(language)
        self.queue = queue
        self.text = None

    def _get_data(self):
        while True:
            d = self.queue.get()
            if d is None:
                break
            yield d
            self.queue.task_done()

    def run(self):
        return self.handle_audio_stream(self._get_data(), self.language)

    def finalize(self):
        """ return final transcription """
        return self.text

    @abstractmethod
    def handle_audio_stream(self, audio, language):
        pass


class StreamingSTT(STT, metaclass=ABCMeta):
    """
        ABC class for threaded streaming STT implementations.
    """

    def __init__(self, config=None):
        super().__init__(config)
        self.stream = None
        self.can_stream = True
        self.transcript_ready = Event()

    def stream_start(self, language=None):
        self.stream_stop()
        self.queue = Queue()
        self.stream = self.create_streaming_thread()
        self.stream.language = standardize_lang_tag(language or self.lang)
        self.transcript_ready.clear()
        self.stream.start()

    def stream_data(self, data):
        self.queue.put(data)

    def stream_stop(self):
        if self.stream is not None:
            self.queue.put(None)
            text = self.stream.finalize()
            self.stream.join()
            self.stream = None
            self.queue = None
            self.transcript_ready.set()
            return text
        return None

    def execute(self, audio: Optional = None,
                language: Optional[str] = None):
        return self.stream_stop()

    def transcribe(self, audio: Optional = None,
                   lang: Optional[str] = None) -> List[Tuple[str, float]]:
        """transcribe audio data to a list of
        possible transcriptions and respective confidences"""
        return [(self.execute(audio, lang), 1.0)]

    @abstractmethod
    def create_streaming_thread(self):
        pass
