import abc
from typing import Optional, Dict, Union, List, Set

from ovos_utils import classproperty
from ovos_utils.process_utils import RuntimeRequirements


class LanguageDetector:
    def __init__(self, config: Optional[Dict[str, Union[str, int]]] = None):
        """
        Initializes the LanguageDetector with optional configuration settings.
        
        Args:
            config: Optional dictionary that may specify default language ("lang"), hint language ("hint_lang"), or a language boost score ("boost").
        """
        self.config = config or {}

    @classproperty
    def runtime_requirements(cls) -> RuntimeRequirements:
        """
        Specifies the runtime requirements for the language detector.
        
        Returns:
            A RuntimeRequirements object indicating that no internet or network access
            is required before or during use, and fallback is supported without them.
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
        Returns a mapping of detected language codes to their probabilities for the given text.
        
        Args:
            text: The input text whose language probabilities are to be determined.
        
        Returns:
            A dictionary where keys are language codes and values are the corresponding probabilities.
        """

    @classproperty
    @abc.abstractmethod
    def available_languages(cls) -> Set[str]:
        """
        Returns the set of language codes supported by this detector implementation.
        
        This class property must be overridden by subclasses to specify which languages
        the detector can recognize.
        
        Returns:
            Set[str]: Supported language codes.
        """
        return set()


class LanguageTranslator:
    def __init__(self, config: Optional[Dict[str, str]] = None):
        """
        Initializes the LanguageTranslator with optional configuration settings.
        
        Args:
            config: Optional dictionary that may specify a default language ("lang") and an internal language ("internal").
        """
        self.config = config or {}

    @classproperty
    def runtime_requirements(cls) -> RuntimeRequirements:
        """
        Specifies the runtime requirements for the language translator.
        
        Returns:
            A RuntimeRequirements object indicating that no internet or network access is required before or during load, and that fallback is supported without internet or network connectivity.
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
        Translates text from a source language to a target language.
        
        If `target` is not specified, the internal language is used as the target. If `source` is not specified, the default language is used as the source.
        
        Args:
            text: The text to translate.
            target: The target language code, or None to use the internal language.
            source: The source language code, or None to use the default language.
        
        Returns:
            The translated text.
        """

    def translate_dict(self, data: Dict[str, Union[str, Dict, List]], lang_tgt: str, lang_src: str = "en") -> Dict[
        str, Union[str, Dict, List]]:
        """
        Recursively translates all string values within a nested dictionary from the source language to the target language.
        
        Args:
            data: A dictionary containing strings, dictionaries, or lists to translate.
            lang_tgt: The target language code.
            lang_src: The source language code (default is "en").
        
        Returns:
            The input dictionary with all string values translated to the target language.
        """
        for k, v in data.items():
            if isinstance(v, dict):
                data[k] = self.translate_dict(v, lang_tgt, lang_src)
            elif isinstance(v, str):
                data[k] = self.translate(v, lang_tgt, lang_src)
            elif isinstance(v, list):
                data[k] = self.translate_list(v, lang_tgt, lang_src)
        return data

    def translate_list(self, data: List[Union[str, Dict, List]], lang_tgt: str, lang_src: str = "en") -> List[
        Union[str, Dict, List]]:
        """
        Recursively translates all string values within a nested list from the source language to the target language.
        
        Args:
            data: A list containing strings, dictionaries, or nested lists to translate.
            lang_tgt: The target language code.
            lang_src: The source language code. Defaults to "en".
        
        Returns:
            A list with all string values translated to the target language, preserving the original structure.
        """
        for idx, v in enumerate(data):
            if isinstance(v, dict):
                data[idx] = self.translate_dict(v, lang_tgt, lang_src)
            elif isinstance(v, str):
                data[idx] = self.translate(v, lang_tgt, lang_src)
            elif isinstance(v, list):
                data[idx] = self.translate_list(v, lang_tgt, lang_src)
        return data

    @classproperty
    @abc.abstractmethod
    def available_languages(cls) -> Set[str]:
        """
        Returns the set of language codes supported by this translator implementation.
        
        This class property should be overridden by subclasses to specify which languages
        are available for translation. All languages in the returned set are expected to
        be mutually translatable by the implementation.
        
        Returns:
            Set[str]: Set of supported language codes.
        """
        return set()

    @classproperty
    @abc.abstractmethod
    def supported_translations(cls, source_lang: str) -> Set[str]:
        """
        Returns the set of target languages available for translation from the specified source language.
        
        Args:
            source_lang: The source language code.
        
        Returns:
            A set of language codes representing valid translation targets for the given source language.
        """
        return cls.available_languages
