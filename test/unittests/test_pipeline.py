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
            """
            Match utterances for a greeting and return a hello intent match.
            
            Parameters:
                utterances (list[str]): List of utterance strings to inspect.
                lang (str): Language code of the utterances (unused by this implementation).
                message (Message): Incoming message object (unused by this implementation).
            
            Returns:
                IntentHandlerMatch or None: An `IntentHandlerMatch` with `match_type` set to `"hello_intent"` and `utterance` set to `"hello"` if any string "hello" appears in `utterances`, `None` otherwise.
            """
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
            """
            Produce a high-confidence IntentHandlerMatch when the provided utterances exactly equal ["exact match"].
            
            Parameters:
                utterances (list[str]): List of utterance strings to evaluate.
                lang (str): Language code of the utterances.
                message (Message): The incoming message object (may be ignored by this matcher).
            
            Returns:
                IntentHandlerMatch or None: An IntentHandlerMatch with `match_type` "high" and `utterance` set to the first utterance when `utterances == ["exact match"]`, `None` otherwise.
            """
            if utterances == ["exact match"]:
                from ovos_plugin_manager.templates.pipeline import IntentHandlerMatch
                return IntentHandlerMatch(match_type="high", utterance=utterances[0])
            return None

        def match_medium(self, utterances, lang, message):
            """
            Attempt a medium-confidence intent match for the provided utterances.
            
            Parameters:
                utterances (list[str]): Candidate utterances to evaluate.
                lang (str): Language code for the utterances.
                message (Message): Original message object associated with the utterances.
            
            Returns:
                IntentHandlerMatch: An IntentHandlerMatch with `match_type` set to "medium" and `utterance` set to the first utterance when `utterances == ["fuzzy match"]`, `None` otherwise.
            """
            if utterances == ["fuzzy match"]:
                from ovos_plugin_manager.templates.pipeline import IntentHandlerMatch
                return IntentHandlerMatch(match_type="medium", utterance=utterances[0])
            return None

        def match_low(self, utterances, lang, message):
            """
            Attempt a low-priority intent match when the utterances list exactly equals ["last resort"].
            
            Parameters:
                utterances (list[str]): Tokenized user utterances to match against.
                lang (str): Language code of the utterances.
                message (Message): The original message object.
            
            Returns:
                IntentHandlerMatch: An `IntentHandlerMatch` with `match_type` set to "low" and `utterance` set to the first element when `utterances == ["last resort"]`, `None` otherwise.
            """
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
        """
        Create a MagicMock configured to mimic a Message instance.
        
        Returns:
            MagicMock: A MagicMock object with its spec set to `Message` from ovos_bus_client.message.
        """
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

    @patch("ovos_plugin_manager.pipeline.find_plugins")
    def test_find_pipeline_plugins(self, mock_find):
        from ovos_plugin_manager.pipeline import find_pipeline_plugins
        find_pipeline_plugins()
        mock_find.assert_called_once_with(PluginTypes.PIPELINE)

    @patch("ovos_plugin_manager.pipeline.load_plugin")
    def test_load_pipeline_plugin(self, mock_load):
        from ovos_plugin_manager.pipeline import load_pipeline_plugin
        load_pipeline_plugin("my-pipeline")
        mock_load.assert_called_once_with("my-pipeline", PluginTypes.PIPELINE)


# ---------------------------------------------------------------------------
# OVOSPipelineFactory
# ---------------------------------------------------------------------------

class TestOVOSPipelineFactory(unittest.TestCase):

    @patch("ovos_plugin_manager.pipeline.find_pipeline_plugins",
           return_value={"pipe-a": _ConcretePipeline, "pipe-b": _ConcretePipeline})
    def test_get_installed_pipeline_ids(self, _):
        from ovos_plugin_manager.pipeline import OVOSPipelineFactory
        ids = OVOSPipelineFactory.get_installed_pipeline_ids()
        self.assertIn("pipe-a", ids)
        self.assertIn("pipe-b", ids)

    @patch("ovos_plugin_manager.pipeline.find_pipeline_plugins",
           return_value={"plain-pipe": _ConcretePipeline})
    def test_get_installed_matcher_ids_plain_plugin(self, _):
        from ovos_plugin_manager.pipeline import OVOSPipelineFactory
        ids = OVOSPipelineFactory.get_installed_pipeline_matcher_ids()
        self.assertIn("plain-pipe", ids)
        # plain PipelinePlugin — no confidence variants expected
        self.assertNotIn("plain-pipe-high", ids)

    @patch("ovos_plugin_manager.pipeline.find_pipeline_plugins",
           return_value={"conf-pipe": _ConcreteConfidenceMatcher})
    def test_get_installed_matcher_ids_confidence_plugin(self, _):
        from ovos_plugin_manager.pipeline import OVOSPipelineFactory
        ids = OVOSPipelineFactory.get_installed_pipeline_matcher_ids()
        self.assertIn("conf-pipe-low", ids)
        self.assertIn("conf-pipe-medium", ids)
        self.assertIn("conf-pipe-high", ids)

    @patch("ovos_plugin_manager.pipeline.find_pipeline_plugins",
           return_value={"my-pipe": _ConcretePipeline})
    def test_load_plugin_returns_instance(self, _):
        from ovos_plugin_manager.pipeline import OVOSPipelineFactory
        instance = OVOSPipelineFactory.load_plugin("my-pipe")
        self.assertIsInstance(instance, _ConcretePipeline)

    @patch("ovos_plugin_manager.pipeline.find_pipeline_plugins", return_value={})
    def test_load_plugin_raises_for_unknown(self, _):
        from ovos_plugin_manager.pipeline import OVOSPipelineFactory
        with self.assertRaises(ValueError):
            OVOSPipelineFactory.load_plugin("nonexistent-pipe")

    @patch("ovos_plugin_manager.pipeline.find_pipeline_plugins",
           return_value={"my-pipe": _ConcretePipeline})
    def test_load_plugin_passes_bus_and_config(self, _):
        from ovos_plugin_manager.pipeline import OVOSPipelineFactory
        fake_bus = MagicMock()
        instance = OVOSPipelineFactory.load_plugin(
            "my-pipe", bus=fake_bus, config={"key": "val"})
        self.assertIs(instance.bus, fake_bus)
        self.assertEqual(instance.config, {"key": "val"})


class TestIntentHandlerMatchFields(unittest.TestCase):
    def test_suppress_activation_defaults_false(self):
        from ovos_plugin_manager.templates.pipeline import IntentHandlerMatch
        m = IntentHandlerMatch(match_type="x:intent", skill_id="x")
        self.assertFalse(m.suppress_activation)

    def test_suppress_activation_settable(self):
        from ovos_plugin_manager.templates.pipeline import IntentHandlerMatch
        m = IntentHandlerMatch(match_type="x:stop", skill_id="x",
                               suppress_activation=True)
        self.assertTrue(m.suppress_activation)
