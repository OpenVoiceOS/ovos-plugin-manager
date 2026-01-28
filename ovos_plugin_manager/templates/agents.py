import abc
from abc import ABC
from dataclasses import dataclass
from typing import List


@dataclass
class AgentMessage:
    """
    Represents a single message in the agent's conversation.

    Attributes:
        role (str): The role of the message sender, e.g., "user", "system", "assistant".
        content (str): The textual content of the message.
    """
    role: str
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
        """
        Initialize the context manager with a plugin configuration.
        
        Parameters:
            config (dict): Plugin configuration dictionary; if None, an empty dict is used.
        """
        self.config = config or {}

    @property
    def system_prompt(self) -> str:
        """
        Return the base system prompt from the manager's configuration.
        
        Returns:
            str: The base system prompt from `config["system_prompt"]` if present, otherwise an empty string.
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
        Append new messages to the stored history for the specified session.
        
        Parameters:
            new_messages (List[AgentMessage]): Messages to add to the session history.
            session_id (str): Identifier of the conversation session whose history will be updated.
        
        Raises:
            NotImplementedError: Implementations must override this method to persist or merge messages into history.
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

