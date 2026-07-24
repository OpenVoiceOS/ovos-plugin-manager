import abc
from dataclasses import dataclass
from typing import Optional, Dict, List, Union

from ovos_bus_client.client import MessageBusClient
from ovos_bus_client.message import Message
from ovos_bus_client.session import Session
from ovos_utils.fakebus import FakeBus


@dataclass
class IntentHandlerMatch:
    """
    Represents an intent handler match result, expected by ovos-core plugins.

    Attributes:
        match_type (str): Name of the service that matched the intent.
        match_data (Optional[Dict]): Additional data provided by the intent match.
        skill_id (Optional[str]): The skill this handler belongs to.
        utterance (Optional[str]): The original utterance triggering the intent.
        suppress_activation (bool): When True the orchestrator dispatches the
            match without activating ``skill_id`` (no ``{skill_id}.activate``).
            A termination or continuation of an already-active skill's
            participation — e.g. a stop — sets this, since it must not register
            the target as a freshly activated skill.
        intent_context (Optional[Dict]): Context keywords this match promotes
            into the session's intent_context, per OVOS-CONTEXT-1 §5.1.
    """
    match_type: str
    match_data: Optional[Dict] = None
    skill_id: Optional[str] = None
    utterance: Optional[str] = None
    updated_session: Optional[Session] = None
    suppress_activation: bool = False
    intent_context: Optional[Dict] = None


class PipelinePlugin:
    """
    Base class for intent matching pipeline plugins. Mainly useful for typing

    Attributes:
        config (Dict): Configuration for the plugin.
    """

    def __init__(self, bus: Optional[Union[MessageBusClient, FakeBus]] = None,
                 config: Optional[Dict] = None):
        self.bus = bus or FakeBus()
        self.config = config or {}

    @abc.abstractmethod
    def match(self, utterances: List[str], lang: str, message: Message) -> Optional[IntentHandlerMatch]:
        """
        Match an utterance

        Args:
            utterances (List[str]): List of utterances to match.
            lang (str): The language of the utterances.
            message (Message): The message containing the utterance.

        Returns:
            Optional[IntentHandlerMatch]: The match result or None if no match is found.
        """


class ConfidenceMatcherPipeline(PipelinePlugin):
    """
    Base class for plugins that match utterances with confidence levels,
    but do not directly trigger actions.

    Example plugins: adapt, padatious.

    Attributes:
        bus (Union[MessageBusClient, FakeBus]): The message bus client for communication.
    """

    def match(self, utterances: List[str], lang: str, message: Message) -> Optional[IntentHandlerMatch]:
        return (self.match_high(utterances, lang, message) or
                self.match_medium(utterances, lang, message) or
                self.match_low(utterances, lang, message))

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
