from ovos_config import Configuration
from ovos_plugin_manager.vad import get_vad_config


class VADEngine:
    def __init__(self, config=None, sample_rate=None):
        self.config_core = Configuration()
        config = config or get_vad_config()
        self.sample_rate = sample_rate or \
                           self.config_core.get("listener", {}).get("sample_rate", 16000)

    def is_silence(self, chunk):
        # return True or False
        return False

