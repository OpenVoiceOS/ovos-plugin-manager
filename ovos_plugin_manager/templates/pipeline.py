import abc
from collections import namedtuple

from ovos_config import Configuration

from ovos_bus_client.message import Message

from ovos_utils import classproperty


# Intent match response tuple containing
# intent_service: Name of the service that matched the intent
# intent_type: intent name (used to call intent handler over the message bus)
# intent_data: data provided by the intent match
# skill_id: the skill this handler belongs to
IntentMatch = namedtuple('IntentMatch',
                         ['intent_service', 'intent_type',
                          'intent_data', 'skill_id', 'utterance']
                         )


class PipelineComponentPlugin:

    def __init__(self, bus, config=None):
        self.config = config or \
                      Configuration().get("pipeline", {}).get(self.matcher_id)
        self.bus = bus
        self.register_bus_events()

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


class PipelineMultiConfPlugin(PipelineComponentPlugin):

    def match(self, utterances: list, lang: str, message: Message):
        return self.match_high(utterances, lang, message)

    @abc.abstractmethod
    def match_high(self, utterances: list, lang: str, message: Message) -> IntentMatch:
        pass

    @abc.abstractmethod
    def match_medium(self, utterances: list, lang: str, message: Message) -> IntentMatch:
        pass

    @abc.abstractmethod
    def match_low(self, utterances: list, lang: str, message: Message) -> IntentMatch:
        pass
