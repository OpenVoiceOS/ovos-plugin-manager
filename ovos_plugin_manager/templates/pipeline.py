import abc
import re
from dataclasses import dataclass

from ovos_config import Configuration

from ovos_bus_client.message import Message
from ovos_utils import classproperty
from ovos_utils.messagebus import get_message_lang


@dataclass()
class IntentMatch:  # replaces the named tuple from classic mycroft
    intent_service: str
    intent_type: str
    intent_data: dict
    skill_id: str
    utterance: str
    confidence: float = 0.0
    utterance_remainder: str = ""  # unconsumed text / leftover utterance


class PipelinePlugin:
    """these plugins return a match to the utterance, but do not trigger an action """

    def __init__(self, bus, config=None):
        self.config = config or \
                      Configuration().get("pipeline", {}).get(self.matcher_id)
        self.bus = bus
        self.register_bus_events()

    @property  # magic property - take session data into account
    def lang(self):
        return get_message_lang() or \
            self.config.get("lang") or \
            "en-us"

    @property
    def valid_languages(self):
        core_config = Configuration()
        lang = core_config.get("lang", "en-us")
        langs = core_config.get('secondary_langs') or []
        if lang not in langs:
            langs.insert(0, lang)
        return langs

    @classproperty
    def matcher_id(self):
        raise NotImplementedError

    def register_bus_events(self):
        pass

    @abc.abstractmethod
    def match(self, utterances: list, lang: str, message: Message) -> IntentMatch:
        pass

    def shutdown(self):
        pass

    # helpers to filter matches by confidence
    # exposed in pipeline config under mycroft.conf as {matcher_id}_high/medium/low
    def match_high(self, utterances: list, lang: str, message: Message) -> IntentMatch:
        thresh = 0.9  # TODO - from config
        match = self.match(utterances, lang, message)
        if match.confidence >= thresh:
            return match

    def match_medium(self, utterances: list, lang: str, message: Message) -> IntentMatch:
        thresh = 0.75  # TODO - from config
        match = self.match(utterances, lang, message)
        if match.confidence >= thresh:
            return match

    def match_low(self, utterances: list, lang: str, message: Message) -> IntentMatch:
        thresh = 0.5  # TODO - from config
        match = self.match(utterances, lang, message)
        if match.confidence >= thresh:
            return match


class PipelineStagePlugin(PipelinePlugin):
    """WARNING: has side effects when match is used

    these plugins will consume an utterance during the match process,
    aborting the next pipeline stages if a match is returned.

    it is not known if this component will match without going through the match process

    eg. converse, fallback """


