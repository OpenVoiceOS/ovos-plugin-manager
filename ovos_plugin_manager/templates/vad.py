from ovos_utils.configuration import read_mycroft_config


class VADEngine:
    def __init__(self, config=None):
        try:
            self.config_core = read_mycroft_config() or {}
        except FileNotFoundError:
            self.config_core = {}
        self._init_config(config)

    def _init_config(self, config=None):
        if config is None:
            config_vad = self.config_core.get("listener", {}).get("VAD") or {}
            self.config = config_vad.get(config_vad.get("module"), {})
        else:
            self.config = config

    def is_silence(self, chunk):
        # return True or False
        return False

