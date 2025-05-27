import abc
from typing import Optional, List

from ovos_bus_client.session import SessionManager
from ovos_utils import classproperty
from ovos_utils.lang import standardize_lang_tag
from ovos_utils.process_utils import RuntimeRequirements


class Segmenter:
    def __init__(self, config=None):
        """
        Initializes the Segmenter with an optional configuration dictionary.
        
        Args:
            config: Optional dictionary of configuration parameters. If not provided,
                an empty dictionary is used.
        """
        self.config = config or {}

    @classproperty
    def runtime_requirements(cls):
        """
        Describes the runtime connectivity requirements for the segmenter.
        
        By default, indicates that no internet or network connectivity is required before loading or during operation, and that fallback is allowed when offline. Subclasses should override this property to specify different requirements as needed.
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
        Returns the standardized language code for segmentation.
        
        The language is determined from the instance configuration if available; otherwise, it is retrieved from the current session.
        """
        lang = self.config.get("lang") or SessionManager.get().lang
        return standardize_lang_tag(lang)

    @abc.abstractmethod
    def segment(self, text: str, lang: Optional[str] = None) -> List[str]:
        """
        Segments the input text into a list of strings.
        
        Subclasses must implement this method to divide the provided text into segments, such as sentences or phrases, according to the specified language.
        
        Args:
            text: The text to be segmented.
            lang: Optional language code to guide segmentation. If not provided, the segmenter's default language is used.
        
        Returns:
            A list of segmented strings.
        
        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError()
