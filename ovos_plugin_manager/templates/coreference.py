from mycroft_bus_client.message import dig_for_message


class CoreferenceSolverEngine:
    cache = {}
    contexts = {}
    prev_sentence = ""
    prev_solved = ""

    # TODO move lang data elsewhere
    COREFERENCE_INDICATORS_EN = ["he", "she", "it", "they", "them", "these", "whom",
                                 "whose", "who", "its", "it's", "him", "her", "we",
                                 "us"]
    COREFERENCE_INDICATORS_PT = [
        'ele', "lo", "dele", "nele", "seu", 'ela', "la", "dela", "nela", "sua",
        'eu', 'me', 'mim', 'nós', "comigo", "meu", "minha", "meus", "minhas",
        "tu", "te", "ti", "lhe", "contigo", "consigo", "si", 'eles', 'elas',
        "vós", "vocês", "lhes", "los", "las", "neles", "nelas", "convosco",
        "conosco", "connosco", "teus", "tuas", "seus", "suas", "nossos",
        "vossos", "nossas", "vossas"]

    def __init__(self, config=None):
        self.config = config or {}

    @property
    def lang(self):
        lang = self.config.get("lang")
        msg = dig_for_message()
        if msg:
            lang = msg.data.get("lang")
        return lang or "en-us"

    def contains_corefs(self, text, lang=None):
        lang = lang or self.lang
        if lang.startswith("en"):
            indicators = self.COREFERENCE_INDICATORS_EN
        elif lang.startswith("pt"):
            indicators = self.COREFERENCE_INDICATORS_PT
        else:
            indicators = []
        words = text.split(" ")
        for indicator in indicators:
            if indicator in words:
                return True
        return False

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

    def replace_coreferences(self, text,lang=None):
        lang = lang or self.lang
        self.prev_sentence = text
        return self.solve_corefs(text, lang=lang)

    def replace_coreferences_with_context(self, text, lang=None):
        lang = lang or self.lang
        if text in self.cache:
            solved = self.cache[text]
        else:
            solved = self.solve_corefs(text, lang=lang)
        extracted = self.extract_replacements(text, solved)
        for pronoun in extracted:
            if len(extracted[pronoun]) > 0:
                self.contexts[pronoun] = extracted[pronoun][-1]
        self.prev_sentence = text
        self.prev_solved = solved
        return solved

    def solve_corefs(self, text, lang=None):
        lang = lang or self.lang
        return text


def replace_coreferences(text, smart=True, lang=None, solver=None):
    if smart and solver:
        if not solver.contains_corefs(text, lang):
            return text
    if solver:
        solved = solver.replace_coreferences(text)
        if solved == text:
            return solver.replace_coreferences_with_context(text)
        return solved
    return text
