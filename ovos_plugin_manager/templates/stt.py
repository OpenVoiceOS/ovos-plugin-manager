from abc import ABCMeta, abstractmethod
from queue import Queue
from threading import Thread, Event
from typing import List, Tuple, Optional, Set, Union

from ovos_bus_client.session import SessionManager
from ovos_plugin_manager.templates.transformers import AudioLanguageDetector
from ovos_plugin_manager.utils.config import get_plugin_config
from ovos_utils import classproperty
from ovos_utils.lang import standardize_lang_tag
from ovos_utils.log import LOG
from ovos_utils.process_utils import RuntimeRequirements

from ovos_config import Configuration


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
        """
        Detects the language of the provided audio using the bound language detector.
        
        Args:
            audio: The audio data to analyze.
            valid_langs: Optional set or list of language codes to restrict detection.
        
        Returns:
            A tuple containing the detected language code and its confidence score.
        
        Raises:
            NotImplementedError: If no language detector is bound to the instance.
        """
        if self._detector is None:
            raise NotImplementedError(f"{self.__class__.__name__} does not support audio language detection")
        return self._detector.detect(audio, valid_langs=valid_langs or self.available_languages)

    @classproperty
    def runtime_requirements(cls):
        """
        Returns the runtime requirements for the STT implementation.
        
        This class method should be overridden by subclasses to specify network and internet
        dependencies required for the plugin to function correctly. By default, it returns
        a `RuntimeRequirements` object with default settings, indicating no special
        requirements.
        """
        return RuntimeRequirements()

    @property
    def lang(self):
        """
        Gets the current language tag in standardized format.
        
        Returns:
            The standardized language tag, determined by the instance, configuration, or session language.
        """
        return standardize_lang_tag(self._lang or \
                                    self.config.get("lang") or \
                                    SessionManager.get().lang)

    @lang.setter
    def lang(self, val):
        # backwards compat
        """
        Sets the language tag for speech recognition, standardizing its format.
        """
        self._lang = standardize_lang_tag(val)

    @abstractmethod
    def execute(self, audio, language: Optional[str] = None) -> str:
        # TODO - eventually deprecate this and make transcribe the @abstractmethod
        """
        Performs speech recognition on the provided audio input using the specified language.
        
        This method must be implemented by subclasses to return the recognized text from the audio data.
        
        Args:
            audio: The audio data to be transcribed.
            language: Optional language tag specifying the language for recognition.
        
        Returns:
            The transcribed text from the audio input.
        """
        pass

    def transcribe(self, audio, lang: Optional[str] = None) -> List[Tuple[str, float]]:
        """
        Transcribes audio data into a list of possible transcriptions with confidence scores.
        
        If `lang` is set to "auto", attempts to detect the language from the audio and falls back to the default language if detection fails.
        
        Args:
            audio: The audio data to transcribe.
            lang: The language code to use for transcription, or "auto" to enable automatic language detection.
        
        Returns:
            A list containing a single tuple with the transcription and a confidence score of 1.0.
        """
        if lang is not None and lang == "auto":
            try:
                lang, prob = self.detect_language(audio, self.available_languages)
            except Exception as e:
                LOG.error(f"Language detection failed: {e}. Falling back to default language.")
                lang = self.lang  # Fall back to default language
        return [(self.execute(audio, lang), 1.0)]

    @classproperty
    def available_languages(cls) -> Set[str]:
        """
        Returns the set of languages supported by this STT implementation.
        
        This class property should be overridden by subclasses to specify the supported language tags.
        
        Returns:
            Set[str]: Supported language tags.
        """
        return set()


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
