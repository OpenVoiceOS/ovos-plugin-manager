from typing import List

from ovos_config.config import Configuration
from ovos_utils.messagebus import get_mycroft_bus

from ovos_plugin_manager.utils import ReadWriteStream


class MetadataTransformer:

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
        self.noise_feed = ReadWriteStream()
        self.hotword_feed = ReadWriteStream()
        self.speech_feed = ReadWriteStream()

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
