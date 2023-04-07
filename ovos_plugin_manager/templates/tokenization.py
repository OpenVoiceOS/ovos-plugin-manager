from ovos_bus_client.message import dig_for_message
from ovos_utils import classproperty
from ovos_utils.process_utils import RuntimeRequirements
from quebra_frases import span_indexed_word_tokenize, word_tokenize


class Tokenizer:
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

    def span_tokenize(self, text, lang=None):
        lang = lang or self.lang
        return span_indexed_word_tokenize(text)

    def tokenize(self, text, lang=None):
        lang = lang or self.lang
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
