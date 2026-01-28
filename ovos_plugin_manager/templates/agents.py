import abc
import difflib
import time
from abc import ABC
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Iterable, Tuple, Union, Dict

from ovos_bus_client.session import SessionManager, Session
from ovos_utils import flatten_list
from ovos_utils.lang import standardize_lang_tag
from ovos_utils.log import LOG
from quebra_frases import sentence_tokenize, word_tokenize


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
        """
        Initialize the instance and store the provided configuration.
        
        Parameters:
            config (dict): Plugin or engine configuration; falsy values are treated as an empty dict.
        """
        self.config = config or {}

    @property
    def system_prompt(self) -> str:
        """
        Provide the configured base system prompt for this context manager.
        
        Returns:
            The base system prompt from configuration, or an empty string if none is set.
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
        Update the stored message history for a session with the provided messages.
        
        Parameters:
            new_messages (List[AgentMessage]): Messages to incorporate into the session's history.
            session_id (str): Identifier of the conversation session whose history will be updated.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def augment_context(self, utterance: str, session_id: str) -> List[AgentMessage]:
        """
        Produce messages that augment conversational context for the next agent response.
        
        The returned list may include a leading system message (for example containing self.system_prompt) and must end with a user message containing the provided utterance. Implementations may include summarized history, retrieved memory, retrieval-augmented content, tool definitions, or other context useful to the agent.
        
        Parameters:
            utterance (str): The latest user input to include as the final user message.
            session_id (str): Identifier for the conversation session.
        
        Returns:
            List[AgentMessage]: Ordered messages forming the augmented context; the last message must be a user message containing `utterance`.
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
        """
        Produce a text-only AgentMessage that describes the provided multimodal message.
        
        Parameters:
            message (MultimodalAgentMessage): Multimodal message containing textual, image, audio, or file content to be described.
        
        Returns:
            AgentMessage: An AgentMessage whose content is a textual description suitable for downstream (non-multimodal) engines.
        """
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

    def __init__(self, config: dict):
        """
        Initialize the engine and store its configuration on the instance.
        
        Parameters:
            config (dict): Configuration mapping for the engine. If falsy, an empty dict is used.
        """
        self.config = config or {}

    @property
    def lang(self) -> str:
        """
        Determine the engine's language tag by using the configured language if present, otherwise falling back to the current session language, and return it in a standardized form.
        
        Returns:
            str: Standardized language tag (e.g., BCP-47 style).
        """
        lang = self.config.get("lang") or SessionManager.get().lang
        return standardize_lang_tag(lang)


