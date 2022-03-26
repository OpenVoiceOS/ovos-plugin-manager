from mycroft_bus_client.message import dig_for_message
from ovos_utils import flatten_list
from quebra_frases import sentence_tokenize


class Segmenter:
    # Add lang markers here for naive segmentation
    # NOTE str.split operation, not token by token comparison
    # this means you need spaces on both sides of the marker
    SEGMENTATION_MARKERS_EN = [" and ", " then "]
    SEGMENTATION_MARKERS_PT = [" e ", " depois ", " a seguir ", " de seguida "]

    def __init__(self, config=None):
        self.config = config or {}

    @property
    def lang(self):
        lang = self.config.get("lang")
        msg = dig_for_message()
        if msg:
            lang = msg.data.get("lang")
        return lang or "en-us"

    @staticmethod
    def _extract(text, markers, no_replaces=None):
        # TODO refactor this ugly beast
        no_replaces = no_replaces or []
        if isinstance(text, str):
            sents = [text]
        else:
            sents = text
        for m in markers:
            for idx, sent in enumerate(sents):
                subs = {}
                if isinstance(sent, str):
                    for no in no_replaces:
                        if m in no:
                            _ = str(idx) + no.replace(m, "")
                            subs[_] = no
                            sents[idx] = sents[idx].replace(no, _)
                    splits = sents[idx].split(m)
                    for k in subs:
                        splits = [_.replace(k, subs[k]) for _ in splits]
                    sents[idx] = splits

            # flatten list
            sents = flatten_list(sents)
        return sents

    @staticmethod
    def extract_candidates(text, lang="en"):
        sents = sentence_tokenize(text)
        if lang.startswith("en"):
            return Segmenter._extract(sents, Segmenter.SEGMENTATION_MARKERS_EN,
                                      ["p.m", "p.m.", "a.m", "a.m."])
        elif lang.startswith("pt"):
            return Segmenter._extract(sents, Segmenter.SEGMENTATION_MARKERS_PT)
        return sents

    def segment(self, text):
        return [s.strip() for s in self.extract_candidates(text, lang=self.lang) if s]
