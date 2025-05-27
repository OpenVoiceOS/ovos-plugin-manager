from ovos_bus_client.session import SessionManager
from ovos_utils import classproperty
from ovos_utils.lang import standardize_lang_tag
from ovos_utils.process_utils import RuntimeRequirements
from quebra_frases import word_tokenize
import abc


class CoreferenceSolverEngine:
    def __init__(self, config=None):
        """
        Initializes the coreference solver engine with optional configuration.
        
        Args:
            config: Optional dictionary of configuration parameters.
        """
        self.config = config or {}
        self._prev_sentence = ""
        self._prev_solved = ""
        self.contexts = {}

    @classproperty
    def runtime_requirements(cls):
        """
        Returns the runtime connectivity requirements for the coreference solver engine.
        
        By default, specifies that no internet or network connectivity is required. Subclasses
        should override this method to declare their specific connectivity needs by returning
        a customized `RuntimeRequirements` object.
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
        Returns the standardized language code for the current configuration or session.
        
        If a language is specified in the configuration, it is used; otherwise, the language
        from the current session is used. The returned language code is standardized for
        consistency.
        """
        lang = self.config.get("lang") or SessionManager.get().lang
        return standardize_lang_tag(lang)

    @staticmethod
    def extract_replacements(original, solved):
        """
        Identifies and maps words or phrases in the original text that have been replaced in the solved (coreference-resolved) text.
        
        Args:
            original: The original input string.
            solved: The coreference-resolved version of the input string.
        
        Returns:
            A dictionary mapping each replaced word from the original text to a list of its replacements in the solved text.
        """
        a = original.lower()
        b = solved.lower()
        chunk = a.split(" ")
        chunk2 = b.split(" ")
        replaced = {}
        index_map = {}
        # extract keys
        indexes = []
        for idx, w in enumerate(chunk):
            if w not in chunk2:
                indexes.append(idx)
                replaced[idx] = []
                index_map[idx] = w
        i2 = 0
        for i in indexes:
            o = chunk[i:]
            s = chunk2[i + i2:]
            if len(o) == 1:
                # print(o[0], "->", " ".join(s), i)
                replaced[i].append(" ".join(s))
                continue
            for idx, word in enumerate(o):
                if word not in s:
                    chunk3 = s[idx:]
                    for idx2, word2 in enumerate(chunk3):
                        if word2 in o and not replaced[i]:
                            chunk3 = s[:idx2]
                            i2 += len(chunk3) - 1
                            # print(word, "->", " ".join(chunk3), i)
                            replaced[i].append(" ".join(chunk3))
        bucket = {}
        for k in replaced:
            if index_map[k] not in bucket:
                bucket[index_map[k]] = []
            bucket[index_map[k]] += replaced[k]
        return bucket

    def add_context(self, word, solved, lang=None):
        lang = standardize_lang_tag(lang or self.lang)
        if lang not in self.contexts:
            self.contexts[lang] = {}
        if word not in self.contexts[lang]:
            self.contexts[lang][word] = []

        # TODO weight based on age and filter old context somehow
        self.contexts[lang][word].append(solved)

    def extract_context(self, text=None, solved=None, lang=None):
        lang = standardize_lang_tag(lang or self.lang)
        text = text or self._prev_sentence
        solved = solved or self._prev_solved
        replaced = self.extract_replacements(text, solved)
        for k, v in replaced.items():
            self.add_context(k, v, lang=lang)
        return replaced

    def replace_coreferences(self, text, lang=None, set_context=False):
        lang = standardize_lang_tag(lang or self.lang)
        solved = self.solve_corefs(text, lang=lang)
        self._prev_sentence = text
        self._prev_solved = solved
        if set_context:
            self.extract_context(text, solved, lang=lang)
        return solved

    def replace_coreferences_with_context(self, text, lang=None, context=None, set_context=False):
        """
        Resolves coreferences in text and applies contextual replacements.
        
        If a context mapping is provided or available for the language, replaces words in the resolved text with their contextual forms. Optionally updates the context with new replacements.
        
        Args:
            text: The input text to process.
            lang: Optional language code; defaults to the engine's language.
            context: Optional dictionary mapping words to their resolved forms.
            set_context: If True, updates the context with replacements found in this operation.
        
        Returns:
            The text with coreferences resolved and contextual replacements applied.
        """
        lang = standardize_lang_tag(lang or self.lang)
        lang_context = self.contexts.get(lang) or {}
        default_context = {k: v[0] for k, v in lang_context.items() if v}

        solved = self.replace_coreferences(text, lang)

        context = context or default_context
        words = word_tokenize(solved)
        for idx, word in enumerate(words):
            if word in context:
                words[idx] = context[word]
        solved = " ".join(words)

        self._prev_sentence = text
        self._prev_solved = solved
        if set_context:
            self.extract_context(text, solved, lang=lang)
        return solved

    @abc.abstractmethod
    def contains_corefs(self, text: str, lang: str) -> bool:
        """
        Determines whether the given text contains coreferences for the specified language.
        
        Subclasses must implement this method to detect the presence of coreferential expressions in the input text.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def solve_corefs(self, text: str, lang: str):
        """
        Resolves coreferences in the given text for the specified language.
        
        This abstract method must be implemented by subclasses to perform coreference resolution, replacing pronouns or referring expressions with their antecedents.
        
        Args:
            text: The input text containing potential coreferences.
            lang: The language code of the input text.
        
        Returns:
            The text with coreferences resolved.
        """
        raise NotImplementedError()


def replace_coreferences(text, smart=True, lang=None,
                         solver=None, use_context=True, set_context=True):
    """
                         Resolves coreferences in the given text using the specified solver.
                         
                         If `smart` is True, the function first checks whether the text contains coreferences before attempting resolution. If `use_context` is True, contextual information is used to improve resolution. If no solver is provided or no coreferences are detected, the original text is returned.
                         
                         Args:
                             text: The input text to process.
                             smart: Whether to check for coreferences before resolving.
                             lang: Optional language code for processing.
                             solver: CoreferenceSolverEngine instance to use for resolution.
                             use_context: Whether to use contextual information during resolution.
                             set_context: Whether to update the solver's context after resolution.
                         
                         Returns:
                             The text with coreferences resolved, or the original text if no resolution is performed.
                         """
                         if smart and solver:
        if not solver.contains_corefs(text, lang):
            return text
    if solver:
        if not use_context:
            return solver.replace_coreferences(text, set_context=set_context)
        return solver.replace_coreferences_with_context(text, set_context=set_context)
    return text
