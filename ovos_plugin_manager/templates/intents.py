import enum
import re
from collections import namedtuple
from mycroft_bus_client.message import dig_for_message
from ovos_utils import flatten_list
from ovos_utils.json_helper import merge_dict
from ovos_utils.log import LOG
from quebra_frases import word_tokenize, get_exclusive_tokens

from ovos_plugin_manager.segmentation import OVOSUtteranceSegmenterFactory
from ovos_plugin_manager.utils.intent_context import ContextManager

# optional imports, strongly recommended
try:
    from lingua_franca.parse import normalize as lf_normalize
except ImportError:
    lf_normalize = None

# Intent match response tuple containing
# intent_service: Name of the service that matched the intent
# intent_type: intent name
# intent_data: data provided by the intent match
# skill_id: the skill this handler belongs to
IntentMatch = namedtuple('IntentMatch',
                         ['intent_service', 'intent_type',
                          'intent_data', 'skill_id']
                         )


class IntentDeterminationStrategy(str, enum.Enum):
    SINGLE_INTENT = "single"
    REMAINDER = "remainder"
    SEGMENT = "segment"
    SEGMENT_REMAINDER = "segment+remainder"
    SEGMENT_MULTI = "segment+multi"


class IntentPriority(enum.IntEnum):
    CONVERSE = 0
    HIGH = 1
    KEYWORDS_HIGH = 2
    FALLBACK_HIGH = 3
    REGEX_HIGH = 4
    MEDIUM = 5
    KEYWORDS_MEDIUM = 6
    FALLBACK_MEDIUM = 7
    REGEX_MEDIUM = 8
    LOW = 9
    KEYWORDS_LOW = 10
    FALLBACK_LOW = 11
    REGEX_LOW= 12


