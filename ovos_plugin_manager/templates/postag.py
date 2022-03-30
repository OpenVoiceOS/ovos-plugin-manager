from mycroft_bus_client.message import dig_for_message


class PosTagger:
    def __init__(self, config=None):
        self.config = config or {}

    @property
    def lang(self):
        lang = self.config.get("lang")
        msg = dig_for_message()
        if msg:
            lang = msg.data.get("lang")
        return lang or "en-us"

    def postag(self, spans, lang=None):
        lang = lang or self.lang
        tokens = [t for (s, e, t) in spans]
        # this should be implemented by plugins!
        if lang.startswith("pt"):
            return _dummy_postag_pt(tokens)
        elif lang.startswith("en"):
            return _dummy_postag_en(tokens)
        return _dummy_postag(tokens)


def _dummy_postag_pt(tokens):
    pos = []
    for t in tokens:
        if t == "e":
            pos.append((t, "CONJ"))
        elif t in ["o", "a", "os", "as"]:
            pos.append((t, "DET"))
        elif t.lower() in ["ele", "ela", "eles", "elas", "nós", "vós"]:
            pos.append((t, "PRON"))
        elif t in ["do", "da", "dos", "das"]:
            pos.append((t, "ADP"))
        elif t.isdigit():
            pos.append((t, "NUMBER"))
        elif t[0].isupper() and len(t) >= 5:
            pos.append((t, "PROPN"))
        elif len(t) >= 4:
            pos.append((t, "NOUN"))
        else:
            pos.append((t, "VERB"))
    return pos


def _dummy_postag_en(tokens):
    pos = []
    for t in tokens:
        if t == "and":
            pos.append((t, "CONJ"))
        elif t in ["the", "a", "an"]:
            pos.append((t, "DET"))
        elif t.lower() in ["he", "she", "it", "they"]:
            pos.append((t, "PRON"))
        elif t in ["of", "for"]:
            pos.append((t, "ADP"))
        elif t.isdigit():
            pos.append((t, "NUMBER"))
        elif t[0].isupper() and len(t) >= 5:
            pos.append((t, "PROPN"))
        elif len(t) >= 4:
            pos.append((t, "NOUN"))
        else:
            pos.append((t, "VERB"))
    return pos


def _dummy_postag(tokens):
    pos = []
    for t in tokens:
        if t.isdigit():
            pos.append((t, "NUMBER"))
        elif t[0].isupper() and len(t) >= 4:
            pos.append((t, "PROPN"))
        elif len(t) >= 5:
            pos.append((t, "NOUN"))
        else:
            pos.append((t, "VERB"))
    return pos
