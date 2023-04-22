import abc
import enum
import re
from dataclasses import dataclass

from ovos_bus_client.util import get_message_lang
from ovos_config import Configuration
from ovos_utils import flatten_list
from ovos_utils.json_helper import merge_dict
from ovos_utils.log import LOG
from quebra_frases import word_tokenize, get_exclusive_tokens

from ovos_plugin_manager.segmentation import OVOSUtteranceSegmenterFactory

# optional imports, strongly recommended
try:
    from lingua_franca.parse import normalize as lf_normalize
except ImportError:
    lf_normalize = None


class IntentDeterminationStrategy(str, enum.Enum):
    SINGLE_INTENT = "single"
    REMAINDER = "remainder"
    SEGMENT = "segment"
    SEGMENT_REMAINDER = "segment+remainder"
    SEGMENT_MULTI = "segment+multi"


class IntentPriority(enum.IntEnum):
    CONVERSE = 0
    HIGH = 5
    KEYWORDS_HIGH = 10
    FALLBACK_HIGH = 15
    REGEX_HIGH = 20

    MEDIUM_HIGH = 25
    KEYWORDS_MEDIUM = 30
    MEDIUM = 40
    REGEX_MEDIUM = 50
    MEDIUM_LOW = 60
    FALLBACK_MEDIUM = 70

    LOW = 75
    KEYWORDS_LOW = 80
    REGEX_LOW = 90
    FALLBACK_LOW = 100


@dataclass()
class BaseDefinition:
    name: str
    lang: str
    skill_id: str


@dataclass()
class EntityDefinition(BaseDefinition):
    samples: list


@dataclass()
class IntentDefinition(BaseDefinition):
    samples: list

    def get_utterance_remainder(self, utterance, as_string=True):
        chunks = get_exclusive_tokens([utterance] + self.samples)
        words = [t for t in word_tokenize(utterance) if t in chunks]
        if as_string:
            return " ".join(words)
        return words


@dataclass()
class RegexEntityDefinition(BaseDefinition):
    patterns: list


@dataclass()
class RegexIntentDefinition(BaseDefinition):
    patterns: list


@dataclass()
class KeywordIntentDefinition(BaseDefinition):
    requires: list
    optional: list
    excluded: list
    at_least_one: list


@dataclass()
class IntentMatch:
    intent_service: str
    intent_type: str
    intent_data: dict
    confidence: float
    skill_id: str


