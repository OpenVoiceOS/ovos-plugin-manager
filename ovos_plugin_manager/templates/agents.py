import abc
from abc import ABC
from dataclasses import dataclass, field
from enum import Enum
from typing import List


class MessageRole(str, Enum):
    """Standardized roles for Agent interactions."""
    SYSTEM = "system"  # Personality and global constraints
    DEVELOPER = "developer"  # High-priority instructions (OpenAI specific)
    USER = "user"  # Human/End-user input
    ASSISTANT = "assistant"  # AI response


@dataclass
class AgentMessage:
    """
    Represents a single message in the agent's conversation.

    Attributes:
        role (str): The role of the message sender, e.g., "user", "system", "assistant".
        content (str): The textual content of the message.
    """
    role: MessageRole
    content: str


class AgentContextManager(ABC):
    """
    Abstract base class for OVOS plugins that manage conversational context.

    Plugins implementing this class can modify or provide context for OVOS personas,
    solvers, or agents by maintaining short-term or long-term memory and augmenting
    the conversation history with relevant messages.

    Args:
        config (dict): Plugin-specific configuration options.
    """

    def __init__(self, config: dict):
        self.config = config or {}

    @property
    def system_prompt(self) -> str:
        """
        Returns the default system prompt defined in the configuration.

        Individual plugins can modify this prompt in self.augment_context.

        Returns:
            str: The base system prompt.
        """
        # typically defined by individual personas
        return self.config.get("system_prompt", "")

    @abc.abstractmethod
    def get_history(self, session_id: str) -> List[AgentMessage]:
        """
        Retrieve the message history for a given session.

        Plugins may manipulate or filter history here (e.g., trimming old messages,
        summarizing, or applying other memory management strategies).

        Args:
            session_id (str): Identifier for the conversation session.

        Returns:
            List[AgentMessage]: A list of messages representing the session's history.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def update_history(self, new_messages: List[AgentMessage], session_id: str):
        """
        Update the session's message history with new messages.

        Typically called after each interaction to keep the conversation context up to date.

        Args:
            new_messages (List[AgentMessage]): New messages to append to history.
            session_id (str): Identifier for the conversation session.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def augment_context(self, utterance: str, session_id: str) -> List[AgentMessage]:
        """
        Generate a list of messages that augment the context for the next agent response.

        Plugins can use this method to:
            - Append to the system prompt.
            - Summarize conversation history.
            - Retrieve information from long-term memory.
            - Implement retrieval-augmented generation (RAG) or tool definitions.

        The returned message list should follow these rules:
            - The first message MAY be a system message containing self.system_prompt.
            - The final message MUST be a user message containing the current utterance.

        Args:
            utterance (str): The latest user input.
            session_id (str): Identifier for the conversation session.

        Returns:
            List[AgentMessage]: Messages representing the augmented context for the agent.
        """
        raise NotImplementedError()


# NOTE: modeled as a separate class to make multimodal support explicit in plugins
@dataclass
class MultimodalAgentMessage(AgentMessage):
    """
    Represents a single message in the agent's conversation.

    Attributes:
        role (str): The role of the message sender, e.g., "user", "system", "assistant".
        content (str): The textual content of the message.
    """
    role: MessageRole
    content: str
    image_content: List[str] = field(default_factory=list)  # b64 encoded
    audio_content: List[str] = field(default_factory=list)  # b64 encoded
    file_content: List[str] = field(default_factory=list)  # b64 encoded


class MultimodalAdapter(ABC):
    """describe multimodal content in text format.
        eg. describe an image input as text

    Can be used by individual personas or AgentContextManager plugins"""

    @abc.abstractmethod
    def convert(self, message: MultimodalAgentMessage) -> AgentMessage:
        raise NotImplementedError()
