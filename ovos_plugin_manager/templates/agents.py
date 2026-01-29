import abc
import difflib
import time
from abc import ABC
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Iterable, Tuple, Union, Dict, Any

from ovos_bus_client.session import SessionManager, Session
from ovos_utils.lang import standardize_lang_tag
from ovos_utils.log import LOG


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
        role (MessageRole): The role of the message sender, e.g., MessageRole.USER.
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

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    @property
    def system_prompt(self) -> str:
        """
        Returns the default system prompt defined in the configuration.

        Individual plugins may modify this prompt in self.build_conversation_context.

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
    def build_conversation_context(self, utterance: str, session_id: str) -> List[AgentMessage]:
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
        role (MessageRole): The role of the message sender, e.g., MessageRole.USER.
        content (str): The textual content of the message.
    """
    role: MessageRole
    content: str
    image_content: Optional[List[str]] = field(default_factory=list)  # b64 encoded
    audio_content: Optional[List[str]] = field(default_factory=list)  # b64 encoded
    file_content: Optional[List[str]] = field(default_factory=list)  # b64 encoded


class MultimodalAdapter(ABC):
    """describe multimodal content in text format.
        eg. describe an image input as text

    Can be used by individual personas or AgentContextManager plugins"""

    @abc.abstractmethod
    def convert(self, message: MultimodalAgentMessage) -> AgentMessage:
        raise NotImplementedError()


########
# Agent engines replace the previous "solver plugins"
# each task now has a well-defined api contract
# automatic translation is no longer implemented
########
class AbstractAgentEngine(ABC):
    """
    Base class for agent engines that process input to produce specific outputs.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initializes the engine.

        Args:
            config (dict): Configuration mapping for the specific engine.
        """
        self.config = config or {}

    @property
    def lang(self) -> str:
        """Get default language from config or SessionManager."""
        lang = self.config.get("lang") or SessionManager.get().lang
        return standardize_lang_tag(lang)


class RetrievalEngine(AbstractAgentEngine):
    """
    Interface for querying external or internal knowledge bases.

    Supports integrations with remote APIs (Wikipedia, Wolfram Alpha)
    or local databases.
    """

    @abc.abstractmethod
    def query(self, query: str, lang: Optional[str] = None, k: int = 3) -> List[Tuple[str, float]]:
        """
        Searches the knowledge base for relevant documents or data.

        Args:
            query: The search string.
            lang: BCP-47 language code.
            k: The maximum number of results to return.

        Returns:
            List of tuples (content, score) for the top k matches.
        """
        raise NotImplementedError


class ChatEngine(AbstractAgentEngine):
    """
    An engine designed for multi-turn conversations using message list formats.

     messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Knock knock."},
        {"role": "assistant", "content": "Who's there?"},
        {"role": "user", "content": "Orange."},
     ]

     ChatEngine plugins are responsible for filtering any unsupported roles
    """

    @abc.abstractmethod
    def continue_chat(self, messages: List[AgentMessage],
                      session_id: str = "default",
                      lang: Optional[str] = None,
                      units: Optional[str] = None) -> AgentMessage:
        """
        Generate a response message based on the provided chat history.

        Args:
            messages (List[AgentMessage]): Full list of messages in the conversation.
            session_id (str): Identifier for the session.
            lang (str, optional): BCP-47 language code.
            units (str, optional): Preferred unit system (e.g., "metric", "imperial").

        Returns:
            AgentMessage: The generated response message from the assistant.
        """
        raise NotImplementedError()

    def stream_chat(self, messages: List[AgentMessage],
                    session_id: str = "default",
                    lang: Optional[str] = None,
                    units: Optional[str] = None) -> Iterable[AgentMessage]:
        """
        Stream back response messages as they are generated.

        Note:
            Default implementation yields the full response from continue_chat.
            Subclasses should override this for real-time token streaming.

        Args:
            messages (List[AgentMessage]): Full list of messages.
            session_id (str): Identifier for the session.
            lang (str, optional): Language code.
            units (str, optional): Unit system.

        Returns:
            Iterable[AgentMessage]: A stream of response messages.
        """
        yield self.continue_chat(messages, session_id, lang, units)

    def get_response(self, utterance: str,
                     session_id: str = "default",
                     lang: Optional[str] = None,
                     units: Optional[str] = None) -> str:
        """
        High-level wrapper for single-turn text-in/text-out interactions.

        Args:
            utterance: The user's input string.
            session_id: The session identifier.
            lang: BCP-47 language code.
            units: Preferred measurement system.

        Returns:
            The plain-text content of the assistant's response.
        """
        message = AgentMessage(role=MessageRole.USER, content=utterance)
        return self.continue_chat(messages=[message],
                                  session_id=session_id,
                                  lang=lang,
                                  units=units).content


