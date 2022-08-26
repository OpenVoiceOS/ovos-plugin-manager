from ovos_plugin_manager.utils.config import get_plugin_config


class KeywordExtractor:
    def __init__(self, config=None):
        self.config = config or get_plugin_config(config, "keyword_extract")

    def extract(self, text, lang):
        return {text: 0.0}
