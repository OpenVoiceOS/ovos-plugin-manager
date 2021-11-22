from json_database import JsonStorageXDG
import xdg.BaseDirectory


class LanguageDetector:
    def __init__(self, config=None):
        self.config = config or {}
        db_name = self.__class__.__name__.lower()
        self.cache = JsonStorageXDG(db_name,
                                    xdg_folder=xdg.BaseDirectory.xdg_cache_home,
                                    subfolder="lang_detections")
        self.default_language = self.config.get("lang") or "en-us"
        # hint_language: str  E.g., 'it' boosts Italian
        self.hint_language = self.config.get("hint_lang") or self.default_language
        # boost score for this language
        self.boost = self.config.get("boost")

    def get_detection(self, text):
        # plugins that need/want cache can override this method
        # old plugins (pre-cache) or if cache is not desired
        # can continue overriding self.detect and will remain working as usual
        # usage of self.get_detection is encouraged for non-local providers
        return self.default_language  # assume default language by default

    def detect(self, text):
        # read from cache
        tx = self.cache.get(text)
        if tx:
            return tx
        # do detection
        tx = self.get_detection(text)
        # cache translation
        self.cache[text] = tx
        self.cache.store()
        return tx

    def detect_probs(self, text):
        return {self.detect(text): 1.0}


class LanguageTranslator:
    def __init__(self, config=None):
        self.config = config or {}
        db_name = self.__class__.__name__.lower() + ".json"
        self.cache = JsonStorageXDG(db_name,
                                    xdg_folder=xdg.BaseDirectory.xdg_cache_home,
                                    subfolder="lang_translations")
        # translate from, unless specified/detected otherwise
        self.default_language = self.config.get("lang") or "en-us"
        # translate to
        self.internal_language = self.config.get("lang") or "en-us"

    def get_translation(self, text, target=None, source=None):
        # plugins that need/want cache can override this method
        # old plugins (pre-cache) or if cache is not desired
        # can continue overriding self.translate and will remain working as usual
        # usage of self.get_translation is encouraged for non-local providers
        return text

    def translate(self, text, target=None, source=None):
        # read from cache
        if target:
            tx = self.cache.get(target, {}).get(text)
            if tx:
                return tx
        # do translation
        tx = self.get_translation(text, target, source)
        # cache translation
        if target:
            if target not in self.cache:
                self.cache[target] = {}
            self.cache[target][text] = tx
            self.cache.store()
        return tx

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
