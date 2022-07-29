from ovos_config import Configuration


class VADEngine:
    def __init__(self, config=None, sample_rate=None):
        self.config_core = Configuration()
        self._init_config(config)
        self.sample_rate = sample_rate or \
                           self.config_core.get("listener", {}).get("sample_rate", 16000)

    def _init_config(self, config=None):
        if config is None:
            config_vad = self.config_core.get("listener", {}).get("VAD") or {}
            self.config = config_vad.get(config_vad.get("module"), {})
        else:
            self.config = config

    def is_silence(self, chunk):
        # return True or False
        return False

