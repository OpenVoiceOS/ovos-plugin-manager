from mycroft_bus_client.message import dig_for_message
from ovos_utils import classproperty
from ovos_utils import flatten_list
from ovos_utils.process_utils import RuntimeRequirements
from quebra_frases import sentence_tokenize


class Segmenter:
    # Add lang markers here for naive segmentation
    # NOTE str.split operation, not token by token comparison
    # this means you need spaces on both sides of the marker
    SEGMENTATION_MARKERS_EN = [" and ", " then "]
    SEGMENTATION_MARKERS_PT = [" e depois ", " e a seguir ", " e de seguida ",
                               " depois ", " a seguir ", " de seguida ",
                               " e "]

    def __init__(self, config=None):
        self.config = config or {}

    @classproperty
    def runtime_requirements(self):
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
    def lang(self):
        lang = self.config.get("lang")
        msg = dig_for_message()
        if msg:
            lang = msg.data.get("lang")
        return lang or "en-us"

    @staticmethod
    def __extract(text, markers):
        if isinstance(text, str):
            sents = [text]
        else:
            sents = text
        for m in markers:
            for idx, sent in enumerate(sents):
                if isinstance(sent, str):
                    sents[idx] = sents[idx].split(m)
            # flatten list
            sents = flatten_list(sents)
        return sents

    @staticmethod
    def extract_candidates(text, lang="en", split_at_commas=False, split_at_punc=False):
        sents = sentence_tokenize(text)

        markers = []
        if split_at_commas:
            markers += [", ", "; "]
        if split_at_punc:
            markers += [". ", "! ", "? "]
        if lang.startswith("en"):
            markers += Segmenter.SEGMENTATION_MARKERS_EN
        elif lang.startswith("pt"):
            markers += Segmenter.SEGMENTATION_MARKERS_PT

        if markers:
            return Segmenter.__extract(sents, markers)
        return sents

    def segment(self, text):
        split_at_commas = self.config.get("split_commas", False)
        split_at_punc = self.config.get("split_punc", False)
        return [s.strip() for s in self.extract_candidates(
            text, lang=self.lang, split_at_commas=split_at_commas,
            split_at_punc=split_at_punc) if s]