class IntentPipelinePlugin(PipelinePlugin):

    def __init__(self, bus, config=None):
        super().__init__(bus, config)
        self.registered_intents = []
        self.registered_entities = []
        self.register_intent_bus_handlers()

    def register_intent_bus_handlers(self):
        self.bus.on('intent.service:detach_intent', self.handle_detach_intent)
        self.bus.on('intent.service:detach_entity', self.handle_detach_entity)
        self.bus.on('intent.service:detach_skill', self.handle_detach_skill)
        self.bus.on('intent.service.register_intent', self.handle_register_intent)
        self.bus.on('intent.service.register_keyword_intent', self.handle_register_keyword_intent)
        self.bus.on('intent.service.register_regex_intent', self.handle_register_regex_intent)
        self.bus.on('intent.service:register_entity', self.handle_register_entity)
        self.bus.on('intent.service:register_regex_entity', self.handle_register_regex_entity)

        # backwards compat handlers with adapt/padatious namespace
        # TODO - deprecate in ovos-core 0.1.0
        self.bus.on('padatious:register_intent', self.handle_register_intent)
        self.bus.on('padatious:register_entity', self.handle_register_entity)
        self.bus.on('register_vocab', self._handle_adapt_vocab)
        self.bus.on('register_intent', self.handle_register_keyword_intent)
        self.bus.on('detach_intent', self.handle_detach_intent)
        self.bus.on('detach_skill', self.handle_detach_skill)

    # default bus handlers
    def handle_register_keyword_intent(self, message):
        skill_id = message.data.get("skill_id") or message.context.get("skill_id")
        name = message.data["name"]
        requires = message.data["requires"]
        at_least_one = message.data.get("at_least_one", [])
        optional = message.data.get("optional", [])
        excludes = message.data.get("excludes", [])
        self.register_keyword_intent(skill_id=skill_id, intent_name=name, required=requires,
                                     at_least_one=at_least_one, optional=optional,
                                     excluded=excludes)

    def handle_register_intent(self, message):
        """Register intents

        message.data:
            samples: list of natural language spoken utterances
            name: the type/tag of an entity instance

        Args:
            message (Message): message containing intent info
        """
        skill_id = message.data.get("skill_id") or message.context.get("skill_id")
        samples = message.data["samples"]
        intent_type = message.data.get('name')

        self.register_intent(skill_id=skill_id,
                             intent_name=intent_type,
                             samples=samples,
                             lang=self.lang)

    def handle_register_regex_intent(self, message):
        """Register intents

        message.data:
            samples: regex patterns to match the intent
            name: the type/tag of an entity instance

        Args:
            message (Message): message containing intent info
        """
        skill_id = message.data.get("skill_id") or message.context.get("skill_id")
        samples = message.data["samples"]
        intent_type = message.data.get('name')

        self.register_regex_intent(skill_id=skill_id,
                                   intent_name=intent_type,
                                   samples=samples,
                                   lang=self.lang)

    def handle_register_entity(self, message):
        """Register entities.

        message.data:
            samples: list of natural language words / entity examples
            name: the type/tag of an entity instance

        Args:
            message (Message): message containing vocab info
        """
        skill_id = message.data.get("skill_id") or message.context.get("skill_id")
        samples = message.data["samples"]
        entity_type = message.data.get('name')

        self.register_entity(skill_id=skill_id,
                             entity_name=entity_type,
                             samples=samples,
                             lang=self.lang)

    def handle_register_regex_entity(self, message):
        """Register regex entities.

        message.data:
            samples: list of regex expressions that extract the entity
            name: the type/tag of an entity instance

        Args:
            message (Message): message containing vocab info
        """
        skill_id = message.data.get("skill_id") or message.context.get("skill_id")
        samples = message.data["samples"]
        entity_type = message.data.get('name')

        self.register_regex_entity(skill_id=skill_id,
                                   entity_name=entity_type,
                                   samples=samples,
                                   lang=self.lang)

    def handle_detach_entity(self, message):
        skill_id = message.data["skill_id"]
        entity_name = message.data["name"]
        self.detach_entity(skill_id, entity_name)
        self.train()

    def handle_detach_intent(self, message):
        skill_id = message.data["skill_id"]
        intent_name = message.data.get("name") or \
                      message.data.get('intent_name')  # adapt/padatious compat
        self.detach_intent(skill_id, intent_name)
        self.train()

    def handle_detach_skill(self, message):
        skill_id = message.data["skill_id"]
        self.detach_skill(skill_id)
        self.train()

    # backwards compat bus handlers to keep around until ovos-core 0.1.0
    def _handle_adapt_vocab(self, message):
        """Register adapt-like vocabulary.

         This will handle both regex registration and registration of normal
        keywords. if the "regex_str" argument is set all other arguments will
        be ignored.

        message.data:
            entity_value: the natural language word
            samples: list of entity_values
            regex: a regex pattern to extract the entity with
            entity_type: the type/tag of an entity instance
            alias_of: entity this is an alternative for

        Args:
            message (Message): message containing vocab info
        """
        skill_id = message.data.get("skill_id") or message.context.get("skill_id")
        is_r = False
        if "samples" in message.data:
            samples = message.data["samples"]
        elif "regex" in message.data:
            samples = [message.data["regex"]]
            is_r = True
        else:
            entity_value = message.data.get('entity_value')
            samples = [entity_value]

        entity_type = message.data.get('entity_type')
        alias_of = message.data.get('alias_of')

        if is_r:  # regex
            self.register_regex_entity(skill_id=skill_id,
                                       entity_name=entity_type,
                                       samples=samples,
                                       lang=self.lang)
            if alias_of:
                self.register_regex_entity(skill_id=skill_id,
                                           entity_name=alias_of,
                                           samples=samples,
                                           lang=self.lang)

        else:
            self.register_entity(skill_id=skill_id,
                                 entity_name=entity_type,
                                 samples=samples,
                                 lang=self.lang)
            if alias_of:
                self.register_entity(skill_id=skill_id,
                                     entity_name=alias_of,
                                     samples=samples,
                                     lang=self.lang)

    # helpers to navigate registered intent data
    @property
    def manifest(self):
        # ovos-core uses this property to expose the data via messagebus
        # TODO - munge/unmmunge skill_id in name ?
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
        to_detach = [intent for intent in self.registered_intents if intent.skill_id == skill_id] + \
                    [entity for entity in self.registered_entities if entity.skill_id == skill_id]
        self.registered_entities = [e for e in self.registered_entities
                                    if e not in to_detach]
        self.registered_intents = [e for e in self.registered_intents
                                   if e not in to_detach]

    def detach_entity(self, skill_id, entity_name):
        self.registered_entities = [e for e in self.registered_entities
                                    if e.name != entity_name or e.skill_id != skill_id]

    def detach_intent(self, skill_id, intent_name):
        self.registered_intents = [e for e in self.registered_intents
                                   if e.name != intent_name or e.skill_id != skill_id]

    def register_entity(self, skill_id, entity_name, samples, lang=None):
        lang = lang or self.lang
        for ent in self.registered_entities:
            if not isinstance(ent, RegexEntityDefinition) and \
                    ent.name == entity_name and \
                    ent.skill_id == skill_id and \
                    ent.lang == lang:
                # merge new samples, if not wanted detach the entity before re-registering it
                ent.samples = ent.samples + samples
                break
        else:
            entity = EntityDefinition(entity_name, lang=lang, samples=samples, skill_id=skill_id)
            self.registered_entities.append(entity)

    def register_intent(self, skill_id, intent_name, samples, lang=None):
        lang = lang or self.lang

        for ent in self.registered_entities:
            if not isinstance(ent, RegexIntentDefinition) and \
                    ent.name == intent_name and \
                    ent.skill_id == skill_id and \
                    ent.lang == lang:
                # merge new samples, if not wanted detach the intent before re-registering it
                ent.samples = ent.samples + samples
                break
        else:
            intent = IntentDefinition(intent_name, lang=lang, samples=samples, skill_id=skill_id)
            self.registered_intents.append(intent)

    def register_keyword_intent(self, skill_id, intent_name, required,
                                optional=None, at_least_one=None,
                                excluded=None, lang=None):
        lang = lang or self.lang
        intent = KeywordIntentDefinition(intent_name, lang=lang, skill_id=skill_id,
                                         requires=required, optional=optional,
                                         at_least_one=at_least_one, excluded=excluded)
        # NOTE - no merging here, we allow multiple variations of same intent with different rules to match
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

    # from_file helper methods
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

    # intent plugins api
    @abc.abstractmethod
    def train(self):
        """ plugins should parse self.registered_intents and self.registered_entities here and handle any new entries

        must be callable multiple times

        this is called on mycroft.ready and then after every new skill loads/unloads"""
        pass


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