class IntentExtractor:
    def __init__(self, config=None,
                 strategy=IntentDeterminationStrategy.SEGMENT_REMAINDER,
                 priority=IntentPriority.LOW,
                 segmenter=None):
        self.config = config or {}
        self.segmenter = segmenter or OVOSUtteranceSegmenterFactory.create()
        self.strategy = strategy
        self.priority = priority

        self._intent_samples = {}
        self.registered_intents = []
        self.registered_entities = {}
        self.patterns = {}
        self.entity_patterns = {}

        # Context related initializations
        # the context manager is from adapt, however it can be used by any
        # intent engine, in a future PR this will be generalized using
        # ContextManager.get_context and ContextManager.inject_context in
        # the self.calc methods
        self.context_config = self.config.get('context', {})
        self.context_keywords = self.context_config.get('keywords', [])
        self.context_max_frames = self.context_config.get('max_frames', 3)
        self.context_timeout = self.context_config.get('timeout', 2)
        self.context_greedy = self.context_config.get('greedy', False)
        self.context_manager = ContextManager(self.context_timeout)

    @property
    def lang(self):
        lang = self.config.get("lang")
        msg = dig_for_message()
        if msg:
            lang = msg.data.get("lang")
        return lang or "en-us"

    @property
    def intent_samples(self):
        return self._intent_samples

    def normalize_utterance(self, text, lang='', remove_articles=False):
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

    def get_normalizations(self, utterance, lang=None):
        lang = lang or self.lang
        norm = self.normalize_utterance(utterance, remove_articles=True, lang=lang)
        norm2 = self.normalize_utterance(utterance, remove_articles=False, lang=lang)
        norm3 = re.sub(r'[^\w]', ' ', utterance)
        norm4 = ''.join([i if 64 < ord(i) < 128 or ord(i) == 32
                         else '' for i in utterance])
        return [u for u in [norm, norm2, norm3, norm4] if u != utterance]

    def get_utterance_remainder(self, utterance, samples, as_string=True):
        chunks = get_exclusive_tokens([utterance] + samples)
        words = [t for t in word_tokenize(utterance) if t in chunks]
        if as_string:
            return " ".join(words)
        return words

    def detach_skill(self, skill_id):
        remove_list = [i for i in self.registered_intents if skill_id in i]
        for i in remove_list:
            self.detach_intent(i)

    def detach_intent(self, intent_name):
        if intent_name in self.registered_intents:
            self.registered_intents.remove(intent_name)

    def register_entity(self, entity_name, samples=None):
        samples = samples or [entity_name]
        if entity_name not in self.registered_entities:
            self.registered_entities[entity_name] = []
        self.registered_entities[entity_name] += samples

    def register_intent(self, intent_name, samples=None):
        samples = samples or [intent_name]
        if intent_name not in self._intent_samples:
            self._intent_samples[intent_name] = samples
        else:
            self._intent_samples[intent_name] += samples
        self.registered_intents.append(intent_name)

    def register_regex_entity(self, entity_name, samples):
        if entity_name not in self.patterns:
            self.entity_patterns[entity_name] = []
        self.entity_patterns[entity_name] += [re.compile(pattern)
                                              for pattern in samples]

    def register_regex_intent(self, intent_name, samples):
        if intent_name not in self.patterns:
            self.patterns[intent_name] = []
        self.patterns[intent_name] += [re.compile(pattern)
                                       for pattern in samples]

    def register_entity_from_file(self, entity_name, file_name):
        with open(file_name) as f:
            entities = f.read().split("\n")
            self.register_entity(entity_name, entities)

    def register_intent_from_file(self, intent_name, file_name):
        with open(file_name) as f:
            intents = f.read().split("\n")
            self.register_entity(intent_name, intents)

    def register_regex_entity_from_file(self, entity_name, file_name):
        with open(file_name) as f:
            entities = f.read().split("\n")
            self.register_regex_entity(entity_name, entities)

    def register_regex_intent_from_file(self, intent_name, file_name):
        with open(file_name) as f:
            intents = f.read().split("\n")
            self.register_regex_entity(intent_name, intents)

    def extract_regex_entities(self, utterance):
        entities = {}
        utterance = utterance.strip().lower()
        for name, patterns in self.entity_patterns.items():
            for pattern in patterns:
                match = pattern.match(utterance)
                if match:
                    entities = merge_dict(entities, match.groupdict())
        return entities

    def calc_intent(self, utterance, min_conf=0.0):
        """ return intent result for utterance
        UTTERANCE: tell me a joke and say hello
        {'name': 'joke', 'sent': 'tell me a joke and say hello', 'matches': {}, 'conf': 0.5634853146417653}
        """
        raise NotImplementedError

    def calc_intents(self, utterance, min_conf=0.0):
        """ segment utterance and return best intent for individual segments
        if confidence is below min_conf intent is None

       UTTERANCE: tell me a joke and say hello
        {'say hello': {'conf': 0.5750943775957492, 'matches': {}, 'name': 'hello'},
         'tell me a joke': {'conf': 1.0, 'matches': {}, 'name': 'joke'}}

        """
        bucket = {}
        for ut in self.segmenter.segment(utterance):
            intent = self.calc_intent(ut, min_conf=min_conf)
            bucket[ut] = intent
        return bucket

    def calc_intents_list(self, utterance, min_conf=0.0):
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

        """
        utterance = utterance.strip().lower()
        bucket = {}
        for ut in self.segmenter.segment(utterance):
            bucket[ut] = self.filter_intents(ut, min_conf=min_conf)
        return bucket

    def intent_remainder(self, utterance, _prev="", min_conf=0.0):
        """
        calc intent, remove matches from utterance, check for intent in leftover, repeat

        :param utterance:
        :param _prev:
        :return:
        """
        intent_bucket = []
        while _prev != utterance:
            _prev = utterance
            intent = self.calc_intent(utterance, min_conf)
            if intent:
                intent_bucket += [intent]
                utterance = intent['utterance_remainder']
        return intent_bucket

    def intents_remainder(self, utterance, min_conf=0.0):
        """
        segment utterance and for each chunk recursively check for intents in utterance remainer

        :param utterance:
        :param min_conf:
        :return:
        """
        utterances = self.segmenter.segment(utterance)
        bucket = []
        for utterance in utterances:
            bucket += self.intent_remainder(utterance, min_conf=min_conf)
        return [b for b in bucket if b]

    def intent_scores(self, utterance):
        utterance = utterance.strip().lower()
        intents = []
        bucket = self.calc_intents(utterance)
        for utt in bucket:
            intent = bucket[utt]
            if not intent:
                continue
            intents.append(intent)
        return intents

    def filter_intents(self, utterance, min_conf=0.0):
        """
        returns all intents above a minimum confidence, meant for disambiguation

        can somewhat be used for multi intent parsing

        UTTERANCE: close the door turn off the lights
        [{'conf': 0.5311372507542608, 'entities': {}, 'name': 'lights_off'},
         {'conf': 0.505765852348431, 'entities': {}, 'name': 'door_close'}]
        """
        return [i for i in self.intent_scores(utterance) if
                i["conf"] >= min_conf]

    def calc(self, utterance):
        """
        segment utterance and for each chunk recursively check for intents in utterance remainer
        """
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
                intents = self.intent_remainder(utterance)  # up to 2 intents

                # use a bigger chunk of the utterance
                if not intents and prev_ut:
                    # TODO ensure original utterance form
                    # TODO lang support
                    intents = self.intent_remainder(prev_ut + " " + utterance)
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
                bucket.append([self.calc_intent(utterance)])

            # calc multiple intents over full utterance
            # "segment+multi" is misleading in the sense that
            # individual intent engines should do the segmentation
            # if this strategy is selected the segmenter step is skipped
            # and there is only 1 utterance
            else:
                intents = [intent for ut, intent in
                           self.calc_intents(utterance).items()]
                bucket.append(intents)

        return [i for i in flatten_list(bucket) if i]

    def manifest(self):
        return {
            "intent_names": self.registered_intents,
            "entities": self.registered_entities,
            "patterns": self.patterns,
            "entity_patterns": self.entity_patterns
        }