class MultimodalChatEngine(ChatEngine):
    """
    An engine designed for multi-turn conversations using message list formats.

     messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Knock knock."},
        {"role": "assistant", "content": "Who's there?"},
        {"role": "user", "content": "Orange."},
     ]
    """

    @abc.abstractmethod
    def continue_chat(self, messages: List[MultimodalAgentMessage],
                      session_id: str = "default",
                      lang: Optional[str] = None,
                      units: Optional[str] = None) -> MultimodalAgentMessage:
        """
        Generate a response message based on the provided chat history.

        Args:
            messages (List[AgentMessage]): Full list of messages in the conversation.
            session_id (str): Identifier for the session.
            lang (str, optional): BCP-47 language code.
            units (str, optional): Preferred unit system (e.g., "metric", "imperial").

        Returns:
            AgentMessage: The generated response message from the assistant.
        """
        raise NotImplementedError()

    def stream_chat(self, messages: List[MultimodalAgentMessage],
                    session_id: str = "default",
                    lang: Optional[str] = None,
                    units: Optional[str] = None) -> Iterable[MultimodalAgentMessage]:
        """
        Stream back response messages as they are generated.

        Note:
            Default implementation yields the full response from continue_chat.
            Subclasses should override this for real-time token streaming.

        Args:
            messages (List[AgentMessage]): Full list of messages.
            session_id (str): Identifier for the session.
            lang (str, optional): Language code.
            units (str, optional): Unit system.

        Returns:
            Iterable[AgentMessage]: A stream of response messages.
        """
        yield self.continue_chat(messages, session_id, lang, units)

    def get_response(self, utterance: str,
                     image_content: Optional[List[str]] = None,  # b64 encoded
                     audio_content: Optional[List[str]] = None,  # b64 encoded
                     file_content: Optional[List[str]] = None,  # b64 encoded
                     session_id: str = "default",
                     lang: Optional[str] = None,
                     units: Optional[str] = None) -> str:
        """
        High-level wrapper for single-turn text-in/text-out interactions.

        Args:
            utterance: The user's input string.
            session_id: The session identifier.
            lang: BCP-47 language code.
            units: Preferred measurement system.

        Returns:
            The plain-text content of the assistant's response.
        """
        message = MultimodalAgentMessage(role=MessageRole.USER, content=utterance,
                                         image_content=image_content,
                                         audio_content=audio_content,
                                         file_content=file_content)
        return self.continue_chat(messages=[message],
                                  session_id=session_id,
                                  lang=lang,
                                  units=units).content


class SummarizerEngine(AbstractAgentEngine):
    """Engine designed for condensing long documents into concise summaries."""

    @abc.abstractmethod
    def summarize(self, document: str, lang: Optional[str] = None) -> str:
        """
        Create a summary of the provided text.

        Args:
            document (str): The full text to be summarized.
            lang (str, optional): The language of the document.

        Returns:
            str: The summarized text.
        """
        raise NotImplementedError


class ChatSummarizerEngine(AbstractAgentEngine):
    """Engine specialized in summarizing structured chat histories."""

    @abc.abstractmethod
    def summarize(self, messages: List[AgentMessage], lang: Optional[str] = None) -> str:
        """
        Converts a list of AgentMessages into a narrative or bulleted summary.

        Args:
            messages (List[AgentMessage]): Full list of messages in the conversation.
            lang (str, optional): The language of the document.

        Returns:
            str: The summarized text.
        """
        raise NotImplementedError


class ExtractiveQAEngine(AbstractAgentEngine):
    """
    Engine for extractive Question Answering (QA).

    Identifies the specific segment of a text (the "evidence") that
    answers a given question.
    """

    @abc.abstractmethod
    def get_best_passage(self, evidence: str, question: str,
                         lang: Optional[str] = None) -> str:
        """
        Extracts the most relevant passage from the evidence.

        Args:
            evidence (str): The source text to search.
            question (str): The query to answer.
            lang (str, optional): The language of the texts.

        Returns:
            str: The extracted passage answering the question.
        """
        raise NotImplementedError


