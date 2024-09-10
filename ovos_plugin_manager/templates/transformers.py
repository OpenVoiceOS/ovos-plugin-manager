import abc
from typing import List, Tuple, Optional

from ovos_bus_client.util import get_mycroft_bus
from ovos_config.config import Configuration
from ovos_config.locale import get_default_lang
from ovos_utils.log import LOG

from ovos_plugin_manager.utils import ReadWriteStream


class MetadataTransformer:
    """ runs after utterance transformers and before intent service"""

    def __init__(self, name, priority=50, config=None):
        self.name = name
        self.bus = None
        self.priority = priority
        if not config:
            config_core = dict(Configuration())
            config = config_core.get("metadata_transformers", {}).get(self.name)
        self.config = config or {}

    def bind(self, bus=None):
        """ attach messagebus """
        self.bus = bus or get_mycroft_bus()

    def initialize(self):
        """ perform any initialization actions """
        pass

    def transform(self, context: dict = None) -> (list, dict):
        """
        Optionally transform passed context
        eg. inject default values or convert metadata format
        :param context: existing Message context from all previous transformers
        :returns: dict of possibly modified or additional context
        """
        context = context or {}
        return context

    def default_shutdown(self):
        """ perform any shutdown actions """
        pass


class UtteranceTransformer:
    """ runs before metadata transformers and intent service"""

    def __init__(self, name, priority=50, config=None):
        self.name = name
        self.bus = None
        self.priority = priority
        if not config:
            config_core = dict(Configuration())
            config = config_core.get("utterance_transformers", {}).get(self.name)
        self.config = config or {}

    def bind(self, bus=None):
        """ attach messagebus """
        self.bus = bus or get_mycroft_bus()

    def initialize(self):
        """ perform any initialization actions """
        pass

    def transform(self, utterances: List[str],
                  context: dict = None) -> (list, dict):
        """
        Optionally transform passed utterances and/or return additional context
        :param utterances: List of str utterances to parse
        :param context: existing Message context associated with utterances
        :returns: tuple of (possibly modified utterances, additional context)
        """
        return utterances, {}

    def default_shutdown(self):
        """ perform any shutdown actions """
        pass


class AudioTransformer:
    """process audio data and optionally transform it before STT stage"""

    def __init__(self, name, priority=50, config=None):
        self.name = name
        self.bus = None
        self.priority = priority
        self.config = config or self._read_mycroft_conf()

        # listener config
        self.sample_width = self.config.get("sample_width", 2)
        self.channels = self.config.get("channels", 1)
        self.sample_rate = self.config.get("sample_rate", 16000)

        # buffers with audio chunks to be used in predictions
        # always cleared before STT stage
        # 16000 samples/second * 2 bytes/sample * 3 seconds = 96000 bytes.
        self.noise_feed = ReadWriteStream(max_size=96000)  # 3 second buffer
        self.hotword_feed = ReadWriteStream(max_size=96000)  # 3 seconds buffer
        # 16000 samples/second * 2 bytes/sample * 10 seconds = 320000 bytes.
        self.speech_feed = ReadWriteStream(max_size=320000)  # 10 seconds buffer

    def _read_mycroft_conf(self):
        config_core = dict(Configuration())
        config = config_core.get("audio_transformers", {}).get(self.name) or {}
        listener_config = config_core.get("listener") or {}
        for k in ["sample_width", "sample_rate", "channels"]:
            if k not in config and k in listener_config:
                config[k] = listener_config[k]
        return config

    def bind(self, bus=None):
        """ attach messagebus """
        self.bus = bus or get_mycroft_bus()

    def feed_audio_chunk(self, chunk):
        chunk = self.on_audio(chunk)
        self.noise_feed.write(chunk)

    def feed_hotword_chunk(self, chunk):
        chunk = self.on_hotword(chunk)
        self.hotword_feed.write(chunk)

    def feed_speech_chunk(self, chunk):
        chunk = self.on_speech(chunk)
        self.speech_feed.write(chunk)

    def feed_speech_utterance(self, chunk):
        return self.on_speech_end(chunk)

    def reset(self):
        # end of prediction, reset buffers
        self.speech_feed.clear()
        self.hotword_feed.clear()
        self.noise_feed.clear()

    def initialize(self):
        """ perform any initialization actions """
        pass

    def on_audio(self, audio_data):
        """ Take any action you want, audio_data is a non-speech chunk
        """
        return audio_data

    def on_hotword(self, audio_data):
        """ Take any action you want, audio_data is a full wake/hotword
        Common action would be to prepare to received speech chunks
        NOTE: this might be a hotword or a wakeword, listening is not assured
        """
        return audio_data

    def on_speech(self, audio_data):
        """ Take any action you want, audio_data is a speech chunk (NOT a
        full utterance) during recording
        """
        return audio_data

    def on_speech_end(self, audio_data):
        """ Take any action you want, audio_data is the full speech audio
        """
        return audio_data

    def transform(self, audio_data):
        """ return any additional message context to be passed in
        recognize_loop:utterance message, usually a streaming prediction
        Optionally make the prediction here with saved chunks from other handlers
        """
        return audio_data, {}

    def default_shutdown(self):
        """ perform any shutdown actions """
        pass


class DialogTransformer:
    """ runs before TTS stage"""

    def __init__(self, name, priority=50, config=None):
        self.name = name
        self.bus = None
        self.priority = priority
        if not config:
            config_core = dict(Configuration())
            config = config_core.get("dialog_transformers", {}).get(self.name)
        self.config = config or {}

    def bind(self, bus=None):
        """ attach messagebus """
        self.bus = bus or get_mycroft_bus()

    def initialize(self):
        """ perform any initialization actions """
        pass

    def transform(self, dialog: str, context: dict = None) -> Tuple[str, dict]:
        """
        Optionally transform passed dialog and/or return additional context
        :param dialog: str utterance to mutate before TTS
        :returns: str mutated dialog
        """
        return dialog, context

    def default_shutdown(self):
        """ perform any shutdown actions """
        pass


class TTSTransformer:
    """ runs after TTS stage but before playback"""

    def __init__(self, name, priority=50, config=None):
        self.name = name
        self.bus = None
        self.priority = priority
        if not config:
            config_core = dict(Configuration())
            config = config_core.get("dialog_transformers", {}).get(self.name)
        self.config = config or {}

    def bind(self, bus=None):
        """ attach messagebus """
        self.bus = bus or get_mycroft_bus()

    def initialize(self):
        """ perform any initialization actions """
        pass

    def transform(self, wav_file: str, context: dict = None) -> Tuple[str, dict]:
        """
        Optionally transform passed wav_file and return path to transformed file
        :param wav_file: path to wav file generated in TTS stage
        :returns: path to transformed wav file for playback
        """
        return wav_file, context

    def default_shutdown(self):
        """ perform any shutdown actions """
        pass


class AudioLanguageDetector(AudioTransformer):

    @property
    def valid_langs(self) -> List[str]:
        return list(
            set([get_default_lang()] + Configuration().get("secondary_langs", []))
        )

    @abc.abstractmethod
    def detect(self, audio_data: bytes, valid_langs: Optional[List] = None) -> Tuple[str, float]:
        raise NotImplementedError

    # plugin api
    def transform(self, audio_data: bytes):
        lang, prob = self.detect(audio_data)
        LOG.info(f"Detected speech language '{lang}' with probability {prob}")
        return audio_data, {"stt_lang": lang, "lang_probability": prob}
