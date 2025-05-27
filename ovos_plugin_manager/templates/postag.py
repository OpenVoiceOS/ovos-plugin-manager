import abc
from typing import Tuple, List
from ovos_bus_client.session import SessionManager
from ovos_utils import classproperty
from ovos_utils.lang import standardize_lang_tag
from ovos_utils.process_utils import RuntimeRequirements


Tag = Tuple[int, int, str, str]  # start_idx, end_idx, word, tag


class PosTagger:
    def __init__(self, config=None):
        """
        Initializes the POS tagger with an optional configuration dictionary.
        
        Args:
            config: Optional dictionary containing configuration parameters for the tagger.
        """
        self.config = config or {}

    @classproperty
    def runtime_requirements(cls):
        """
        Describes the runtime connectivity requirements for the POS tagger.
        
        By default, indicates that no internet or network connectivity is required before or during loading, and that fallback modes are supported when connectivity is unavailable. Subclasses can override this property to specify different requirements based on their implementation.
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
        Returns the standardized language code for the tagger.
        
        If a language is specified in the configuration, it is used; otherwise, the current session's language is returned. The language code is standardized before being returned.
        """
        lang = self.config.get("lang") or SessionManager.get().lang
        return standardize_lang_tag(lang)

    @abc.abstractmethod
    def postag(self, spans, lang=None) -> List[Tag]:
        """
        Assigns part-of-speech tags to the provided spans.
        
        Args:
            spans: A list of text spans to be tagged.
            lang: Optional language code to specify the language for tagging.
        
        Returns:
            A list of Tag tuples, each containing the start index, end index, word, and its POS tag.
        
        Raises:
            NotImplementedError: This method must be implemented by subclasses.
        """
        raise NotImplementedError()
