from ovos_bus_client.message import dig_for_message
from ovos_utils import classproperty
from ovos_utils.lang import standardize_lang_tag
from ovos_utils.process_utils import RuntimeRequirements


class PosTagger:
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
        return standardize_lang_tag(lang or "en-US")

    def postag(self, spans, lang=None):
        lang = standardize_lang_tag(lang or self.lang)
        # this should be implemented by plugins!
        if lang.startswith("pt"):
            return _dummy_postag_pt(spans)
        elif lang.startswith("en"):
            return _dummy_postag_en(spans)
        return _dummy_postag(spans)


def _dummy_postag_pt(spans):
    pos = []
    for s, e, t in spans:
        if t == "e":
            pos.append((s, e, t, "CONJ"))
        elif t in ["o", "a", "os", "as"]:
            pos.append((s, e, t, "DET"))
        elif t.lower() in ["ele", "ela", "eles", "elas", "nós", "vós"]:
            pos.append((s, e, t, "PRON"))
        elif t in ["do", "da", "dos", "das"]:
            pos.append((s, e, t, "ADP"))
        elif t.isdigit():
            pos.append((s, e, t, "NUMBER"))
        elif t[0].isupper() and len(t) >= 5:
            pos.append((s, e, t, "PROPN"))
        elif len(t) >= 4:
            pos.append((s, e, t, "NOUN"))
        else:
            pos.append((s, e, t, "VERB"))
    return pos


def _dummy_postag_en(spans):
    pos = []
    for s, e, t in spans:
        if t == "and":
            pos.append((s, e, t, "CONJ"))
        elif t in ["the", "a", "an"]:
            pos.append((s, e, t, "DET"))
        elif t.lower() in ["he", "she", "it", "they"]:
            pos.append((s, e, t, "PRON"))
        elif t in ["of", "for"]:
            pos.append((s, e, t, "ADP"))
        elif t.isdigit():
            pos.append((s, e, t, "NUMBER"))
        elif t[0].isupper() and len(t) >= 5:
            pos.append((s, e, t, "PROPN"))
        elif len(t) >= 4:
            pos.append((s, e, t, "NOUN"))
        else:
            pos.append((s, e, t, "VERB"))
    return pos


def _dummy_postag(spans):
    pos = []
    for s, e, t in spans:
        if t.isdigit():
            pos.append((s, e, t, "NUMBER"))
        elif t[0].isupper() and len(t) >= 4:
            pos.append((s, e, t, "PROPN"))
        elif len(t) >= 5:
            pos.append((s, e, t, "NOUN"))
        else:
            pos.append((s, e, t, "VERB"))
    return pos
