import abc
from collections import namedtuple
from dataclasses import dataclass
from typing import Optional, Dict, List, Union

from ovos_bus_client.client import MessageBusClient
from ovos_bus_client.message import Message
from ovos_utils.fakebus import FakeBus

# LEGACY: Intent match response tuple, ovos-core~=0.2 expects PipelinePlugin to return this data structure
# intent_service: Name of the service that matched the intent
# intent_type: intent name (used to call intent handler over the message bus)
# intent_data: data provided by the intent match
# skill_id: the skill this handler belongs to
# TODO - deprecated
IntentMatch = namedtuple('IntentMatch',
                         ['intent_service', 'intent_type',
                          'intent_data', 'skill_id', 'utterance']
                         )


@dataclass
class IntentHandlerMatch:
    """
    Represents an intent handler match result, expected by ovos-core plugins.

    Attributes:
        match_type (str): Name of the service that matched the intent.
        match_data (Optional[Dict]): Additional data provided by the intent match.
        skill_id (Optional[str]): The skill this handler belongs to.
        utterance (Optional[str]): The original utterance triggering the intent.
    """
    match_type: str
    match_data: Optional[Dict] = None
    skill_id: Optional[str] = None
    utterance: Optional[str] = None


@dataclass
class PipelineMatch(IntentHandlerMatch):
    """
    Represents a match in a pipeline that does not trigger an intent message directly.

    Attributes:
        match_type (bool): Indicates if the utterance was matched (compatibility only).
        handled (bool): Whether the match has already handled the utterance.
        match_data (Optional[Dict]): Data provided by the intent match.
        skill_id (Optional[str]): The skill this handler belongs to.
        utterance (Optional[str]): The original utterance triggering the match.
    """
    handled: bool = True
    match_data: Optional[Dict] = None
    skill_id: Optional[str] = None
    utterance: Optional[str] = None
    match_type: bool = True  # compat


class PipelinePlugin:
    """
    Base class for intent matching pipeline plugins. Mainly useful for typing

    Attributes:
        config (Dict): Configuration for the plugin.
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}


class ConfidenceMatcherPipeline(PipelinePlugin):
    """
    Base class for plugins that match utterances with confidence levels,
    but do not directly trigger actions.

    Example plugins: adapt, padatious.

    Attributes:
        bus (Union[MessageBusClient, FakeBus]): The message bus client for communication.
    """

    def __init__(self, bus: Optional[Union[MessageBusClient, FakeBus]] = None,
                 config: Optional[Dict] = None):
        self.bus = bus or FakeBus()
        super().__init__(config=config)

    @abc.abstractmethod
    def match_high(self, utterances: List[str], lang: str, message: Message) -> Optional[IntentHandlerMatch]:
        """
        Match an utterance with high confidence.

        Args:
            utterances (List[str]): List of utterances to match.
            lang (str): The language of the utterances.
            message (Message): The message containing the utterance.

        Returns:
            Optional[IntentHandlerMatch]: The match result or None if no match is found.
        """

    @abc.abstractmethod
    def match_medium(self, utterances: List[str], lang: str, message: Message) -> Optional[IntentHandlerMatch]:
        """
        Match an utterance with medium confidence.

        Args:
            utterances (List[str]): List of utterances to match.
            lang (str): The language of the utterances.
            message (Message): The message containing the utterance.

        Returns:
            Optional[IntentHandlerMatch]: The match result or None if no match is found.
        """

    @abc.abstractmethod
    def match_low(self, utterances: List[str], lang: str, message: Message) -> Optional[IntentHandlerMatch]:
        """
        Match an utterance with low confidence.

        Args:
            utterances (List[str]): List of utterances to match.
            lang (str): The language of the utterances.
            message (Message): The message containing the utterance.

        Returns:
            Optional[IntentHandlerMatch]: The match result or None if no match is found.
        """


class PipelineStageMatcher(PipelinePlugin):
    """
    Base class for plugins that consume an utterance during matching,
    aborting subsequent pipeline stages if a match is found.

    WARNING: has side effects when match is used

    these plugins will consume an utterance during the match process,
    it is not known if this component will match without going through the match process

    Example plugins: converse, common_query.

    Attributes:
        bus (Union[MessageBusClient, FakeBus]): The message bus client for communication.
    """

    def __init__(self, bus: Optional[Union[MessageBusClient, FakeBus]] = None,
                 config: Optional[Dict] = None):
        self.bus = bus or FakeBus()
        super().__init__(config=config)

    @abc.abstractmethod
    def match(self, utterances: List[str], lang: str, message: Message) -> Optional[PipelineMatch]:
        """
        Match an utterance, potentially aborting further stages in the pipeline.

        Args:
            utterances (List[str]): List of utterances to match.
            lang (str): The language of the utterances.
            message (Message): The message containing the utterance.

        Returns:
            Optional[PipelineMatch]: The match result or None if no match is found.
        """
        pass


class PipelineStageConfidenceMatcher(PipelineStageMatcher, ConfidenceMatcherPipeline):
    """
    A specialized matcher that consumes utterances during the matching process
    and supports confidence levels. It aborts further pipeline stages if a match is found.

    Example plugins: fallback, stop.

    Attributes:
        bus (Union[MessageBusClient, FakeBus]): The message bus client for communication.
    """

    def __init__(self, bus: Optional[Union[MessageBusClient, FakeBus]] = None,
                 config: Optional[Dict] = None):
        super().__init__(bus=bus, config=config)

    def match(self, utterances: List[str], lang: str, message: Message) -> Optional[PipelineMatch]:
        """
        Match an utterance using high confidence, with no specific match level defined.

        Args:
            utterances (List[str]): List of utterances to match.
            lang (str): The language of the utterances.
            message (Message): The message containing the utterance.

        Returns:
            Optional[PipelineMatch]: The match result or None if no match is found.
        """
        return self.match_high(utterances, lang, message)

    @abc.abstractmethod
    def match_high(self, utterances: List[str], lang: str, message: Message) -> Optional[PipelineMatch]:
        """
        Match an utterance with high confidence.

        Args:
            utterances (List[str]): List of utterances to match.
            lang (str): The language of the utterances.
            message (Message): The message containing the utterance.

        Returns:
            Optional[PipelineMatch]: The match result or None if no match is found.
        """

    @abc.abstractmethod
    def match_medium(self, utterances: List[str], lang: str, message: Message) -> Optional[PipelineMatch]:
        """
        Match an utterance with medium confidence.

        Args:
            utterances (List[str]): List of utterances to match.
            lang (str): The language of the utterances.
            message (Message): The message containing the utterance.

        Returns:
            Optional[PipelineMatch]: The match result or None if no match is found.
        """

    @abc.abstractmethod
    def match_low(self, utterances: List[str], lang: str, message: Message) -> Optional[PipelineMatch]:
        """
        Match an utterance with low confidence.

        Args:
            utterances (List[str]): List of utterances to match.
            lang (str): The language of the utterances.
            message (Message): The message containing the utterance.

        Returns:
            Optional[PipelineMatch]: The match result or None if no match is found.
        """
