import abc

from ovos_config.config import Configuration
from ovos_utils import classproperty
from ovos_utils.lang import standardize_lang_tag
from ovos_utils.process_utils import RuntimeRequirements
from typing import Optional, Dict, Union, List, Set


class LanguageDetector:
    def __init__(self, config: Optional[Dict[str, Union[str, int]]] = None):
        """
        Initialize the LanguageDetector with configuration settings.

        Args:
            config (Optional[Dict[str, Union[str, int]]]): Configuration dictionary.
                Can contain "lang" for default language, "hint_lang" for a hint language, and "boost" for language boost score.
        """
        self.config = config or {}
        self.default_language = standardize_lang_tag(self.config.get("lang", "en-US"))
        self.hint_language = standardize_lang_tag(self.config.get("hint_lang") or
                                                  self.config.get('user') or
                                                  self.default_language)
        self.boost = self.config.get("boost")

    @classproperty
    def runtime_requirements(self) -> RuntimeRequirements:
        """
        Define the runtime requirements for this language detector.

        Returns:
            RuntimeRequirements: Object indicating the runtime needs, including internet and network requirements.
        """
        return RuntimeRequirements(
            internet_before_load=False,
            network_before_load=False,
            requires_internet=False,
            requires_network=False,
            no_internet_fallback=True,
            no_network_fallback=True
        )

    @abc.abstractmethod
    def detect(self, text: str) -> str:
        """
        Detect the language of the given text.

        Args:
            text (str): The text to detect the language of.

        Returns:
            str: The detected language code (e.g., 'en-US').
        """

    @abc.abstractmethod
    def detect_probs(self, text: str) -> Dict[str, float]:
        """
        Detect the language of the text and return probabilities.

        Args:
            text (str): The text to detect the language of.

        Returns:
            Dict[str, float]: A dictionary with the detected language as the key and its probability as the value.
        """

    @property  # TODO - make abstract method in future releases (mandatory for plugins to implement)
    def available_languages(self) -> Set[str]:
        """
        Return languages supported by this detector implementation in this state.
        This should be a set of languages this detector is capable of recognizing.
        This property should be overridden by the derived class to advertise
        what languages that engine supports.
        Returns:
            Set[str]: A set of language codes supported by this detector.
        """
        return set()


class LanguageTranslator:
    def __init__(self, config: Optional[Dict[str, str]] = None):
        """
        Initialize the LanguageTranslator with configuration settings.

        Args:
            config (Optional[Dict[str, str]]): Configuration dictionary.
                Can contain "lang" for the default language and "internal" for the internal language.
        """
        self.config = config or {}
        # translate from, unless specified/detected otherwise
        self.default_language = standardize_lang_tag(self.config.get("lang") or "en-US")
        # translate to
        self.internal_language = standardize_lang_tag(Configuration().get('language', {}).get("internal") or \
                                 self.default_language)

    @classproperty
    def runtime_requirements(self) -> RuntimeRequirements:
        """
        Define the runtime requirements for this language translator.

        Returns:
            RuntimeRequirements: Object indicating the runtime needs, including internet and network requirements.
        """
        return RuntimeRequirements(
            internet_before_load=False,
            network_before_load=False,
            requires_internet=False,
            requires_network=False,
            no_internet_fallback=True,
            no_network_fallback=True
        )

    @abc.abstractmethod
    def translate(self, text: str, target: Optional[str] = None, source: Optional[str] = None) -> str:
        """
        Translate the given text from the source language to the target language.

        Args:
            text (str): The text to translate.
            target (Optional[str]): The target language code. If None, the internal language is used.
            source (Optional[str]): The source language code. If None, the default language is used.

        Returns:
            str: The translated text.
        """

    def translate_dict(self, data: Dict[str, Union[str, Dict, List]], lang_tgt: str, lang_src: str = "en") -> Dict[str, Union[str, Dict, List]]:
        """
        Translate the values in a dictionary from one language to another.

        Args:
            data (Dict[str, Union[str, Dict, List]]): The dictionary containing text to translate.
            lang_tgt (str): The target language code.
            lang_src (str): The source language code.

        Returns:
            Dict[str, Union[str, Dict, List]]: The dictionary with translated values.
        """
        for k, v in data.items():
            if isinstance(v, dict):
                data[k] = self.translate_dict(v, lang_tgt, lang_src)
            elif isinstance(v, str):
                data[k] = self.translate(v, lang_tgt, lang_src)
            elif isinstance(v, list):
                data[k] = self.translate_list(v, lang_tgt, lang_src)
        return data

    def translate_list(self, data: List[Union[str, Dict, List]], lang_tgt: str, lang_src: str = "en") -> List[Union[str, Dict, List]]:
        """
        Translate the values in a list from one language to another.

        Args:
            data (List[Union[str, Dict, List]]): The list containing text to translate.
            lang_tgt (str): The target language code.
            lang_src (str): The source language code.

        Returns:
            List[Union[str, Dict, List]]: The list with translated values.
        """
        for idx, v in enumerate(data):
            if isinstance(v, dict):
                data[idx] = self.translate_dict(v, lang_tgt, lang_src)
            elif isinstance(v, str):
                data[idx] = self.translate(v, lang_tgt, lang_src)
            elif isinstance(v, list):
                data[idx] = self.translate_list(v, lang_tgt, lang_src)
        return data

    @property  # TODO - make abstract method in future releases (mandatory for plugins to implement)
    def available_languages(self) -> Set[str]:
        """
        Return languages supported by this translator implementation in this state.
        Any language in this set should be translatable to any other language in the set.
        This property should be overridden by the derived class to advertise
        what languages that engine supports.
        Returns:
            Set[str]: A set of language codes supported by this translator.
        """
        return set()

    # TODO - make abstract method in future releases (mandatory for plugins to implement)
    def supported_translations(self, source_lang: Optional[str] = None) -> Set[str]:
        """
        Get the set of target languages to which the source language can be translated.

        Args:
            source_lang (Optional[str]): The source language code.

        Returns:
            Set[str]: A set of language codes that the source language can be translated to.
        """
        return self.available_languages