class ReRankerEngine(AbstractAgentEngine):
    """
    Engine for evaluating and sorting a list of candidates against a query.
    """

    @abc.abstractmethod
    def rerank(self, query: str, options: List[str],
               lang: Optional[str] = None,
               return_index: bool = False) -> List[Tuple[float, Union[str, int]]]:
        """
        Score and rank a list of options against a query.

        Args:
            query (str): The search or selection query.
            options (List[str]): Potential candidates to rank.
            lang (str, optional): Language code.
            return_index (bool): If True, returns the option index instead of text in the tuple.

        Returns:
            List[Tuple[float, Union[str, int]]]: A sorted list of (score, option/index) pairs.
        """
        raise NotImplementedError

    def select_answer(self, query: str,
                      options: List[str],
                      lang: Optional[str] = None,
                      return_index: bool = False) -> Union[str, int]:
        """
        Select the single best answer from a list of options.

        Args:
            query (str): The query to match.
            options (List[str]): List of possible answers.
            lang (str, optional): Language code.
            return_index (bool): Whether to return the index of the option or the text.

        Returns:
            Union[str, int]: The top-ranked option or its index.
        """
        return self.rerank(query, options, lang=lang, return_index=return_index)[0][1]


class YesNoEngine(AbstractAgentEngine):
    """
    Engine for evaluating answers to yes/no questions.

    Determines if a user input means "yes", "no" or undefined
    """

    @abc.abstractmethod
    def yes_or_no(self, question: str, response: str, lang: Optional[str] = None) -> Optional[bool]:
        """
        True: user answered yes
        False: user answered no
        None: invalid/neutral answer
        """
        raise NotImplementedError


class NaturalLanguageInferenceEngine(AbstractAgentEngine):
    """
    Engine for Natural Language Inference (NLI).

    Determines if a 'hypothesis' is logically supported by a 'premise'.
    """

    @abc.abstractmethod
    def predict_entailment(self, premise: str, hypothesis: str,
                           lang: Optional[str] = None) -> bool:
        """
        Determine if the premise logically entails the hypothesis.

        Args:
            premise (str): The base statement or context.
            hypothesis (str): The statement to be verified against the premise.
            lang (str, optional): Language code.

        Returns:
            bool: True if the premise entails the hypothesis, False otherwise.
        """
        raise NotImplementedError


class DocumentIndexerEngine(RetrievalEngine):
    """
    A RetrievalEngine that supports document ingestion and local indexing.
    """

    @abc.abstractmethod
    def ingest_corpus(self, corpus: List[str]):
        """
        Adds a collection of documents to the local index.

        Args:
            corpus: A list of text documents to be indexed.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def query(self, query: str, lang: Optional[str] = None, k: int = 3) -> List[Tuple[str, float]]:
        """Searches the ingested corpus for matching documents."""
        raise NotImplementedError


class QAIndexerEngine(RetrievalEngine):
    """
    A RetrievalEngine specialized in indexing Question-Answer pairs.
    """

    @abc.abstractmethod
    def ingest_corpus(self, corpus: Dict[str, str]):
        """
        Adds question-answer pairs to the index.

        Args:
            corpus: A dictionary where keys are questions and values are answers.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def query(self, query: str, lang: Optional[str] = None, k: int = 3) -> List[Tuple[str, float]]:
        """
        Matches a user query against indexed questions and returns the best answers.

        Returns:
            An iterable of (answer, score) tuples.
        """
        raise NotImplementedError


