
class LanguageDetector:
    def __init__(self, config):
        self.config = config
        self.default_language = self.config.get("lang") or "en-us"
        # hint_language: str  E.g., 'ITALIAN' or 'it' boosts Italian
        self.hint_language = self.config.get("hint_lang") or self.default_language
        self.boost = self.config.get("boost")

    def detect(self, text):
        # assume default language
        return self.default_language

    def detect_probs(self, text):
        return {self.detect(text): 1}


class LanguageTranslator:
    def __init__(self, config):
        self.config = config
        self.boost = self.config.get("boost")
        # translate from, unless specified/detected otherwise
        self.default_language = self.config.get("lang") or "en-us"
        # translate to
        self.internal_language = self.config.get("lang") or "en-us"

    def translate(self, text, target=None, source=None):
        return text
