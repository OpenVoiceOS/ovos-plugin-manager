import unittest
from unittest.mock import MagicMock, patch

from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes


# ---------------------------------------------------------------------------
# Concrete implementations for abstract classes
# ---------------------------------------------------------------------------

class _ConcretePipeline:
    from ovos_plugin_manager.templates.pipeline import PipelinePlugin as _Base

    class _Impl(_Base):
        def match(self, utterances, lang, message):
            if "hello" in utterances:
                from ovos_plugin_manager.templates.pipeline import IntentHandlerMatch
                return IntentHandlerMatch(match_type="hello_intent",
                                         utterance="hello")
            return None


_ConcretePipeline = _ConcretePipeline._Impl


class _ConcreteConfidenceMatcher:
    from ovos_plugin_manager.templates.pipeline import ConfidenceMatcherPipeline as _Base

    class _Impl(_Base):
        def match_high(self, utterances, lang, message):
            if utterances == ["exact match"]:
                from ovos_plugin_manager.templates.pipeline import IntentHandlerMatch
                return IntentHandlerMatch(match_type="high", utterance=utterances[0])
            return None

        def match_medium(self, utterances, lang, message):
            if utterances == ["fuzzy match"]:
                from ovos_plugin_manager.templates.pipeline import IntentHandlerMatch
                return IntentHandlerMatch(match_type="medium", utterance=utterances[0])
            return None

        def match_low(self, utterances, lang, message):
            if utterances == ["last resort"]:
                from ovos_plugin_manager.templates.pipeline import IntentHandlerMatch
                return IntentHandlerMatch(match_type="low", utterance=utterances[0])
            return None


_ConcreteConfidenceMatcher = _ConcreteConfidenceMatcher._Impl


# ---------------------------------------------------------------------------
# IntentHandlerMatch
# ---------------------------------------------------------------------------

class TestIntentHandlerMatch(unittest.TestCase):

    def test_required_field(self):
        from ovos_plugin_manager.templates.pipeline import IntentHandlerMatch
        m = IntentHandlerMatch(match_type="test_intent")
        self.assertEqual(m.match_type, "test_intent")

    def test_optional_fields_default_to_none(self):
        from ovos_plugin_manager.templates.pipeline import IntentHandlerMatch
        m = IntentHandlerMatch(match_type="t")
        self.assertIsNone(m.match_data)
        self.assertIsNone(m.skill_id)
        self.assertIsNone(m.utterance)
        self.assertIsNone(m.updated_session)

    def test_all_fields(self):
        from ovos_plugin_manager.templates.pipeline import IntentHandlerMatch
        m = IntentHandlerMatch(
            match_type="my_intent",
            match_data={"entity": "value"},
            skill_id="my_skill",
            utterance="turn on the lights",
        )
        self.assertEqual(m.match_type, "my_intent")
        self.assertEqual(m.match_data, {"entity": "value"})
        self.assertEqual(m.skill_id, "my_skill")
        self.assertEqual(m.utterance, "turn on the lights")

    def test_equality(self):
        from ovos_plugin_manager.templates.pipeline import IntentHandlerMatch
        a = IntentHandlerMatch(match_type="t", match_data={"k": 1})
        b = IntentHandlerMatch(match_type="t", match_data={"k": 1})
        self.assertEqual(a, b)


# ---------------------------------------------------------------------------
# PipelinePlugin
# ---------------------------------------------------------------------------

class TestPipelinePlugin(unittest.TestCase):

    def test_init_defaults(self):
        p = _ConcretePipeline()
        self.assertIsNotNone(p.bus)
        self.assertEqual(p.config, {})

    def test_init_with_bus_and_config(self):
        fake_bus = MagicMock()
        p = _ConcretePipeline(bus=fake_bus, config={"threshold": 0.5})
        self.assertIs(p.bus, fake_bus)
        self.assertEqual(p.config, {"threshold": 0.5})

    def test_match_returns_match(self):
        from ovos_bus_client.message import Message
        p = _ConcretePipeline()
        msg = MagicMock(spec=Message)
        result = p.match(["hello"], "en-US", msg)
        self.assertIsNotNone(result)
        self.assertEqual(result.match_type, "hello_intent")

    def test_match_returns_none(self):
        from ovos_bus_client.message import Message
        p = _ConcretePipeline()
        msg = MagicMock(spec=Message)
        result = p.match(["goodbye"], "en-US", msg)
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# ConfidenceMatcherPipeline
# ---------------------------------------------------------------------------

class TestConfidenceMatcherPipeline(unittest.TestCase):

    def _make_msg(self):
        from ovos_bus_client.message import Message
        return MagicMock(spec=Message)

    def test_match_high_wins(self):
        p = _ConcreteConfidenceMatcher()
        result = p.match(["exact match"], "en-US", self._make_msg())
        self.assertIsNotNone(result)
        self.assertEqual(result.match_type, "high")

    def test_match_medium_fallback(self):
        p = _ConcreteConfidenceMatcher()
        result = p.match(["fuzzy match"], "en-US", self._make_msg())
        self.assertIsNotNone(result)
        self.assertEqual(result.match_type, "medium")

    def test_match_low_fallback(self):
        p = _ConcreteConfidenceMatcher()
        result = p.match(["last resort"], "en-US", self._make_msg())
        self.assertIsNotNone(result)
        self.assertEqual(result.match_type, "low")

    def test_match_returns_none_when_nothing_matches(self):
        p = _ConcreteConfidenceMatcher()
        result = p.match(["no match at all"], "en-US", self._make_msg())
        self.assertIsNone(result)

    def test_match_high_takes_priority_over_medium(self):
        """high match should short-circuit; medium/low never called."""
        from ovos_plugin_manager.templates.pipeline import IntentHandlerMatch
        p = _ConcreteConfidenceMatcher()
        msg = self._make_msg()

        high_result = IntentHandlerMatch(match_type="high", utterance="exact match")
        p.match_high = MagicMock(return_value=high_result)
        p.match_medium = MagicMock()
        p.match_low = MagicMock()

        result = p.match(["exact match"], "en-US", msg)
        self.assertEqual(result.match_type, "high")
        p.match_medium.assert_not_called()
        p.match_low.assert_not_called()


# ---------------------------------------------------------------------------
# Pipeline plugin discovery helpers
# ---------------------------------------------------------------------------

class TestPipelineUtils(unittest.TestCase):

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_pipeline_plugins(self, mock_find):
        from ovos_plugin_manager.pipeline import find_pipeline_plugins
        find_pipeline_plugins()
        mock_find.assert_called_once_with(PluginTypes.PIPELINE)

    @patch("ovos_plugin_manager.pipeline.load_plugin")
    def test_load_pipeline_plugin(self, mock_load):
        from ovos_plugin_manager.pipeline import load_pipeline_plugin
        load_pipeline_plugin("my-pipeline")
        mock_load.assert_called_once_with("my-pipeline", PluginTypes.PIPELINE)