class RetrievalEngine(AbstractAgentEngine):
    """
    Interface for querying external or internal knowledge bases.

    Supports integrations with remote APIs (Wikipedia, Wolfram Alpha)
    or local databases.
    """

    @abc.abstractmethod
    def query(self, query: str, lang: Optional[str] = None, k: int = 3) -> Iterable[Tuple[str, float]]:
        """
        Search the knowledge base and yield the top matching contents with scores.
        
        Parameters:
            query (str): Query string to match against the knowledge base.
            lang (Optional[str]): BCP-47 language tag to influence matching (optional).
            k (int): Maximum number of results to yield.
        
        Yields:
            Tuple[str, float]: Pairs of (content, score) for each match, ordered from best to worst.
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
                     Generate a single-turn assistant response for a user's utterance.
                     
                     Parameters:
                         utterance (str): The user's input.
                         session_id (str): Session identifier.
                         lang (Optional[str]): BCP-47 language code.
                         units (Optional[str]): Preferred measurement system.
                     
                     Returns:
                         Assistant response text (str).
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
                      Generate a multimodal assistant response from a sequence of multimodal chat messages.
                      
                      Parameters:
                          messages (List[MultimodalAgentMessage]): Conversation history including multimodal content; the final message is typically the user's latest input.
                          session_id (str): Session identifier used to scope conversation state.
                          lang (str, optional): BCP-47 language tag to influence response generation.
                          units (str, optional): Preferred measurement system, e.g., "metric" or "imperial".
                      
                      Returns:
                          MultimodalAgentMessage: The assistant's response, potentially including text and any multimodal content (images, audio, files).
                      """
        raise NotImplementedError()

    def stream_chat(self, messages: List[MultimodalAgentMessage],
                    session_id: str = "default",
                    lang: Optional[str] = None,
                    units: Optional[str] = None) -> Iterable[MultimodalAgentMessage]:
        """
                    Stream response messages as they are produced for a multimodal chat interaction.
                    
                    Default implementation yields the single complete response returned by `continue_chat`; subclasses should override to provide real-time incremental streaming.
                    
                    Parameters:
                        messages (List[MultimodalAgentMessage]): Conversation messages including the latest user input.
                        session_id (str): Session identifier.
                        lang (str | None): Language tag for the response.
                        units (str | None): Unit system to use in the response.
                    
                    Returns:
                        Iterable[MultimodalAgentMessage]: An iterable that yields response messages in generation order.
                    """
        yield self.continue_chat(messages, session_id, lang, units)

    def get_response(self, utterance: str,
                     image_content: List[str] = None,  # b64 encoded
                     audio_content: List[str] = None,  # b64 encoded
                     file_content: List[str] = None,  # b64 encoded
                     session_id: str = "default",
                     lang: Optional[str] = None,
                     units: Optional[str] = None) -> str:
        """
                     High-level single-turn interface that sends a multimodal user utterance and returns the assistant's text reply.
                     
                     Parameters:
                         utterance (str): The user's input string.
                         image_content (List[str], optional): List of base64-encoded images to include with the utterance.
                         audio_content (List[str], optional): List of base64-encoded audio clips to include with the utterance.
                         file_content (List[str], optional): List of base64-encoded files to include with the utterance.
                         session_id (str, optional): Session identifier; defaults to "default".
                         lang (Optional[str], optional): BCP-47 language tag to use for the request.
                         units (Optional[str], optional): Preferred measurement system (e.g., "metric" or "imperial").
                     
                     Returns:
                         str: The plain-text content of the assistant's response.
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
        Produce a concise summary of the given document.
        
        Parameters:
            document (str): Text to summarize.
            lang (Optional[str]): Optional language tag to guide summarization.
        
        Returns:
            summarized_text (str): A concise summary of the input document.
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
                         Finds the passage in `evidence` that is most relevant to the given question.
                         
                         Parameters:
                             evidence (str): Source text to search for an answer.
                             question (str): Question to locate an answer for within the evidence.
                             lang (str, optional): Language tag used for matching/tokenization (if applicable).
                         
                         Returns:
                             str: The passage from `evidence` judged most relevant to `question`.
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
                      
                      Parameters:
                          query (str): The query to match against options.
                          options (List[str]): Candidate answers to evaluate.
                          lang (str, optional): Language code for ranking, if applicable.
                          return_index (bool): If True, return the index of the selected option; otherwise return the option text.
                      
                      Returns:
                          Union[str, int]: The top-ranked option string, or its index when `return_index` is True.
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
        Determine whether a response answers a yes/no question.
        
        Parameters:
            question (str): The yes/no question being asked; used for context when interpreting the response.
            response (str): The user's reply to interpret.
            lang (Optional[str]): Language tag to use when interpreting affirmative/negative expressions (defaults to engine/session language).
        
        Returns:
            True if the response is affirmative, False if the response is negative, None if the response is neutral or cannot be reliably interpreted.
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
                           Decide whether a premise entails a hypothesis.
                           
                           Parameters:
                               lang (Optional[str]): Optional language tag to guide interpretation.
                           
                           Returns:
                               `true` if the premise entails the hypothesis, `false` otherwise.
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
    def query(self, query: str, lang: Optional[str] = None, k: int = 3) -> Iterable[Tuple[str, float]]:
        """
        Retrieve top matching documents from the ingested corpus for a text query.
        
        Parameters:
            query (str): Text query to match against the indexed documents.
            lang (Optional[str]): Language tag to use for the query matching (if supported by the index).
            k (int): Maximum number of results to return.
        
        Returns:
            Iterable[Tuple[str, float]]: An iterable of `(document, score)` pairs where `document` is matching content and `score` is a relevance score (higher means more relevant).
        """
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
    def query(self, query: str, lang: Optional[str] = None, k: int = 3) -> Iterable[Tuple[str, float]]:
        """
        Find the best-matching answers for a query against the indexed question-answer pairs.
        
        Parameters:
            query (str): The user's query to match.
            lang (Optional[str]): Language tag to select a language-specific index (if supported).
            k (int): Maximum number of results to return.
        
        Returns:
            Iterable[Tuple[str, float]]: An iterable of (answer, score) pairs ordered by relevance (highest first).
        """
        raise NotImplementedError


class CoreferenceEngine(AbstractAgentEngine):
    """
    Base class for Coreference Resolution engines in OVOS.

    This class manages the "State" (Context History), while the inheriting
    plugin class provides the "Intelligence" (NLP Logic).
    """

    def __init__(self, config: dict):
        """
        Initialize the coreference engine with configuration and empty context memory.
        
        Maintains per-language context data mapping pronouns to a list of (entity, timestamp) tuples:
        { language_tag: { pronoun: [(entity, unix_timestamp), ...] } }.
        
        Parameters:
            config (dict): Engine configuration. Recognized keys:
                - 'lang': optional default language tag override.
                - 'context_ttl': time-to-live in seconds for stored context entries (default 120).
        """
        super().__init__(config)
        # Structure: { lang: { pronoun: [(entity, timestamp)] } }
        self.context_data: Dict[str, Dict[str, List[Tuple[str, float]]]] = {}

    @property
    def context_ttl(self) -> int:
        """
        Return the time-to-live for stored context entries in seconds.
        
        Returns:
            int: Number of seconds before a context entry is considered stale (default 120).
        """
        return self.config.get("context_ttl", 120)

    # =========================================================================
    # Public API - Consumers call these
    # =========================================================================
    def resolve(self, text: str, lang: Optional[str] = None, use_memory: bool = False) -> str:
        """
        Resolve coreferences in the given text using stored conversational memory and the configured coreference solver.
        
        Parameters:
            text (str): Input text potentially containing coreferences.
            lang (Optional[str]): Language tag to use for resolution; when None, the engine's default language is used.
            use_memory (bool): If True, apply and update persistent pronoun→entity mappings based on historical context.
        
        Returns:
            str: Text with coreferences resolved.
        
        Description:
            The method prunes expired memory entries for the chosen language, optionally applies existing memory mappings to the input, invokes the coreference solver when ambiguous references are detected, and—if memory is enabled—learns new mappings from differences between the pre-solved and solved text.
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
        Manually add a pronoun-to-entity memory mapping for a specific language.
        
        Inserts the given (entity, timestamp) pair as the most recent mapping for `pronoun` in the resolved language. If `lang` is omitted, the engine's current language is used; `pronoun` is normalized to lowercase before storing.
        
        Parameters:
            pronoun (str): The pronoun token to map (e.g., "her", "they").
            entity (str): The entity text to associate with the pronoun (e.g., "mom", "the team").
            lang (Optional[str]): BCP-47 language tag to scope the mapping; when None uses the engine's language.
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
        """
        Clear stored coreference context data.
        
        If `lang` is provided, clears context only for that language (language tag is normalized). If `lang` is omitted, clears context for all languages.
        """
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
        Resolve coreferent expressions in the given text for the specified language.
        
        Parameters:
            text (str): Input text that may contain pronouns or other referring expressions.
            lang (str): Language tag to guide resolution (e.g., "en-US").
        
        Returns:
            str: Text with coreferences replaced by their resolved referents (e.g., "I saw the dog. The dog was running.").
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def contains_corefs(self, text: str, lang: str) -> bool:
        """
        Detect whether the text contains resolvable coreferences for the specified language.
        
        Implementations should return True when the input contains pronouns or referring expressions that would require coreference resolution, and False otherwise.
        
        Returns:
            bool: `True` if the text contains resolvable coreferences for the language, `False` otherwise.
        """
        raise NotImplementedError()

    # =========================================================================
    # Internal Helpers
    # =========================================================================

    def _prune_context(self, lang: str):
        """
        Prune stale memory entries for a language from the context store.
        
        Removes any (entity, timestamp) pairs older than self.context_ttl from self.context_data[lang].
        If a pronoun key has no remaining entries after pruning, that key is deleted.
        
        Parameters:
            lang (str): Language tag identifying which language's context to prune.
        """
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
        """
        Apply stored memory replacements to words in `text` for the given language.
        
        Replaces tokens that match stored pronoun/phrase keys with their most recent associated entity for `lang`. If no replacements are applicable or no memory exists for `lang`, returns the original `text`.
        
        Parameters:
            text (str): Input text whose tokens may be replaced.
            lang (str): Standardized language tag to select the memory store.
        
        Returns:
            str: Text with applicable memory-based substitutions applied.
        """
        if lang not in self.context_data:
            return text

        words = word_tokenize(text)
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
        """
        Extract replacements between the original and solved texts and store them as pronoun→entity mappings for the given language.
        
        Parameters:
            original (str): The text before coreference resolution.
            solved (str): The text after coreference resolution.
            lang (str): Language tag used when storing context mappings.
        """
        replacements = self._extract_replacements(original, solved)

        for pronoun, entities in replacements.items():
            # Register all identified replacements
            for entity in entities:
                self.set_context(pronoun, entity, lang)

    @staticmethod
    def _extract_replacements(original: str, solved: str) -> Dict[str, List[str]]:
        """
        Identify token-level phrase substitutions between two texts.
        
        Compares `original` and `solved` at the word/token level (tokens are lowercased and split on whitespace) and returns a mapping from each phrase in `original` that was replaced to a list of corresponding replacement phrases observed in `solved`. Replacement phrases are returned as space-joined, lowercased token sequences; duplicate replacements are omitted while preserving their discovery order.
        
        Parameters:
            original (str): The original text.
            solved (str): The text after substitutions.
        
        Returns:
            Dict[str, List[str]]: A dictionary where keys are lowercase phrases from `original` that were replaced, and values are lists of their distinct replacement phrases from `solved`.
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


def sentence_split(text: str, max_sentences: int = 25) -> List[str]:
    """
    Split the input text into at most `max_sentences` sentence strings.
    
    Parameters:
        text (str): Text to split into sentences.
        max_sentences (int): Maximum number of sentences to return (default 25).
    
    Returns:
        List[str]: Sentences extracted from the input. Returns an empty list for empty input;
        if sentence splitting fails, returns a single-element list containing the original `text`.
    """
    if not text:
        LOG.warning("empty text received in sentence_split")
        return []
    try:
        # sentence_tokenize occasionally has issues with \n for some reason
        return flatten_list([sentence_tokenize(t)
                             for t in text.split("\n")])[:max_sentences]
    except Exception as e:
        LOG.exception(f"Error in sentence_split: {e}")
        return [text]