import unittest
from copy import copy, deepcopy
from unittest.mock import patch, Mock

from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes

_TEST_CONFIG = {
    "lang": "en-US",
    "listener": {
        "end_of_turn": {
            "module": "dummy",
            "dummy": {
                "threshold": 0.5
            },
            "ovos-eot-plugin-cuelight": {
                "preset": "careful"
            }
        }
    }
}
_FALLBACK_CONFIG = {
    "end_of_turn": {
        "module": "bad",
        "bad": {"fallback_module": "good"},
        "good": {"a": "b"}
    }
}


class _ConcreteEOT:
    from ovos_plugin_manager.templates.eot import EndOfTurnEngine as _Base

    class _Impl(_Base):
        def get_probability(self, chunk, context=None) -> float:
            # pretend any chunk holding a 0x01 byte ends the turn
            return 1.0 if b'\x01' in chunk else 0.0

        @property
        def p_speech(self):
            return 0.25


_ConcreteEOT = _ConcreteEOT._Impl


class TestEndOfTurnTemplate(unittest.TestCase):

    def test_default_config(self):
        eot = _ConcreteEOT()
        self.assertEqual(eot.threshold, 0.5)
        self.assertEqual(eot.sample_rate, 16000)
        self.assertEqual(eot.supported_langs, ())

    def test_config_override(self):
        eot = _ConcreteEOT(config={"threshold": 0.9}, sample_rate=8000)
        self.assertEqual(eot.threshold, 0.9)
        self.assertEqual(eot.sample_rate, 8000)

    def test_update_decision(self):
        eot = _ConcreteEOT()
        decision = eot.update(b'\x00' * 320)
        self.assertEqual(decision.p_end, 0.0)
        self.assertEqual(decision.p_speech, 0.25)
        self.assertFalse(decision.ended)

        decision = eot.update(b'\x01' * 320)
        self.assertEqual(decision.p_end, 1.0)
        self.assertTrue(decision.ended)

    def test_threshold_gates_decision(self):
        eot = _ConcreteEOT(config={"threshold": 0.5})
        self.assertTrue(eot.is_end_of_turn(b'\x01' * 320))
        eot = _ConcreteEOT(config={"threshold": 1.1})
        self.assertFalse(eot.is_end_of_turn(b'\x01' * 320))

    def test_base_is_noop(self):
        from ovos_plugin_manager.templates.eot import EndOfTurnEngine
        eot = EndOfTurnEngine()
        self.assertEqual(eot.get_probability(b'\x01' * 320), 0.0)
        self.assertIsNone(eot.p_speech)
        self.assertFalse(eot.is_end_of_turn(b'\x01' * 320))
        # reset() should not raise
        eot.reset()

    def test_decision_dataclass(self):
        from ovos_plugin_manager.templates.eot import EndOfTurnDecision
        decision = EndOfTurnDecision(p_end=0.7, p_speech=0.2, ended=True)
        self.assertEqual(decision.p_end, 0.7)
        self.assertEqual(decision.p_speech, 0.2)
        self.assertTrue(decision.ended)

    def test_chunk_context_dataclass(self):
        from ovos_plugin_manager.templates.eot import ChunkContext
        self.assertIsNone(ChunkContext().is_speech)
        self.assertTrue(ChunkContext(is_speech=True).is_speech)

    def test_update_forwards_context(self):
        from ovos_plugin_manager.templates.eot import (
            ChunkContext, EndOfTurnEngine)

        seen = []

        class _ContextEngine(EndOfTurnEngine):
            def get_probability(self, chunk, context=None) -> float:
                seen.append(context)
                if context is not None and context.is_speech:
                    return 1.0
                return 0.0

        eot = _ContextEngine()
        ctx = ChunkContext(is_speech=True)
        self.assertTrue(eot.update(b'\x00' * 320, ctx).ended)
        self.assertTrue(eot.is_end_of_turn(b'\x00' * 320, ctx))
        self.assertEqual(seen, [ctx, ctx])
        # context is optional
        self.assertFalse(eot.update(b'\x00' * 320).ended)

    def test_runtime_requirements(self):
        from ovos_utils.process_utils import RuntimeRequirements
        eot = _ConcreteEOT()
        req = eot.runtime_requirements
        self.assertIsInstance(req, RuntimeRequirements)
        self.assertFalse(req.internet_before_load)
        self.assertFalse(req.requires_internet)


