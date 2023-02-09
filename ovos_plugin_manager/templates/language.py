from ovos_config.config import Configuration
from ovos_utils import classproperty
from ovos_utils.process_utils import RuntimeRequirements


class LanguageDetector:
    def __init__(self, config=None):
        self.config = config or {}
        self.default_language = self.config.get("lang") or "en-us"
        # hint_language: str  E.g., 'it' boosts Italian
        self.hint_language = self.config.get("hint_lang") or \
                             self.config.get('user') or self.default_language
        # boost score for this language
        self.boost = self.config.get("boost")

    @classproperty
    def runtime_requirements(self):
        """ skill developers should override this if they do not require connectivity
         some examples:
         IOT plugin that controls devices via LAN could return:
            scans_on_init = True
            RuntimeRequirements(internet_before_load=False,
                                 network_before_load=scans_on_init,
                                 requires_internet=False,
                                 requires_network=True,
                                 no_internet_fallback=True,
                                 no_network_fallback=False)
         online search plugin with a local cache:
            has_cache = False
            RuntimeRequirements(internet_before_load=not has_cache,
                                 network_before_load=not has_cache,
                                 requires_internet=True,
                                 requires_network=True,
                                 no_internet_fallback=True,
                                 no_network_fallback=True)
         a fully offline plugin:
            RuntimeRequirements(internet_before_load=False,
                                 network_before_load=False,
                                 requires_internet=False,
                                 requires_network=False,
                                 no_internet_fallback=True,
                                 no_network_fallback=True)
        """
        return RuntimeRequirements(internet_before_load=False,
                                   network_before_load=False,
                                   requires_internet=False,
                                   requires_network=False,
                                   no_internet_fallback=True,
                                   no_network_fallback=True)

    def detect(self, text):
        # assume default language
        return self.default_language

    def detect_probs(self, text):
        return {self.detect(text): 1}

    @property
    def available_languages(self) -> set:
        """
        Return languages supported by this detector implementation in this state.
        This should be a set of languages this detector is capable of recognizing.
        This property should be overridden by the derived class to advertise
        what languages that engine supports.
        Returns:
            set: supported languages
        """
        return set()


class LanguageTranslator:
    def __init__(self, config=None):
        self.config = config or {}
        # translate from, unless specified/detected otherwise
        self.default_language = self.config.get("lang") or "en-us"
        # translate to
        self.internal_language = (Configuration().get('language') or
                                  dict()).get("internal") or \
                                 self.default_language

    @classproperty
    def runtime_requirements(self):
        """ skill developers should override this if they do not require connectivity
         some examples:
         IOT plugin that controls devices via LAN could return:
            scans_on_init = True
            RuntimeRequirements(internet_before_load=False,
                                 network_before_load=scans_on_init,
                                 requires_internet=False,
                                 requires_network=True,
                                 no_internet_fallback=True,
                                 no_network_fallback=False)
         online search plugin with a local cache:
            has_cache = False
            RuntimeRequirements(internet_before_load=not has_cache,
                                 network_before_load=not has_cache,
                                 requires_internet=True,
                                 requires_network=True,
                                 no_internet_fallback=True,
                                 no_network_fallback=True)
         a fully offline plugin:
            RuntimeRequirements(internet_before_load=False,
                                 network_before_load=False,
                                 requires_internet=False,
                                 requires_network=False,
                                 no_internet_fallback=True,
                                 no_network_fallback=True)
        """
        return RuntimeRequirements(internet_before_load=False,
                                   network_before_load=False,
                                   requires_internet=False,
                                   requires_network=False,
                                   no_internet_fallback=True,
                                   no_network_fallback=True)

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

    @property
    def available_languages(self) -> set:
        """
        Return languages supported by this translator implementation in this state.
        Any language in this set should be translatable to any other language in the set.
        This property should be overridden by the derived class to advertise
        what languages that engine supports.
        Returns:
            set: supported languages
        """
        return set()

    def supported_translations(self, source_lang: str = None) -> set:
        """
        Return valid target languages we can translate `source_lang` to.
        This method should be overridden by the derived class.
        Args:
            source_lang: ISO 639-1 source language code
        Returns:
            set of ISO 639-1 languages the source language can be translated to
        """
        return self.available_languages
