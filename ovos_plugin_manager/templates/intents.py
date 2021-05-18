import abc
import re


class IntentEngine:
    keyword_based = False
    regex_entity_support = False

    def __init__(self, config=None, auto_train=False, engine_id=None):
        self.config = config or {}
        self._intent_samples = {}
        self.registered_intents = []
        self.registered_entities = {}
        self.regexes = {}
        self.auto_train = auto_train
        self.engine_id = engine_id or self.__class__.__name__

    @property
    def intent_samples(self):
        return self._intent_samples

    @property
    def manifest(self):
        return {
            "intent_names": self.registered_intents,
            "entities": self.registered_entities,
            "regex_entities": self.regexes
        }

    @staticmethod
    def get_normalizations(utterance, lang=None):
        norms = [utterance]
        if lang:
            try:
                from lingua_nostra.parse import normalize
                norms.append(normalize(utterance, lang=lang))
            except ImportError:
                pass

            try:
                from lingua_franca.parse import normalize
                norms.append(normalize(utterance, remove_articles=True,
                                       lang=lang))
                norms.append(normalize(utterance, remove_articles=False,
                                       lang=lang))
            except ImportError:
                pass
        norms.append(re.sub(r'[^\w]', ' ', utterance))
        norms.append(''.join([i if 64 < ord(i) < 128 or ord(i) == 32
                              else '' for i in utterance]))
        return list(set(norms))

    def detach_skill(self, skill_id):
        remove_list = [i for i in self.registered_intents
                       if i.startswith(skill_id)]
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

    def register_regex_entity(self, entity_name, samples):
        if isinstance(samples, str):
            samples = [samples]
        if entity_name not in self.regexes:
            self.regexes[entity_name] = []
        self.regexes[entity_name] += samples

    def register_intent(self, intent_name, samples=None):
        samples = samples or [intent_name]
        if intent_name not in self._intent_samples:
            self._intent_samples[intent_name] = samples
        else:
            self._intent_samples[intent_name] += samples
        self.registered_intents.append(intent_name)

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
            intents = f.read().split("\n")
            self.register_regex_entity(entity_name, intents)

    @abc.abstractmethod
    def calc_intent(self, utterance):
        """ return intent result for utterance
       UTTERANCE: tell me a joke
        {'name': 'joke',
        'sent': 'tell me a joke',
         'matches': {},
          'conf': 0.5634853146417653}

        """
        pass

    @abc.abstractmethod
    def train(self, single_thread=True, timeout=120, force_training=True):
        # in case engines need a training step this might be called
        return True
