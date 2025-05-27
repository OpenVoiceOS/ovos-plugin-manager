import abc
from typing import List, Dict, Optional
from ovos_utils.process_utils import RuntimeRequirements

from ovos_bus_client.session import SessionManager
from ovos_utils import classproperty
from ovos_utils.lang import standardize_lang_tag


class KeywordExtractor:
    def __init__(self, config=None):
        """
        Initializes the KeywordExtractor with an optional configuration.
        
        Args:
            config: Optional dictionary of configuration parameters. If not provided, an empty dictionary is used.
        """
        self.config = config or {}

    @classproperty
    def runtime_requirements(cls):
        """
        Specifies the runtime connectivity requirements for the keyword extractor.
        
        By default, indicates that no internet or network connectivity is required before or during loading, and that fallback behavior is allowed if connectivity is unavailable. Subclasses should override this property to declare their specific connectivity needs.
        """
        return RuntimeRequirements(internet_before_load=False,
                                   network_before_load=False,
                                   requires_internet=False,
                                   requires_network=False,
                                   no_internet_fallback=True,
                                   no_network_fallback=True)

    @property
    def lang(self) -> str:
        """
        Returns the standardized language code for the extractor.
        
        If a language is specified in the configuration, it is used; otherwise, the language
        from the current session is used. The resulting language code is standardized for
        consistency.
        """
        lang = self.config.get("lang") or SessionManager.get().lang
        return standardize_lang_tag(lang)

    @abc.abstractmethod
    def extract(self, text: str, lang: Optional[str] = None) -> Dict[str, float]:
        """
        Extracts keywords from the given text and assigns relevance scores.
        
        Args:
            text: The input text from which to extract keywords.
            lang: Optional language code to guide extraction; if not provided, the extractor's default language is used.
        
        Returns:
            A dictionary mapping each extracted keyword to its relevance score.
        
        Raises:
            NotImplementedError: This method must be implemented by subclasses.
        """
        raise NotImplementedError()
