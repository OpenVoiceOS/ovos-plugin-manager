import enum
import abc
from typing import Set

from ovos_utils import classproperty
from ovos_utils.lang.phonemes import arpabet2ipa, ipa2arpabet
from ovos_utils.lang.visimes import VISIMES
from ovos_utils.process_utils import RuntimeRequirements


class PhonemeAlphabet(str, enum.Enum):
    ARPA = "arpa"
    IPA = "ipa"


class OutOfVocabulary(ValueError):
    """ could not get phonemes for word """


class Grapheme2PhonemePlugin:
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
    def arpa_is_implemented(self):
        return self.__class__.get_arpa is not Grapheme2PhonemePlugin.get_arpa

    @property
    def ipa_is_implemented(self):
        return self.__class__.get_ipa is not Grapheme2PhonemePlugin.get_ipa

    def get_arpa(self, word, lang, ignore_oov=False):
        # if ipa is implemented, use it and convert
        if self.ipa_is_implemented:
            ipa = self.get_ipa(word, lang)
            norm = lambda k: k.replace('ˈ', "")
            return [ipa2arpabet[norm(p)] for p in ipa
                    if norm(p) in ipa2arpabet]
        if ignore_oov:
            return None
        raise OutOfVocabulary

    def get_ipa(self, word, lang, ignore_oov=False):
        # if arpa is implemented, use it and convert
        if self.arpa_is_implemented:
            arpa = self.get_arpa(word, lang)
            norm = lambda k: k.replace("9", "") \
                .replace("8", "") \
                .replace("7", "") \
                .replace("6", "") \
                .replace("5", "") \
                .replace("4", "") \
                .replace("3", "") \
                .replace("2", "") \
                .replace("1", "") \
                .replace("0", "")
            return [arpabet2ipa[norm(p)] for p in arpa
                    if norm(p) in arpabet2ipa]
        if ignore_oov:
            return None
        raise OutOfVocabulary

    def utterance2arpa(self, utterance, lang, ignore_oov=False):
        arpa = []
        for w in utterance.split():
            phones = self.get_arpa(w, lang, ignore_oov) or []
            if not phones and not ignore_oov:
                raise OutOfVocabulary(f"unknown word: {w}")
            arpa += phones + ["."]
        if arpa:
            return arpa[:-1]
        if ignore_oov:
            return None
        raise OutOfVocabulary

    def utterance2ipa(self, utterance, lang, ignore_oov=False):
        ipa = []
        for w in utterance.split():
            phones = self.get_ipa(w, lang, ignore_oov) or []
            if not phones and not ignore_oov:
                raise OutOfVocabulary(f"unknown word: {w}")
            ipa += phones + ["."]
        if ipa:
            return ipa[:-1]
        if ignore_oov:
            return None
        raise OutOfVocabulary

    def utterance2visemes(self, utterance, lang, default_dur=0.4):
        arpa = []
        for w in utterance.split():
            phones = self.get_arpa(w, lang) or \
                     ['B', 'L', 'AE', '.', 'B', 'L', 'AE']
            arpa += phones + ["."]
        return [(VISIMES.get(pho.lower(), '4'), default_dur) for pho in arpa]

    @classproperty
    @abc.abstractmethod
    def available_languages(cls) -> Set[str]:
        """Return languages supported by this G2P implementation in this state
        This property should be overridden by the derived class to advertise
        what languages that engine supports.
        Returns:
            set: supported languages
        """