class CoreferenceEngine(AbstractAgentEngine):
    """
    Base class for Coreference Resolution engines in OVOS.

    This class manages the "State" (Context History), while the inheriting
    plugin class provides the "Intelligence" (NLP Logic).
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Args:
            config: Configuration dict.
                    keys:
                        'lang': default language override
                        'context_ttl': seconds to keep context (default: 120)
        """
        super().__init__(config)
        # Structure: { lang: { pronoun: [(entity, timestamp)] } }
        self.context_data: Dict[str, Dict[str, List[Tuple[str, float]]]] = {}

    @property
    def context_ttl(self) -> int:
        """Time in seconds before a context entry is considered 'stale'."""
        return self.config.get("context_ttl", 120)

    # =========================================================================
    # Public API - Consumers call these
    # =========================================================================
    def resolve(self, text: str, lang: Optional[str] = None, use_memory: bool = False) -> str:
        """
        Main entry point. Resolves coreferences using both historical context
        and the active NLP solver.

        Flow:
        1. Prune stale context (older than TTL).
        2. Apply known context (e.g., 'her' -> 'mom') to the text.
        3. Pass the result to the NLP solver plugin.
        4. Compare Input vs Output to learn NEW context for next time.
        """
        lang = standardize_lang_tag(lang or self.lang)

        # 1. Cleanup old memories
        self._prune_context(lang)

        # 2. Apply 'Vault' (Memory) Context
        # This handles cases where we manually registered "her" = "mom"
        if use_memory:
            text_with_context = self._apply_memory(text, lang)
        else:
            text_with_context = text

        # 3. Apply 'Intelligence' (Plugin NLP)
        # Only run expensive NLP if pronouns/ambiguity exist
        if self.contains_corefs(text_with_context, lang):
            final_solved = self.solve_corefs(text_with_context, lang)
        else:
            final_solved = text_with_context

        # 4. Update Memory
        # If the NLP changed "it" to "the dog", we learn that for next time.
        if use_memory:
            self._learn_context(text_with_context, final_solved, lang)

        return final_solved

    def set_context(self, pronoun: str, entity: str, lang: Optional[str] = None):
        """
        Manually inject context.
        Useful for Skills to force a reference.

        Example: set_context("her", "mom") -> "Tell her hi" becomes "Tell mom hi"
        """
        lang = standardize_lang_tag(lang or self.lang)
        if lang not in self.context_data:
            self.context_data[lang] = {}

        pronoun = pronoun.lower()
        if pronoun not in self.context_data[lang]:
            self.context_data[lang][pronoun] = []

        # Insert at the top as the most recent
        self.context_data[lang][pronoun].insert(0, (entity, time.time()))

    def reset_context(self, lang: Optional[str] = None):
        """Clear context history. Call this at end of sessions."""
        if lang:
            self.context_data[standardize_lang_tag(lang)] = {}
        else:
            self.context_data = {}

    # =========================================================================
    # Abstract Interface - Plugin Developers Implement These
    # =========================================================================

    @abc.abstractmethod
    def solve_corefs(self, text: str, lang: str) -> str:
        """
        Implement the actual coreference resolution logic here.
        Example input: "I saw the dog. It was running."
        Example output: "I saw the dog. The dog was running."
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def contains_corefs(self, text: str, lang: str) -> bool:
        """
        Return True if the text contains words that need resolving (pronouns, references).

        Used to optimize performance by avoiding calls to self.solve_corefs.

        eg. A basic implementation can match the input against a wordlist of lang specific pronouns.
        """
        raise NotImplementedError()

    # =========================================================================
    # Internal Helpers
    # =========================================================================

    def _prune_context(self, lang: str):
        """Remove context entries older than self.context_ttl."""
        if lang not in self.context_data:
            return

        now = time.time()
        ttl = self.context_ttl

        keys_to_remove = []
        for word, history in self.context_data[lang].items():
            # Filter keep only fresh entries
            valid_entries = [entry for entry in history if (now - entry[1]) < ttl]

            if not valid_entries:
                keys_to_remove.append(word)
            else:
                self.context_data[lang][word] = valid_entries

        for k in keys_to_remove:
            del self.context_data[lang][k]

    def _apply_memory(self, text: str, lang: str) -> str:
        """Replace words in text based on current memory."""
        if lang not in self.context_data:
            return text

        words = text.split()
        dirty = False

        for i, word in enumerate(words):
            w_lower = word.lower()
            if w_lower in self.context_data[lang]:
                # Get the most recent entity (index 0)
                replacement_entity = self.context_data[lang][w_lower][0][0]
                words[i] = replacement_entity
                dirty = True

        return " ".join(words) if dirty else text

    def _learn_context(self, original: str, solved: str, lang: str):
        """Diff original vs solved to extract new replacements and save them."""
        replacements = self._extract_replacements(original, solved)

        for pronoun, entities in replacements.items():
            # Register all identified replacements
            for entity in entities:
                self.set_context(pronoun, entity, lang)

    @staticmethod
    def _extract_replacements(original: str, solved: str) -> Dict[str, List[str]]:
        """
        Compares the original text with the solved text to identify exactly
        which words were replaced using difflib.
        """

        # 1. Tokenize inputs
        seq_original = original.lower().split()
        seq_solved = solved.lower().split()

        # 2. Diff the sequences
        matcher = difflib.SequenceMatcher(None, seq_original, seq_solved)

        replacements: Dict[str, List[str]] = {}

        # 3. Extract replacements
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'replace':
                old_phrase = " ".join(seq_original[i1:i2])
                new_phrase = " ".join(seq_solved[j1:j2])

                if old_phrase not in replacements:
                    replacements[old_phrase] = []

                if new_phrase not in replacements[old_phrase]:
                    replacements[old_phrase].append(new_phrase)

        return replacements
