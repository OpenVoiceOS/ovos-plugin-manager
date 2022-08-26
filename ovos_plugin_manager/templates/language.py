from ovos_config.config import Configuration


class LanguageDetector:
    def __init__(self, config=None):
        config_core = Configuration()
        self.config = config or config_core.get('language')
        self.default_language = config_core.get("lang") or "en-us"
        # hint_language: str  E.g., 'it' boosts Italian
        self.hint_language = self.config.get("hint_lang") or \
            self.config.get('user') or self.default_language
        # boost score for this language
        self.boost = self.config.get("boost")

    def detect(self, text):
        # assume default language
        return self.default_language

    def detect_probs(self, text):
        return {self.detect(text): 1}


class LanguageTranslator:
    def __init__(self, config=None):
        config_core = Configuration()
        self.config = config or config_core.get('language')
        # translate from, unless specified/detected otherwise
        self.default_language = config_core.get("lang") or "en-us"
        # translate to
        self.internal_language = self.config.get("internal") or \
            self.default_language or "en-us"

    def translate(self, text, target=None, source=None):
        return text

    def translate_dict(self, data, lang_tgt, lang_src="en"):
        for k, v in data.items():
            if isinstance(v, dict):
                data[k] = self.translate_dict(v, lang_tgt, lang_src)
            elif isinstance(v, str):
                data[k] = self.translate(v, lang_tgt, lang_src)
            elif isinstance(v, list):
                data[k] = self.translate_list(v, lang_tgt, lang_src)
        return data

    def translate_list(self, data, lang_tgt, lang_src="en"):
        for idx, v in enumerate(data):
            if isinstance(v, dict):
                data[idx] = self.translate_dict(v, lang_tgt, lang_src)
            elif isinstance(v, str):
                data[idx] = self.translate(v, lang_tgt, lang_src)
            elif isinstance(v, list):
                data[idx] = self.translate_list(v, lang_tgt, lang_src)
        return data