class IntentExtractor:
    def __init__(self, config=None,
                 strategy=IntentDeterminationStrategy.SEGMENT_REMAINDER,
                 priority=IntentPriority.LOW,
                 segmenter=None):
        self.config = config or Configuration().get("intents", {})
        self.segmenter = segmenter or OVOSUtteranceSegmenterFactory.create()
        self.strategy = strategy
        # modifier to lower confidence of individual plugins
        self.weight = self.config.get("weight", 1.0)
        self.priority = priority
        self.registered_intents = []
        self.registered_entities = []

    @property
    def lang(self):
        return get_message_lang() or \
            self.config.get("lang") or \
            "en-us"

    def normalize_utterance(self, text, lang=None, remove_articles=False):
        lang = lang or self.lang
        # use lingua_franca if installed
        if lf_normalize:
            try:
                return lf_normalize(text, lang=lang, remove_articles=remove_articles)
            except Exception as e:
                # most likely lang not loaded
                LOG.error(f"Lingua franca normalization failed!: {e}")

        # extreme fallback
        words = word_tokenize(text)
        if lang and lang.startswith("en"):
            if remove_articles:
                removals = ["the"]
                words = [w for w in words if len(w) >= 3 and w.lower() not in removals]
        return " ".join(w for w in words if w)

    def get_utterance_remainder(self, utterance, samples, as_string=True, lang=None):
        lang = lang or self.lang
        chunks = get_exclusive_tokens([utterance] + samples)
        words = [t for t in word_tokenize(utterance) if t in chunks]
        if as_string:
            return " ".join(words)
        return words

    def get_intent_samples(self, skill_id, intent_name, lang=None):
        lang = lang or self.lang
        for e in [e for e in self.registered_intents if isinstance(e, IntentDefinition)]:
            if e.name == intent_name and e.lang == lang and e.skill_id == skill_id:
                return e.samples
        return []

    def get_entity_samples(self, skill_id, entity_name, lang=None):
        lang = lang or self.lang
        for e in [e for e in self.registered_entities if isinstance(e, EntityDefinition)]:
            if e.name == entity_name and e.lang == lang and e.skill_id == skill_id:
                return e.samples
        return []

    # registering/unloading intents
    def detach_skill(self, skill_id):
        for intent in self.registered_intents:
            if intent.skill_id == skill_id:
                self.detach_intent(skill_id, intent.name)

        for entity in self.registered_entities:
            if entity.skill_id == skill_id:
                self.detach_entity(skill_id, entity.name)

    def detach_entity(self, skill_id, entity_name):
        self.registered_entities = [e for e in self.registered_entities
                                    if e.name != entity_name and e.skill_id != skill_id]

    def detach_intent(self, skill_id, intent_name):
        self.registered_intents = [e for e in self.registered_intents
                                   if e.name != intent_name and e.skill_id != skill_id]

    def register_entity(self, skill_id, entity_name, samples=None, lang=None):
        lang = lang or self.lang
        entity = EntityDefinition(entity_name, lang=lang, samples=samples, skill_id=skill_id)
        self.registered_entities.append(entity)

    def register_intent(self, skill_id, intent_name, samples=None, lang=None):
        lang = lang or self.lang
        intent = IntentDefinition(intent_name, lang=lang, samples=samples, skill_id=skill_id)
        self.registered_intents.append(intent)

    def register_keyword_intent(self, skill_id, intent_name, keywords,
                                optional=None, at_least_one=None,
                                excluded=None, lang=None):
        lang = lang or self.lang
        intent = KeywordIntentDefinition(intent_name, lang=lang, skill_id=skill_id,
                                         requires=keywords, optional=optional,
                                         at_least_one=at_least_one, excluded=excluded)
        self.registered_intents.append(intent)

    def register_regex_entity(self, skill_id, entity_name, samples,
                              lang=None):
        lang = lang or self.lang
        entity = RegexEntityDefinition(entity_name, lang=lang, skill_id=skill_id,
                                       patterns=[re.compile(pattern) for pattern in samples])
        self.registered_entities.append(entity)

    def register_regex_intent(self, skill_id, intent_name, samples,
                              lang=None):
        lang = lang or self.lang
        intent = RegexIntentDefinition(intent_name, lang=lang, skill_id=skill_id,
                                       patterns=[re.compile(pattern) for pattern in samples])
        self.registered_intents.append(intent)

    # from file helper methods
    def register_entity_from_file(self, skill_id, entity_name, file_name,
                                  lang=None):
        with open(file_name) as f:
            entities = f.read().split("\n")
            self.register_entity(skill_id, entity_name, entities,
                                 lang=lang)

    def register_intent_from_file(self, skill_id, intent_name, file_name,
                                  lang=None):
        with open(file_name) as f:
            intents = f.read().split("\n")
            self.register_intent(skill_id, intent_name, intents,
                                 lang=lang)

    def register_regex_entity_from_file(self, skill_id, entity_name, file_name,
                                        lang=None):
        with open(file_name) as f:
            entities = f.read().split("\n")
            self.register_regex_entity(skill_id, entity_name, entities,
                                       lang=lang)

    def register_regex_intent_from_file(self, skill_id, intent_name, file_name,
                                        lang=None):
        with open(file_name) as f:
            intents = f.read().split("\n")
            self.register_regex_intent(skill_id, intent_name, intents,
                                       lang=lang)

    def train(self):
        """ if the plugin needs to train on the registered data this is the place to do it"""
        pass

    # intent handling
    def extract_regex_entities(self, utterance, lang=None):
        lang = lang or self.lang
        entities = {}
        utterance = utterance.strip().lower()
        entity_patterns = [e for e in self.registered_entities
                           if isinstance(e, RegexEntityDefinition)]
        for ent in entity_patterns:
            if ent.lang != lang:
                continue
            for pattern in ent.patterns:
                match = pattern.match(utterance)
                if match:
                    entities = merge_dict(entities, match.groupdict())
        return entities

    @abc.abstractmethod
    def calc_intent(self, utterance, min_conf=0.5, lang=None, session=None):
        """ return intent result for utterance
        UTTERANCE: tell me a joke and say hello
        {'name': 'joke', 'sent': 'tell me a joke and say hello', 'matches': {}, 'conf': 0.5634853146417653}
        :return IntentMatch
        """
        raise NotImplementedError

    def calc_intents(self, utterance, min_conf=0.5, lang=None, session=None):
        """ segment utterance and return best intent for individual segments
        if confidence is below min_conf intent is None

       UTTERANCE: tell me a joke and say hello
        {'say hello': {'conf': 0.5750943775957492, 'matches': {}, 'name': 'hello'},
         'tell me a joke': {'conf': 1.0, 'matches': {}, 'name': 'joke'}}

        returns dict of subutterances and respective matches
          {"XXX": IntentMatch, "YYY": IntentMatch}
        """
        lang = lang or self.lang
        bucket = {}
        for ut in self.segmenter.segment(utterance):
            intent = self.calc_intent(ut, min_conf=min_conf, lang=lang, session=session)
            bucket[ut] = intent
        return bucket

    def calc_intents_list(self, utterance, min_conf=0.5, lang=None, session=None):
        """ segment utterance and return all intents for individual segments

       UTTERANCE: tell me a joke and say hello

        {'say hello': [{'conf': 0.1405158302488502, 'matches': {}, 'name': 'weather'},
                       {'conf': 0.5750943775957492, 'matches': {}, 'name': 'hello'},
                       {'conf': 0.0, 'matches': {}, 'name': 'name'},
                       {'conf': 0.36216947883621736, 'matches': {}, 'name': 'joke'}],
         'tell me a joke': [{'conf': 0.0, 'matches': {}, 'name': 'weather'},
                            {'conf': 0.0, 'matches': {}, 'name': 'hello'},
                            {'conf': 0.0, 'matches': {}, 'name': 'name'},
                            {'conf': 1.0, 'matches': {}, 'name': 'joke'}]}


        returns dict of subutterances and list of all matches
          {"XXX": [IntentMatch], "YYY": [IntentMatch]}
        """
        lang = lang or self.lang
        utterance = utterance.strip().lower()
        bucket = {}
        for ut in self.segmenter.segment(utterance):
            bucket[ut] = self.filter_intents(ut, min_conf=min_conf, lang=lang, session=session)
        return bucket

    def intent_remainder(self, utterance, _prev="", min_conf=0.5, lang=None, session=None):
        """
        calc intent, remove matches from utterance, check for intent in leftover, repeat

        :return: list [IntentMatch]
        """
        lang = lang or self.lang
        intent_bucket = []
        while _prev != utterance:
            _prev = utterance
            intent = self.calc_intent(utterance, min_conf=min_conf, lang=lang, session=session)
            if intent:
                intent_bucket += [intent]
                utterance = intent['utterance_remainder']
        return intent_bucket

    def intents_remainder(self, utterance, min_conf=0.5, lang=None, session=None):
        """
        segment utterance and for each chunk recursively check for intents in utterance remainder

        :return: list [IntentMatch]
        """
        lang = lang or self.lang
        utterances = self.segmenter.segment(utterance)
        bucket = []
        for utterance in utterances:
            bucket += self.intent_remainder(utterance, min_conf=min_conf, lang=lang, session=session)
        return [b for b in bucket if b]

    def intent_scores(self, utterance, lang=None, session=None):
        """
        calc_intents in list format

        :return: list [IntentMatch]
        """
        lang = lang or self.lang
        utterance = utterance.strip().lower()
        intents = []
        bucket = self.calc_intents(utterance, lang=lang, session=session)
        for utt in bucket:
            intent = bucket[utt]
            if not intent:
                continue
            intents.append(intent)
        return intents

    def filter_intents(self, utterance, min_conf=0.5, lang=None, session=None):
        """
        returns all intents above a minimum confidence, meant for disambiguation

        can somewhat be used for multi intent parsing

        UTTERANCE: close the door turn off the lights
        [{'conf': 0.5311372507542608, 'entities': {}, 'name': 'lights_off'},
         {'conf': 0.505765852348431, 'entities': {}, 'name': 'door_close'}]

        :return: list [IntentMatch]
        """
        lang = lang or self.lang
        return [i for i in self.intent_scores(utterance, lang=lang, session=session) if
                i.confidence >= min_conf]

    def calc(self, utterance, min_conf=0.5, lang=None, session=None):
        """
        segment utterance and for each chunk recursively check for intents in utterance remainder

        :return: list [IntentMatch]
        """
        lang = lang or self.lang
        if self.strategy in [IntentDeterminationStrategy.SEGMENT_REMAINDER,
                             IntentDeterminationStrategy.SEGMENT]:
            utterances = self.segmenter.segment(utterance)
            # up to N intents
        else:
            utterances = [utterance]
        prev_ut = ""
        bucket = []
        for utterance in utterances:
            # calc intent + calc intent again in leftover text
            if self.strategy in [IntentDeterminationStrategy.REMAINDER,
                                 IntentDeterminationStrategy.SEGMENT_REMAINDER]:
                intents = self.intent_remainder(utterance, min_conf=min_conf,
                                                lang=lang, session=session)  # up to 2 intents

                # use a bigger chunk of the utterance
                if not intents and prev_ut:
                    # TODO ensure original utterance form
                    # TODO lang support
                    intents = self.intent_remainder(prev_ut + " " + utterance,
                                                    min_conf=min_conf, lang=lang, session=session)
                    if intents:
                        # replace previous intent match with
                        # larger utterance segment match
                        bucket[-1] = intents
                        prev_ut = prev_ut + " " + utterance
                else:
                    prev_ut = utterance
                    bucket.append(intents)

            # calc single intent over full utterance
            # if this strategy is selected the segmenter step is skipped
            # and there is only 1 utterance
            elif self.strategy == IntentDeterminationStrategy.SINGLE_INTENT:
                bucket.append([self.calc_intent(utterance, min_conf=min_conf, lang=lang, session=session)])

            # calc multiple intents over full utterance
            # "segment+multi" is misleading in the sense that
            # individual intent engines should do the segmentation
            # if this strategy is selected the segmenter step is skipped
            # and there is only 1 utterance
            else:
                intents = [intent for ut, intent in
                           self.calc_intents(utterance, min_conf=min_conf, lang=lang, session=session).items()]
                bucket.append(intents)

        return [i for i in flatten_list(bucket) if i]

    def manifest(self):
        return {
            "intent_names": [e.name for e in self.registered_intents
                             if isinstance(e, IntentDefinition)],
            "keyword_intent_names": [e.name for e in self.registered_intents
                                     if isinstance(e, KeywordIntentDefinition)],
            "patterns": [e.name for e in self.registered_intents
                         if isinstance(e, RegexIntentDefinition)],
            "entities": [e.name for e in self.registered_entities
                         if isinstance(e, EntityDefinition)],
            "entity_patterns": [e.name for e in self.registered_entities
                                if isinstance(e, RegexEntityDefinition)],
        }


