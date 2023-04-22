import enum
import re
from collections import namedtuple
from ovos_config import Configuration
from ovos_utils import flatten_list
from ovos_utils.json_helper import merge_dict
from ovos_utils.log import LOG
from quebra_frases import word_tokenize, get_exclusive_tokens

from ovos_bus_client.util import get_message_lang
from ovos_plugin_manager.segmentation import OVOSUtteranceSegmenterFactory

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


class BaseDefinition:
    def __init__(self, name, lang):
        self.name = name
        self.lang = lang


class EntityDefinition(BaseDefinition):
    def __init__(self, name, lang, samples=None):
        super().__init__(name, lang)
        self.samples = samples or [name]


class IntentDefinition(BaseDefinition):
    def __init__(self, name, lang, samples=None):
        super().__init__(name, lang)
        self.samples = samples or [name]


class RegexEntityDefinition(BaseDefinition):
    def __init__(self, name, lang, patterns):
        super().__init__(name, lang)
        self.patterns = patterns


class RegexIntentDefinition(BaseDefinition):
    def __init__(self, name, lang, patterns=None):
        super().__init__(name, lang)
        self.patterns = patterns or []


class KeywordIntentDefinition(BaseDefinition):
    def __init__(self, name, lang, requires,
                 optional=None, at_least_one=None, excluded=None):
        super().__init__(name, lang)
        self.requires = requires
        self.optional = optional or []
        self.excluded = excluded or []
        self.at_least_one = at_least_one or []