class TestEndOfTurn(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.END_OF_TURN
    CONFIG_TYPE = PluginConfigTypes.END_OF_TURN
    TEST_CONFIG = _TEST_CONFIG['listener']
    CONFIG_SECTION = "end_of_turn"
    TEST_LANG = "en-US"

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.end_of_turn import find_end_of_turn_plugins
        find_end_of_turn_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_plugin(self, load_plugin):
        from ovos_plugin_manager.end_of_turn import load_end_of_turn_plugin
        load_end_of_turn_plugin("test_mod")
        load_plugin.assert_called_once_with("test_mod", self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_configs_for_plugin_type")
    def test_get_configs(self, load_configs):
        from ovos_plugin_manager.end_of_turn import get_end_of_turn_configs
        get_end_of_turn_configs()
        load_configs.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_plugin_configs")
    def test_get_module_configs(self, load_plugin_configs):
        from ovos_plugin_manager.end_of_turn import (
            get_end_of_turn_module_configs)
        get_end_of_turn_module_configs("test_mod")
        load_plugin_configs.assert_called_once_with("test_mod",
                                                    self.CONFIG_TYPE)

    @patch("ovos_plugin_manager.utils.config.get_plugin_config")
    def test_get_config(self, get_config):
        from ovos_plugin_manager.end_of_turn import get_end_of_turn_config
        get_end_of_turn_config(self.TEST_CONFIG)
        get_config.assert_called_once_with(self.TEST_CONFIG,
                                           self.CONFIG_SECTION)


class TestEndOfTurnFactory(unittest.TestCase):
    def test_create(self):
        from ovos_plugin_manager.end_of_turn import OVOSEndOfTurnFactory
        real_get_class = OVOSEndOfTurnFactory.get_class
        mock_class = Mock()

        mock_get_class = Mock(return_value=mock_class)
        OVOSEndOfTurnFactory.get_class = mock_get_class

        OVOSEndOfTurnFactory.create(config=_TEST_CONFIG)
        mock_get_class.assert_called_once_with(
            _TEST_CONFIG['listener']['end_of_turn'])
        mock_class.assert_called_once_with(
            _TEST_CONFIG['listener']["end_of_turn"]['dummy'])

        # Test invalid config
        with self.assertRaises(ValueError):
            OVOSEndOfTurnFactory.create({'end_of_turn': {'value': None}})

        OVOSEndOfTurnFactory.get_class = real_get_class

    def test_create_fallback(self):
        from ovos_plugin_manager.end_of_turn import OVOSEndOfTurnFactory
        real_get_class = OVOSEndOfTurnFactory.get_class
        mock_class = Mock()
        call_args = None
        bad_call_args = None

        def _copy_args(*args):
            nonlocal call_args, bad_call_args
            if args[0]["module"] == "bad":
                bad_call_args = deepcopy(args)
                return None
            call_args = deepcopy(args)
            return mock_class

        mock_get_class = Mock(side_effect=_copy_args)
        OVOSEndOfTurnFactory.get_class = mock_get_class

        OVOSEndOfTurnFactory.create(config=_FALLBACK_CONFIG)
        mock_get_class.assert_called()
        self.assertEqual(call_args[0]["module"], 'good')
        self.assertEqual(bad_call_args[0]["module"], 'bad')
        mock_class.assert_called_once_with(_FALLBACK_CONFIG['end_of_turn']['good'])
        OVOSEndOfTurnFactory.get_class = real_get_class

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_get_class(self, load_plugin):
        mock = Mock()
        load_plugin.return_value = mock
        from ovos_plugin_manager.end_of_turn import OVOSEndOfTurnFactory
        from ovos_plugin_manager.templates.eot import EndOfTurnEngine

        # Test invalid config
        with self.assertRaises(ValueError):
            OVOSEndOfTurnFactory.get_class({'module': None})

        # Test dummy/none/silence modules
        for module_name in ("dummy", "none", "silence"):
            config = deepcopy(_TEST_CONFIG)
            config['listener']['end_of_turn']['module'] = module_name
            module = OVOSEndOfTurnFactory.get_class(config)
            self.assertEqual(EndOfTurnEngine, module)
        load_plugin.assert_not_called()

        # Test valid module
        config = deepcopy(_TEST_CONFIG)
        config['listener']['end_of_turn']['module'] = 'ovos-eot-plugin-cuelight'
        module = OVOSEndOfTurnFactory.get_class(config)
        load_plugin.assert_called_once_with('ovos-eot-plugin-cuelight',
                                            PluginTypes.END_OF_TURN)
        self.assertEqual(module, mock)

    def test_get_end_of_turn_config(self):
        from ovos_plugin_manager.end_of_turn import get_end_of_turn_config
        config = copy(_TEST_CONFIG)
        dummy_config = get_end_of_turn_config(config)
        self.assertEqual(dummy_config,
                         {**_TEST_CONFIG['listener']['end_of_turn']['dummy'],
                          **{'module': 'dummy'}})
        config = copy(_TEST_CONFIG)
        config['listener']['end_of_turn']['module'] = 'ovos-eot-plugin-cuelight'
        plugin_config = get_end_of_turn_config(config)
        self.assertEqual(plugin_config,
                         {**_TEST_CONFIG['listener']['end_of_turn']
                         ['ovos-eot-plugin-cuelight'],
                          **{'module': 'ovos-eot-plugin-cuelight'}})
        config = copy(_TEST_CONFIG)
        config['end_of_turn'] = {'module': 'fake'}
        fake_config = get_end_of_turn_config(config)
        self.assertEqual(fake_config, {'module': 'fake'})
