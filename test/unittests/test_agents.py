# Copyright 2024, OpenVoiceOS
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for ovos_plugin_manager.agents and ovos_plugin_manager.templates.agents."""

import time
import unittest
from typing import Dict, List, Optional, Tuple, Union
from unittest.mock import MagicMock, patch

from ovos_plugin_manager.templates.agents import (
    AgentContextManager,
    AgentMessage,
    ChatEngine,
    ChatSummarizerEngine,
    CoreferenceEngine,
    DocumentIndexerEngine,
    ExtractiveQAEngine,
    MessageRole,
    MultimodalAdapter,
    MultimodalAgentMessage,
    MultimodalChatEngine,
    NaturalLanguageInferenceEngine,
    QAIndexerEngine,
    ReRankerEngine,
    RetrievalEngine,
    SummarizerEngine,
    YesNoEngine,
)
from ovos_plugin_manager.utils import PluginTypes


# ---------------------------------------------------------------------------
# Concrete minimal implementations for abstract classes
# ---------------------------------------------------------------------------

class _MemoryPlugin(AgentContextManager):
    """Minimal concrete implementation of AgentContextManager for tests."""

    def __init__(self, config: Optional[Dict] = None) -> None:
        """Initialise with optional config."""
        super().__init__(config)
        self._history: Dict[str, List[AgentMessage]] = {}

    def get_history(self, session_id: str) -> List[AgentMessage]:
        """Return stored history for session."""
        return self._history.get(session_id, [])

    def update_history(self, new_messages: List[AgentMessage], session_id: str) -> None:
        """Append messages to session history."""
        self._history.setdefault(session_id, []).extend(new_messages)

    def build_conversation_context(self, utterance: str, session_id: str) -> List[AgentMessage]:
        """Build basic context from history."""
        msgs = self.get_history(session_id)
        msgs.append(AgentMessage(role=MessageRole.USER, content=utterance))
        return msgs


class _ChatEngineImpl(ChatEngine):
    """Minimal ChatEngine returning a fixed response."""

    def continue_chat(
        self,
        messages: List[AgentMessage],
        session_id: str = "default",
        lang: Optional[str] = None,
        units: Optional[str] = None,
    ) -> AgentMessage:
        """Echo the last user message back."""
        last = messages[-1].content if messages else "hello"
        return AgentMessage(role=MessageRole.ASSISTANT, content=f"echo: {last}")


class _MultimodalChatEngineImpl(MultimodalChatEngine):
    """Minimal MultimodalChatEngine for tests."""

    def continue_chat(
        self,
        messages: List[MultimodalAgentMessage],
        session_id: str = "default",
        lang: Optional[str] = None,
        units: Optional[str] = None,
    ) -> MultimodalAgentMessage:
        """Return a fixed multimodal message."""
        return MultimodalAgentMessage(role=MessageRole.ASSISTANT, content="ok")


class _ReRankerImpl(ReRankerEngine):
    """Minimal ReRankerEngine sorting by string length."""

    def rerank(
        self,
        query: str,
        options: List[str],
        lang: Optional[str] = None,
        return_index: bool = False,
    ) -> List[Tuple[float, Union[str, int]]]:
        """Rank by length descending."""
        scored = [(float(len(o)), i if return_index else o) for i, o in enumerate(options)]
        return sorted(scored, reverse=True)


class _CoreferenceEngineImpl(CoreferenceEngine):
    """Minimal CoreferenceEngine that does nothing."""

    def solve_corefs(self, text: str, lang: str) -> str:
        """Return text unchanged."""
        return text.replace("it", "the dog")

    def contains_corefs(self, text: str, lang: str) -> bool:
        """Check for 'it' as a stand-in pronoun."""
        return "it" in text.lower().split()


# ---------------------------------------------------------------------------
# Tests for AgentMessage / MessageRole dataclasses
# ---------------------------------------------------------------------------

class TestAgentMessage(unittest.TestCase):
    """Tests for AgentMessage dataclass."""

    def test_create_message(self) -> None:
        """AgentMessage stores role and content."""
        msg = AgentMessage(role=MessageRole.USER, content="hello")
        self.assertEqual(msg.role, MessageRole.USER)
        self.assertEqual(msg.content, "hello")

    def test_message_roles(self) -> None:
        """All MessageRole enum values exist."""
        roles = {r.value for r in MessageRole}
        self.assertIn("system", roles)
        self.assertIn("user", roles)
        self.assertIn("assistant", roles)

    def test_multimodal_message_defaults(self) -> None:
        """MultimodalAgentMessage has empty lists by default."""
        msg = MultimodalAgentMessage(role=MessageRole.USER, content="hi")
        self.assertEqual(msg.image_content, [])
        self.assertEqual(msg.audio_content, [])
        self.assertEqual(msg.file_content, [])


# ---------------------------------------------------------------------------
# Tests for AgentContextManager
# ---------------------------------------------------------------------------

class TestAgentContextManager(unittest.TestCase):
    """Tests for AgentContextManager base class via _MemoryPlugin."""

    def setUp(self) -> None:
        """Set up a fresh _MemoryPlugin for each test."""
        self.plugin = _MemoryPlugin(config={"system_prompt": "Be helpful."})

    def test_system_prompt_from_config(self) -> None:
        """system_prompt property reads from config."""
        self.assertEqual(self.plugin.system_prompt, "Be helpful.")

    def test_system_prompt_default(self) -> None:
        """system_prompt defaults to empty string when not in config."""
        p = _MemoryPlugin()
        self.assertEqual(p.system_prompt, "")

    def test_get_history_empty(self) -> None:
        """get_history returns empty list for unknown session."""
        result = self.plugin.get_history("unknown")
        self.assertEqual(result, [])

    def test_update_and_get_history(self) -> None:
        """update_history appends messages retrievable via get_history."""
        msgs = [AgentMessage(role=MessageRole.USER, content="test")]
        self.plugin.update_history(msgs, "session1")
        history = self.plugin.get_history("session1")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].content, "test")

    def test_build_conversation_context(self) -> None:
        """build_conversation_context appends current utterance."""
        ctx = self.plugin.build_conversation_context("hello world", "s1")
        self.assertIsInstance(ctx, list)
        self.assertEqual(ctx[-1].content, "hello world")
        self.assertEqual(ctx[-1].role, MessageRole.USER)


# ---------------------------------------------------------------------------
# Tests for ChatEngine
# ---------------------------------------------------------------------------

class TestChatEngine(unittest.TestCase):
    """Tests for ChatEngine base class via _ChatEngineImpl."""

    def setUp(self) -> None:
        """Initialise engine."""
        self.engine = _ChatEngineImpl()

    def test_continue_chat(self) -> None:
        """continue_chat returns an AgentMessage."""
        msgs = [AgentMessage(role=MessageRole.USER, content="ping")]
        result = self.engine.continue_chat(msgs)
        self.assertIsInstance(result, AgentMessage)
        self.assertIn("ping", result.content)

    def test_get_response(self) -> None:
        """get_response returns plain string."""
        resp = self.engine.get_response("test")
        self.assertIsInstance(resp, str)

    def test_stream_tokens(self) -> None:
        """stream_tokens yields individual words."""
        msgs = [AgentMessage(role=MessageRole.USER, content="hello world")]
        tokens = list(self.engine.stream_tokens(msgs))
        self.assertIsInstance(tokens, list)
        self.assertTrue(len(tokens) > 0)

    def test_stream_sentences(self) -> None:
        """stream_sentences yields sentence strings."""
        msgs = [AgentMessage(role=MessageRole.USER, content="line1\nline2")]
        sentences = list(self.engine.stream_sentences(msgs))
        self.assertIsInstance(sentences, list)


# ---------------------------------------------------------------------------
# Tests for MultimodalChatEngine
# ---------------------------------------------------------------------------

class TestMultimodalChatEngine(unittest.TestCase):
    """Tests for MultimodalChatEngine."""

    def setUp(self) -> None:
        """Initialise engine."""
        self.engine = _MultimodalChatEngineImpl()

    def test_get_response(self) -> None:
        """get_response returns a string."""
        result = self.engine.get_response("hello")
        self.assertIsInstance(result, str)

    def test_stream_chat(self) -> None:
        """stream_chat yields at least one message."""
        msgs = [MultimodalAgentMessage(role=MessageRole.USER, content="hi")]
        stream = list(self.engine.stream_chat(msgs))
        self.assertGreater(len(stream), 0)


# ---------------------------------------------------------------------------
# Tests for ReRankerEngine
# ---------------------------------------------------------------------------

class TestReRankerEngine(unittest.TestCase):
    """Tests for ReRankerEngine."""

    def setUp(self) -> None:
        """Initialise engine."""
        self.engine = _ReRankerImpl()

    def test_rerank_returns_list(self) -> None:
        """rerank returns sorted list of (score, option) tuples."""
        result = self.engine.rerank("query", ["a", "bb", "ccc"])
        self.assertEqual(len(result), 3)
        # highest score first
        self.assertGreaterEqual(result[0][0], result[1][0])

    def test_select_answer(self) -> None:
        """select_answer returns the top-ranked option."""
        result = self.engine.select_answer("query", ["a", "bb", "ccc"])
        self.assertEqual(result, "ccc")  # longest wins in our impl

    def test_select_answer_return_index(self) -> None:
        """select_answer with return_index=True returns an int."""
        result = self.engine.select_answer("query", ["a", "bb", "ccc"], return_index=True)
        self.assertIsInstance(result, int)


# ---------------------------------------------------------------------------
# Tests for CoreferenceEngine
# ---------------------------------------------------------------------------

class TestCoreferenceEngine(unittest.TestCase):
    """Tests for CoreferenceEngine base class methods."""

    def setUp(self) -> None:
        """Set up engine with default config."""
        self.engine = _CoreferenceEngineImpl(config={"context_ttl": 120})

    def test_context_ttl_default(self) -> None:
        """context_ttl reads from config."""
        self.assertEqual(self.engine.context_ttl, 120)

    def test_set_and_resolve_context(self) -> None:
        """set_context injects context used by resolve."""
        self.engine.set_context("it", "the cat", lang="en-us")
        # 'it' is in text, so contains_corefs=True and solve_corefs replaces it
        result = self.engine.resolve("I saw it running", lang="en-us")
        self.assertIsInstance(result, str)

    def test_reset_context_lang(self) -> None:
        """reset_context with lang clears only that lang."""
        self.engine.set_context("it", "cat", lang="en-us")
        self.engine.reset_context(lang="en-us")
        self.assertEqual(self.engine.context_data.get("en-US", {}), {})

    def test_reset_context_all(self) -> None:
        """reset_context without lang clears everything."""
        self.engine.set_context("it", "cat", lang="en-us")
        self.engine.reset_context()
        self.assertEqual(self.engine.context_data, {})

    def test_prune_stale_context(self) -> None:
        """Stale context entries are pruned."""
        # inject old entry manually
        import time as _time
        self.engine.context_data["en-US"] = {
            "it": [("cat", _time.time() - 200)]  # older than TTL=120
        }
        self.engine._prune_context("en-US")
        self.assertNotIn("it", self.engine.context_data.get("en-US", {}))

    def test_apply_memory(self) -> None:
        """_apply_memory replaces known pronouns."""
        self.engine.set_context("her", "mom", lang="en-us")
        result = self.engine._apply_memory("tell her hi", "en-US")
        self.assertIn("mom", result)

    def test_extract_replacements(self) -> None:
        """_extract_replacements detects substituted words."""
        replacements = CoreferenceEngine._extract_replacements(
            "I saw it running", "I saw the dog running"
        )
        self.assertIn("it", replacements)

    def test_resolve_no_corefs(self) -> None:
        """resolve returns text unchanged when no corefs."""
        result = self.engine.resolve("I saw the dog running", lang="en-us")
        self.assertEqual(result, "I saw the dog running")

    def test_resolve_with_memory(self) -> None:
        """resolve with use_memory=True applies memory context."""
        self.engine.set_context("it", "dog", lang="en-us")
        result = self.engine.resolve("I saw it running", lang="en-us", use_memory=True)
        self.assertIsInstance(result, str)


# ---------------------------------------------------------------------------
# Tests for agents.py (plugin discovery wrappers)
# ---------------------------------------------------------------------------

class TestAgentsModule(unittest.TestCase):
    """Tests for ovos_plugin_manager.agents find/load functions."""

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_memory_plugins(self, mock_find: MagicMock) -> None:
        """find_memory_plugins calls find_plugins with AGENT_MEMORY."""
        from ovos_plugin_manager.agents import find_memory_plugins
        mock_find.return_value = {"test": MagicMock()}
        result = find_memory_plugins()
        mock_find.assert_called_once_with(PluginTypes.AGENT_MEMORY)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_memory_plugin(self, mock_load: MagicMock) -> None:
        """load_memory_plugin calls load_plugin with correct type."""
        from ovos_plugin_manager.agents import load_memory_plugin
        mock_load.return_value = MagicMock()
        load_memory_plugin("test-plugin")
        mock_load.assert_called_once_with("test-plugin", PluginTypes.AGENT_MEMORY)

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_chat_plugins(self, mock_find: MagicMock) -> None:
        """find_chat_plugins calls find_plugins with AGENT_CHAT."""
        from ovos_plugin_manager.agents import find_chat_plugins
        mock_find.return_value = {}
        find_chat_plugins()
        mock_find.assert_called_once_with(PluginTypes.AGENT_CHAT)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_chat_plugin(self, mock_load: MagicMock) -> None:
        """load_chat_plugin calls load_plugin with AGENT_CHAT."""
        from ovos_plugin_manager.agents import load_chat_plugin
        mock_load.return_value = MagicMock()
        load_chat_plugin("my-chat")
        mock_load.assert_called_once_with("my-chat", PluginTypes.AGENT_CHAT)

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_summarizer_plugins(self, mock_find: MagicMock) -> None:
        """find_summarizer_plugins calls find_plugins with AGENT_SUMMARIZER."""
        from ovos_plugin_manager.agents import find_summarizer_plugins
        mock_find.return_value = {}
        find_summarizer_plugins()
        mock_find.assert_called_once_with(PluginTypes.AGENT_SUMMARIZER)

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_retrieval_plugins(self, mock_find: MagicMock) -> None:
        """find_retrieval_plugins calls find_plugins with AGENT_RETRIEVAL."""
        from ovos_plugin_manager.agents import find_retrieval_plugins
        mock_find.return_value = {}
        find_retrieval_plugins()
        mock_find.assert_called_once_with(PluginTypes.AGENT_RETRIEVAL)

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_reranker_plugins(self, mock_find: MagicMock) -> None:
        """find_reranker_plugins calls find_plugins with AGENT_RERANKER."""
        from ovos_plugin_manager.agents import find_reranker_plugins
        mock_find.return_value = {}
        find_reranker_plugins()
        mock_find.assert_called_once_with(PluginTypes.AGENT_RERANKER)

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_yesno_plugins(self, mock_find: MagicMock) -> None:
        """find_yesno_plugins calls find_plugins with AGENT_YES_NO."""
        from ovos_plugin_manager.agents import find_yesno_plugins
        mock_find.return_value = {}
        find_yesno_plugins()
        mock_find.assert_called_once_with(PluginTypes.AGENT_YES_NO)

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_nli_plugins(self, mock_find: MagicMock) -> None:
        """find_natural_language_inference_plugins uses AGENT_NLI."""
        from ovos_plugin_manager.agents import find_natural_language_inference_plugins
        mock_find.return_value = {}
        find_natural_language_inference_plugins()
        mock_find.assert_called_once_with(PluginTypes.AGENT_NLI)

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_document_indexer_plugins(self, mock_find: MagicMock) -> None:
        """find_document_indexer_plugins uses AGENT_DOC_RETRIEVAL."""
        from ovos_plugin_manager.agents import find_document_indexer_plugins
        mock_find.return_value = {}
        find_document_indexer_plugins()
        mock_find.assert_called_once_with(PluginTypes.AGENT_DOC_RETRIEVAL)

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_qa_indexer_plugins(self, mock_find: MagicMock) -> None:
        """find_qa_indexer_plugins uses AGENT_QA_RETRIEVAL."""
        from ovos_plugin_manager.agents import find_qa_indexer_plugins
        mock_find.return_value = {}
        find_qa_indexer_plugins()
        mock_find.assert_called_once_with(PluginTypes.AGENT_QA_RETRIEVAL)

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_coreference_plugins(self, mock_find: MagicMock) -> None:
        """find_coreference_plugins uses AGENT_COREF."""
        from ovos_plugin_manager.agents import find_coreference_plugins
        mock_find.return_value = {}
        find_coreference_plugins()
        mock_find.assert_called_once_with(PluginTypes.AGENT_COREF)

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_chat_summarizer_plugins(self, mock_find: MagicMock) -> None:
        """find_chat_summarizer_plugins uses AGENT_CHAT_SUMMARIZER."""
        from ovos_plugin_manager.agents import find_chat_summarizer_plugins
        mock_find.return_value = {}
        find_chat_summarizer_plugins()
        mock_find.assert_called_once_with(PluginTypes.AGENT_CHAT_SUMMARIZER)

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_multimodal_chat_plugins(self, mock_find: MagicMock) -> None:
        """find_multimodal_chat_plugins uses AGENT_CHAT_MULTIMODAL."""
        from ovos_plugin_manager.agents import find_multimodal_chat_plugins
        mock_find.return_value = {}
        find_multimodal_chat_plugins()
        mock_find.assert_called_once_with(PluginTypes.AGENT_CHAT_MULTIMODAL)

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_multimodal_adapter_plugins(self, mock_find: MagicMock) -> None:
        """find_multimodal_adapter_plugins uses AGENT_MULTIMODAL_ADAPTER."""
        from ovos_plugin_manager.agents import find_multimodal_adapter_plugins
        mock_find.return_value = {}
        find_multimodal_adapter_plugins()
        mock_find.assert_called_once_with(PluginTypes.AGENT_MULTIMODAL_ADAPTER)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_extractive_qa_plugin(self, mock_load: MagicMock) -> None:
        """load_extractive_qa_plugin calls load_plugin with AGENT_EXTRACTIVE_QA."""
        from ovos_plugin_manager.agents import load_extractive_qa_plugin
        mock_load.return_value = MagicMock()
        load_extractive_qa_plugin("qa-plugin")
        mock_load.assert_called_once_with("qa-plugin", PluginTypes.AGENT_EXTRACTIVE_QA)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_multimodal_adapter_plugin(self, mock_load: MagicMock) -> None:
        """load_multimodal_adapter_plugin calls load_plugin with AGENT_MULTIMODAL_ADAPTER."""
        from ovos_plugin_manager.agents import load_multimodal_adapter_plugin
        mock_load.return_value = MagicMock()
        load_multimodal_adapter_plugin("mm-adapter")
        mock_load.assert_called_once_with("mm-adapter", PluginTypes.AGENT_MULTIMODAL_ADAPTER)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_retrieval_plugin(self, mock_load: MagicMock) -> None:
        """load_retrieval_plugin calls load_plugin with AGENT_RETRIEVAL."""
        from ovos_plugin_manager.agents import load_retrieval_plugin
        mock_load.return_value = MagicMock()
        load_retrieval_plugin("retrieval-plugin")
        mock_load.assert_called_once_with("retrieval-plugin", PluginTypes.AGENT_RETRIEVAL)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_summarizer_plugin(self, mock_load: MagicMock) -> None:
        """load_summarizer_plugin calls load_plugin with AGENT_SUMMARIZER."""
        from ovos_plugin_manager.agents import load_summarizer_plugin
        mock_load.return_value = MagicMock()
        load_summarizer_plugin("summ-plugin")
        mock_load.assert_called_once_with("summ-plugin", PluginTypes.AGENT_SUMMARIZER)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_chat_summarizer_plugin(self, mock_load: MagicMock) -> None:
        """load_chat_summarizer_plugin calls load_plugin with AGENT_CHAT_SUMMARIZER."""
        from ovos_plugin_manager.agents import load_chat_summarizer_plugin
        mock_load.return_value = MagicMock()
        load_chat_summarizer_plugin("chat-summ")
        mock_load.assert_called_once_with("chat-summ", PluginTypes.AGENT_CHAT_SUMMARIZER)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_yesno_plugin(self, mock_load: MagicMock) -> None:
        """load_yesno_plugin calls load_plugin with AGENT_YES_NO."""
        from ovos_plugin_manager.agents import load_yesno_plugin
        mock_load.return_value = MagicMock()
        load_yesno_plugin("yesno-plugin")
        mock_load.assert_called_once_with("yesno-plugin", PluginTypes.AGENT_YES_NO)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_natural_language_inference_plugin(self, mock_load: MagicMock) -> None:
        """load_natural_language_inference_plugin calls load_plugin with AGENT_NLI."""
        from ovos_plugin_manager.agents import load_natural_language_inference_plugin
        mock_load.return_value = MagicMock()
        load_natural_language_inference_plugin("nli-plugin")
        mock_load.assert_called_once_with("nli-plugin", PluginTypes.AGENT_NLI)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_document_indexer_plugin(self, mock_load: MagicMock) -> None:
        """load_document_indexer_plugin calls load_plugin with AGENT_DOC_RETRIEVAL."""
        from ovos_plugin_manager.agents import load_document_indexer_plugin
        mock_load.return_value = MagicMock()
        load_document_indexer_plugin("doc-plugin")
        mock_load.assert_called_once_with("doc-plugin", PluginTypes.AGENT_DOC_RETRIEVAL)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_qa_indexer_plugin(self, mock_load: MagicMock) -> None:
        """load_qa_indexer_plugin calls load_plugin with AGENT_QA_RETRIEVAL."""
        from ovos_plugin_manager.agents import load_qa_indexer_plugin
        mock_load.return_value = MagicMock()
        load_qa_indexer_plugin("qa-idx")
        mock_load.assert_called_once_with("qa-idx", PluginTypes.AGENT_QA_RETRIEVAL)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_coreference_plugin(self, mock_load: MagicMock) -> None:
        """load_coreference_plugin calls load_plugin with AGENT_COREF."""
        from ovos_plugin_manager.agents import load_coreference_plugin
        mock_load.return_value = MagicMock()
        load_coreference_plugin("coref-plugin")
        mock_load.assert_called_once_with("coref-plugin", PluginTypes.AGENT_COREF)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_multimodal_chat_plugin(self, mock_load: MagicMock) -> None:
        """load_multimodal_chat_plugin calls load_plugin with AGENT_CHAT_MULTIMODAL."""
        from ovos_plugin_manager.agents import load_multimodal_chat_plugin
        mock_load.return_value = MagicMock()
        load_multimodal_chat_plugin("mm-chat")
        mock_load.assert_called_once_with("mm-chat", PluginTypes.AGENT_CHAT_MULTIMODAL)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_reranker_plugin(self, mock_load: MagicMock) -> None:
        """load_reranker_plugin calls load_plugin with AGENT_RERANKER."""
        from ovos_plugin_manager.agents import load_reranker_plugin
        mock_load.return_value = MagicMock()
        load_reranker_plugin("reranker-plugin")
        mock_load.assert_called_once_with("reranker-plugin", PluginTypes.AGENT_RERANKER)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_option_matcher_plugin(self, mock_load: MagicMock) -> None:
        """load_option_matcher_plugin calls load_plugin with AGENT_OPTION_MATCHER."""
        from ovos_plugin_manager.agents import load_option_matcher_plugin
        mock_load.return_value = MagicMock()
        load_option_matcher_plugin("option-matcher-plugin")
        mock_load.assert_called_once_with("option-matcher-plugin", PluginTypes.AGENT_OPTION_MATCHER)


class TestFindOptionMatcherPlugins(unittest.TestCase):
    """Tests for find_option_matcher_plugins."""

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_option_matcher_plugins(self, mock_find: MagicMock) -> None:
        """find_option_matcher_plugins calls find_plugins with AGENT_OPTION_MATCHER."""
        from ovos_plugin_manager.agents import find_option_matcher_plugins
        mock_find.return_value = {}
        find_option_matcher_plugins()
        mock_find.assert_called_once_with(PluginTypes.AGENT_OPTION_MATCHER)


class TestOptionMatcherEngine(unittest.TestCase):
    """Tests for OptionMatcherEngine base class."""

    def test_match_option_is_abstract(self) -> None:
        """OptionMatcherEngine.match_option must be implemented by subclasses."""
        from ovos_plugin_manager.templates.agents import OptionMatcherEngine
        with self.assertRaises(TypeError):
            OptionMatcherEngine()  # type: ignore[abstract]

    def test_concrete_subclass_works(self) -> None:
        """A concrete OptionMatcherEngine subclass can be instantiated and called."""
        from ovos_plugin_manager.templates.agents import OptionMatcherEngine

        class FakeMatcher(OptionMatcherEngine):
            def match_option(self, utterance, options, lang=None):
                return options[0] if options else None

        matcher = FakeMatcher()
        self.assertEqual(matcher.match_option("anything", ["alpha", "beta"]), "alpha")
        self.assertIsNone(matcher.match_option("anything", []))


if __name__ == "__main__":
    unittest.main()