class IntentExtractor:
    def __init__(self, config=None,
                 strategy=IntentDeterminationStrategy.SEGMENT_REMAINDER,
                 priority=IntentPriority.LOW,
                 segmenter=None):
        self.config = config or {}
        self.segmenter = segmenter or OVOSUtteranceSegmenterFactory.create()
        self.strategy = strategy
        self.priority = priority

        # sample based
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

    def get_intent_samples(self, intent_name, lang=None):
        lang = lang or self.lang
        for e in [e for e in self.registered_intents if isinstance(e, IntentDefinition)]:
            if e.name == intent_name and e.lang == lang:
                return e.samples
        return []

    def get_entity_samples(self, entity_name, lang=None):
        lang = lang or self.lang
        for e in [e for e in self.registered_entities if isinstance(e, EntityDefinition)]:
            if e.name == entity_name and e.lang == lang:
                return e.samples
        return []

    # registering/unloading intents
    def detach_skill(self, skill_id):
        for i in [e for e in self.registered_intents
                  if e.name.startswith(skill_id)]:
            self.detach_intent(i.name)

        for i in [e for e in self.registered_entities
                  if e.name.startswith(skill_id)]:
            self.detach_entity(i.name)

    def detach_entity(self, entity_name):
        self.registered_entities = [e for e in self.registered_entities
                                    if e.name != entity_name]

    def detach_intent(self, intent_name):
        self.registered_intents = [e for e in self.registered_intents
                                   if e.name != intent_name]

    def register_entity(self, entity_name, samples=None, lang=None):
        lang = lang or self.lang
        entity = EntityDefinition(entity_name, lang, samples)
        self.registered_entities.append(entity)

    def register_intent(self, intent_name, samples=None, lang=None):
        lang = lang or self.lang
        intent = IntentDefinition(intent_name, lang, samples)
        self.registered_intents.append(intent)

    def register_keyword_intent(self, intent_name, keywords,
                                optional=None, at_least_one=None,
                                excluded=None, lang=None):
        lang = lang or self.lang
        intent = KeywordIntentDefinition(intent_name, lang,
                                         requires=keywords, optional=optional,
                                         at_least_one=at_least_one, excluded=excluded)
        self.registered_intents.append(intent)

    def register_regex_entity(self, entity_name, samples,
                              lang=None):
        lang = lang or self.lang
        entity = RegexEntityDefinition(entity_name, lang,
                                       patterns=[re.compile(pattern) for pattern in samples])
        self.registered_entities.append(entity)

    def register_regex_intent(self, intent_name, samples,
                              lang=None):
        lang = lang or self.lang
        intent = RegexIntentDefinition(intent_name, lang,
                                       patterns=[re.compile(pattern) for pattern in samples])
        self.registered_intents.append(intent)

    # from file helper methods
    def register_entity_from_file(self, entity_name, file_name,
                                  lang=None):
        with open(file_name) as f:
            entities = f.read().split("\n")
            self.register_entity(entity_name, entities,
                                 lang=lang)

    def register_intent_from_file(self, intent_name, file_name,
                                  lang=None):
        with open(file_name) as f:
            intents = f.read().split("\n")
            self.register_intent(intent_name, intents,
                                 lang=lang)

    def register_regex_entity_from_file(self, entity_name, file_name,
                                        lang=None):
        with open(file_name) as f:
            entities = f.read().split("\n")
            self.register_regex_entity(entity_name, entities,
                                       lang=lang)

    def register_regex_intent_from_file(self, intent_name, file_name,
                                        lang=None):
        with open(file_name) as f:
            intents = f.read().split("\n")
            self.register_regex_intent(intent_name, intents,
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

    def calc_intent(self, utterance, min_conf=0.5, lang=None, session=None):
        """ return intent result for utterance
        UTTERANCE: tell me a joke and say hello
        {'name': 'joke', 'sent': 'tell me a joke and say hello', 'matches': {}, 'conf': 0.5634853146417653}
        """
        raise NotImplementedError

    def calc_intents(self, utterance, min_conf=0.5, lang=None, session=None):
        """ segment utterance and return best intent for individual segments
        if confidence is below min_conf intent is None

       UTTERANCE: tell me a joke and say hello
        {'say hello': {'conf': 0.5750943775957492, 'matches': {}, 'name': 'hello'},
         'tell me a joke': {'conf': 1.0, 'matches': {}, 'name': 'joke'}}
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

        :param utterance:
        :param _prev:
        :return:
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
        segment utterance and for each chunk recursively check for intents in utterance remainer

        :param utterance:
        :param min_conf:
        :return:
        """
        lang = lang or self.lang
        utterances = self.segmenter.segment(utterance)
        bucket = []
        for utterance in utterances:
            bucket += self.intent_remainder(utterance, min_conf=min_conf, lang=lang, session=session)
        return [b for b in bucket if b]

    def intent_scores(self, utterance, lang=None, session=None):
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
        """
        lang = lang or self.lang
        return [i for i in self.intent_scores(utterance, lang=lang, session=session) if
                i["conf"] >= min_conf]

    def calc(self, utterance, min_conf=0.5, lang=None, session=None):
        """
        segment utterance and for each chunk recursively check for intents in utterance remainer
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


class IntentEngine:
    def __init__(self, engine_id, config=None, bus=None, engine=None):
        self.engine_id = engine_id
        self.bus = bus
        self.engine = engine
        self.config = config or Configuration().get("intents", {}).get(engine_id, {})
        if bus:
            self.bind(bus, engine)

    def bind(self, bus=None, engine=None):
        engine = engine or self.engine
        if engine is None:
            from ovos_plugin_manager.intents import load_intent_engine
            engine = load_intent_engine(self.engine_id, self.config)
        self.engine = engine
        self.bus = bus or self.bus
        self.register_bus_handlers()
        self.register_compat_bus_handlers()

    def register_bus_handlers(self):
        self.bus.on('ovos.intentbox.register.entity', self.handle_register_entity)
        self.bus.on('ovos.intentbox.register.intent', self.handle_register_intent)
        self.bus.on('ovos.intentbox.register.keyword_intent', self.handle_register_keyword_intent)
        self.bus.on("ovos.intentbox.register.regex_intent", self.handle_register_regex_intent)

        self.bus.on('ovos.intentbox.detach.entity', self.handle_detach_entity)
        self.bus.on('ovos.intentbox.detach.intent', self.handle_detach_intent)
        self.bus.on('ovos.intentbox.detach.skill', self.handle_detach_skill)

        self.bus.on(f'ovos.intentbox.get.intent.{self.engine_id}', self.handle_get_intent)
        self.bus.on(f'ovos.intentbox.get.manifest.{self.engine_id}', self.handle_get_manifest)

    def register_compat_bus_handlers(self):
        """mycroft compatible namespaces"""
        self.bus.on('detach_intent', self.handle_detach_intent)  # api compatible
        self.bus.on('detach_skill', self.handle_detach_skill)  # api compatible
        # adapt api
        self.bus.on('register_vocab', self.handle_register_adapt_vocab)
        self.bus.on('register_intent', self.handle_register_keyword_intent)  # api compatible
        # padatious api
        self.bus.on('padatious:register_intent', self.handle_register_intent)  # api compatible
        self.bus.on('padatious:register_entity', self.handle_register_entity)  # api compatible

    @property
    def priority(self):
        if self.engine:
            return self.engine.priority
        return IntentPriority.FALLBACK_LOW

    def train(self):
        if self.engine:
            self.engine.train()

    def handle_utterance_message(self, message):
        utterances = message.data["utterances"]
        lang = get_message_lang(message)
        good_utterance = False
        if self.engine:
            for utterance in utterances:
                for intent in self.engine.calc(utterance, lang=lang):
                    intent_type = intent["intent_type"]
                    yield IntentMatch(self.engine_id, intent_type, intent)
                    good_utterance = True
                if good_utterance:
                    break

    # bus handlers
    @staticmethod
    def _parse_message(message):
        name = message.data["name"]
        lang = get_message_lang(message)
        samples = message.data.get("samples") or []
        if not samples and message.data.get("file_name"):
            with open(message.data["file_name"]) as f:
                samples = [l for l in f.read().split("\n")
                           if l and not l.startswith("#")]
        samples = samples or [name]

        return name, samples, lang

    def handle_register_intent(self, message):
        intent_name, samples, lang = self._parse_message(message)
        if self.engine:
            self.engine.register_intent(intent_name, samples, lang)

    def handle_register_entity(self, message):
        entity_name = message.data["name"]
        lang = get_message_lang(message)
        samples = message.data.get("samples") or []
        if not samples and message.data.get("file_name"):
            with open(message.data["file_name"]) as f:
                samples = [l for l in f.read().split("\n")
                           if l and not l.startswith("#")]
        samples = samples or [entity_name]
        if self.engine:
            self.engine.register_entity(entity_name, samples, lang)

    def handle_register_regex_intent(self, message):
        intent_name, samples, lang = self._parse_message(message)
        if self.engine:
            self.engine.register_regex_intent(intent_name, samples, lang)

    def handle_register_regex_entity(self, message):
        entity_name, samples, lang = self._parse_message(message)
        if self.engine:
            self.engine.register_regex_entity(entity_name, samples, lang)

    def handle_register_keyword_intent(self, message):
        if self.engine:
            self.engine.register_keyword_intent(
                message.data['name'],
                [_[0] for _ in message.data['requires']],
                [_[0] for _ in message.data.get('optional', [])],
                [_[0] for _ in message.data.get('at_least_one', [])],
                [_[0] for _ in message.data.get('excludes', [])])

    def handle_detach_intent(self, message):
        intent_name = message.data.get('intent_name')
        if self.engine:
            self.engine.detach_intent(intent_name)

    def handle_detach_entity(self, message):
        name = message.data.get('name')
        if self.engine:
            self.engine.detach_entity(name)

    def handle_detach_skill(self, message):
        """Remove all intents registered for a specific skill.
        Args:
            message (Message): message containing intent info
        """
        skill_id = message.data.get('skill_id')
        if self.engine:
            self.engine.detach_skill(skill_id)

    def handle_get_intent(self, message):
        # TODO
        utterance = message.data["utterance"]
        lang = get_message_lang(message)

    def handle_get_manifest(self, message):
        # TODO
        pass

    # backwards compat bus handlers
    def handle_register_adapt_vocab(self, message):
        if 'entity_value' not in message.data and 'start' in message.data:
            message.data['entity_value'] = message.data['start']
            message.data['entity_type'] = message.data['end']
        entity_value = message.data.get('entity_value')
        entity_type = message.data.get('entity_type')
        regex_str = message.data.get('regex')
        alias_of = message.data.get('alias_of') or []
        lang = get_message_lang(message)
        if regex_str:
            if not entity_type:
                # mycroft does not send an entity_type when registering adapt regex
                # the entity name is in the regex itself, need to extract from string
                # is syntax always (?P<name>someregexhere)  ?
                entity_type = regex_str.split("(?P<")[-1].split(">")[0]
            message.data["name"] = entity_type
            message.data["samples"] = [regex_str]
            self.handle_register_regex_entity(message)
        else:
            for ent in [entity_type] + alias_of:
                message.data["name"] = ent
                message.data["samples"] = [entity_value]
                self.handle_register_entity(message)

    def __str__(self):
        return self.engine_id

    def __repr__(self):
        return f"IntentEngine:{self.engine_id}"
