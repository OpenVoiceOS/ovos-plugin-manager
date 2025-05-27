from ovos_bus_client.session import SessionManager
from ovos_utils import classproperty
from ovos_utils.lang import standardize_lang_tag
from ovos_utils.process_utils import RuntimeRequirements
from quebra_frases import span_indexed_word_tokenize, word_tokenize


class Tokenizer:
    def __init__(self, config=None):
        """
        Initializes the Tokenizer instance with an optional configuration.
        
        Args:
            config: Optional dictionary specifying tokenizer settings.
        """
        self.config = config or {}

    @classproperty
    def runtime_requirements(cls):
        """
        Specifies the runtime connectivity requirements for the Tokenizer.
        
        Returns:
            RuntimeRequirements: Indicates that the Tokenizer does not require internet
            or network connectivity before or during loading, and supports operation
            without either. Skill developers can override this method to declare
            different connectivity needs for their own plugins.
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
        Returns the standardized language code for the tokenizer.
        
        The language is determined from the instance configuration if available; otherwise, it is retrieved from the current session.
        """
        lang = self.config.get("lang") or SessionManager.get().lang
        return standardize_lang_tag(lang)

    def span_tokenize(self, text, lang=None):
        """
        Tokenizes text into spans indicating the start and end indices of each token.
        
        Args:
            text: The input string to tokenize.
            lang: Optional language code (currently unused).
        
        Returns:
            A list of tuples, each containing the start index, end index, and token string.
        """
        return span_indexed_word_tokenize(text)

    def tokenize(self, text, lang=None):
        return word_tokenize(text)

    @staticmethod
    def restore_spans(spans):
        # restore sentence from spans
        sentence = ""
        for start, end, token in spans:
            if start > len(sentence):
                sentence += " "
            sentence += token
        return sentence
