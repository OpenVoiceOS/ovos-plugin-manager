import abc
from dataclasses import dataclass
from typing import Optional, Dict, List, Union

from ovos_bus_client.message import Message
from ovos_bus_client.client import MessageBusClient
from ovos_utils.fakebus import FakeBus


@dataclass()
class IntentMatch:
    # ovos-core expects PipelinePlugins to return this data structure
    # replaces old IntentMatch response namedtuple
    # intent_service: Name of the service that matched the intent
    # intent_type: intent name (used to call intent handler over the message bus)
    # intent_data: data provided by the intent match
    # skill_id: the skill this handler belongs to
    match_type: str
    match_data: Optional[Dict] = None
    skill_id: Optional[str] = None
    utterance: Optional[str] = None


@dataclass()
class PipelineMatch(IntentMatch):
    # same as above, but does not emit intent message on match
    # the process of matching already handles the utterance
    match_type: bool = True  # for compat only
    handled: bool = True
    match_data: Optional[Dict] = None
    skill_id: Optional[str] = None
    utterance: Optional[str] = None


class PipelinePlugin:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}


class ConfidenceMatcherPipeline(PipelinePlugin):
    """these plugins return a match to the utterance,
    but do not trigger an action directly during the match

     eg. adapt, padatious"""

    def __init__(self, bus: Optional[Union[MessageBusClient, FakeBus]] = None,
                 config: Optional[Dict] = None):
        self.bus = bus or FakeBus()
        super().__init__(config=config)

    @abc.abstractmethod
    def match_high(self, utterances: List[str], lang: str, message: Message) -> Optional[IntentMatch]:
        pass

    @abc.abstractmethod
    def match_medium(self, utterances: List[str], lang: str, message: Message) -> Optional[IntentMatch]:
        pass

    @abc.abstractmethod
    def match_low(self, utterances: List[str], lang: str, message: Message) -> Optional[IntentMatch]:
        pass


class PipelineStageMatcher(PipelinePlugin):
    """WARNING: has side effects when match is used

    these plugins will consume an utterance during the match process,
    aborting the next pipeline stages if a match is returned.

    it is not known if this component will match without going through the match process

    eg. converse, common_query """

    def __init__(self, bus: Optional[Union[MessageBusClient, FakeBus]] = None,
                 config: Optional[Dict] = None):
        self.bus = bus or FakeBus()
        super().__init__(config=config)

    @abc.abstractmethod
    def match(self, utterances: List[str], lang: str, message: Message) -> Optional[PipelineMatch]:
        pass


class PipelineStageConfidenceMatcher(PipelineStageMatcher, ConfidenceMatcherPipeline):
    """WARNING: has side effects when match is used

    these plugins will consume an utterance during the match process,
    aborting the next pipeline stages if a match is returned.

    it is not known if this component will match without going through the match process

    eg. fallback, stop """

    def __init__(self, bus: Optional[Union[MessageBusClient, FakeBus]] = None,
                 config: Optional[Dict] = None):
        super().__init__(bus=bus, config=config)

    def match(self, utterances: List[str], lang: str, message: Message) -> Optional[PipelineMatch]:
        # no match level specified, method still needs to be implmented since its a subclass of PipelineStageMatcher
        return self.match_high(utterances, lang, message)

    @abc.abstractmethod
    def match_high(self, utterances: List[str], lang: str, message: Message) -> Optional[PipelineMatch]:
        pass

    @abc.abstractmethod
    def match_medium(self, utterances: List[str], lang: str, message: Message) -> Optional[PipelineMatch]:
        pass

    @abc.abstractmethod
    def match_low(self, utterances: List[str], lang: str, message: Message) -> Optional[PipelineMatch]:
        pass
