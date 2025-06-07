from ovos_bus_client.session import SessionManager
from ovos_utils import classproperty
from ovos_utils.lang import standardize_lang_tag
from ovos_utils.process_utils import RuntimeRequirements
from quebra_frases import word_tokenize
import abc


class CoreferenceSolverEngine:
    def __init__(self, config=None):
        self.config = config or {}
        self._prev_sentence = ""
        self._prev_solved = ""
        self.contexts = {}

    @classproperty
    def runtime_requirements(cls):
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

    @property
    def lang(self) -> str:
        lang = self.config.get("lang") or SessionManager.get().lang
        return standardize_lang_tag(lang)

    @staticmethod
    def extract_replacements(original, solved):
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
        raise NotImplementedError()

    @abc.abstractmethod
    def solve_corefs(self, text: str, lang: str):
        raise NotImplementedError()


def replace_coreferences(text, smart=True, lang=None,
                         solver=None, use_context=True, set_context=True):
    if smart and solver:
        if not solver.contains_corefs(text, lang):
            return text
    if solver:
        if not use_context:
            return solver.replace_coreferences(text, set_context=set_context)
        return solver.replace_coreferences_with_context(text, set_context=set_context)
    return text
