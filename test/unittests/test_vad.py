import unittest
from unittest.mock import patch, Mock
from copy import copy, deepcopy
from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes

_TEST_CONFIG = {
    "lang": "en-us",
    "listener": {
        "VAD": {
            "module": "dummy",
            "dummy": {
                "vad_param": True
            },
            "ovos-vad-plugin-webrtcvad": {
                "vad_mode": 2
            }
        }
    }
}


class TestVADTemplate(unittest.TestCase):
    from ovos_plugin_manager.templates.vad import VADEngine
    # TODO


class TestVAD(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.VAD
    CONFIG_TYPE = PluginConfigTypes.VAD
    TEST_CONFIG = _TEST_CONFIG['listener']
    CONFIG_SECTION = "VAD"
    TEST_LANG = "en-us"

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.vad import find_vad_plugins
        find_vad_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_plugin(self, load_plugin):
        from ovos_plugin_manager.vad import load_vad_plugin
        load_vad_plugin("test_mod")
        load_plugin.assert_called_once_with("test_mod", self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_configs_for_plugin_type")
    def test_get_configs(self, load_configs):
        from ovos_plugin_manager.vad import get_vad_configs
        get_vad_configs()
        load_configs.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_plugin_configs")
    def test_get_module_configs(self, load_plugin_configs):
        from ovos_plugin_manager.vad import get_vad_module_configs
        get_vad_module_configs("test_mod")
        load_plugin_configs.assert_called_once_with("test_mod",
                                                    self.CONFIG_TYPE)

    @patch("ovos_plugin_manager.utils.config.get_plugin_config")
    def test_get_config(self, get_config):
        from ovos_plugin_manager.vad import get_vad_config
        get_vad_config(self.TEST_CONFIG)
        get_config.assert_called_once_with(self.TEST_CONFIG,
                                           self.CONFIG_SECTION)


class TestVADFactory(unittest.TestCase):
    def test_create(self):
        from ovos_plugin_manager.vad import OVOSVADFactory
        real_get_class = OVOSVADFactory.get_class
        mock_class = Mock()

        mock_get_class = Mock(return_value=mock_class)
        OVOSVADFactory.get_class = mock_get_class

        OVOSVADFactory.create(config=_TEST_CONFIG)
        mock_get_class.assert_called_once_with(
            {**_TEST_CONFIG['listener']['VAD']['dummy'], **{"module": "dummy"}})
        mock_class.assert_called_once_with(
            _TEST_CONFIG['listener']["VAD"]['dummy'])

        # Test invalid config
        with self.assertRaises(ValueError):
            OVOSVADFactory.create({'VAD': {'value': None}})

        OVOSVADFactory.get_class = real_get_class

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_get_class(self, load_plugin):
        mock = Mock()
        load_plugin.return_value = mock
        from ovos_plugin_manager.vad import OVOSVADFactory
        from ovos_plugin_manager.templates.vad import VADEngine

        # Test invalid config
        with self.assertRaises(ValueError):
            OVOSVADFactory.get_class({'module': None})

        # Test dummy module
        module = OVOSVADFactory.get_class(_TEST_CONFIG)
        load_plugin.assert_not_called()
        self.assertEqual(VADEngine, module)

        # Test valid module
        config = deepcopy(_TEST_CONFIG)
        config['listener']['VAD']['module'] = 'ovos-vad-plugin-webrtcvad'
        module = OVOSVADFactory.get_class(config)
        load_plugin.assert_called_once_with('ovos-vad-plugin-webrtcvad',
                                            PluginTypes.VAD)
        self.assertEqual(module, mock)

    def test_get_vad_config(self):
        from ovos_plugin_manager.vad import get_vad_config
        config = copy(_TEST_CONFIG)
        dummy_config = get_vad_config(config)
        self.assertEqual(dummy_config,
                         {**_TEST_CONFIG['listener']['VAD']['dummy'],
                          **{'module': 'dummy'}})
        config = copy(_TEST_CONFIG)
        config['listener']['VAD']['module'] = 'ovos-vad-plugin-webrtcvad'
        webrtc_config = get_vad_config(config)
        self.assertEqual(webrtc_config,
                         {**_TEST_CONFIG['listener']['VAD']
                          ['ovos-vad-plugin-webrtcvad'],
                          **{'module': 'ovos-vad-plugin-webrtcvad'}})
        config = copy(_TEST_CONFIG)
        config['VAD'] = {'module': 'fake'}
        fake_config = get_vad_config(config)
        self.assertEqual(fake_config, {'module': 'fake'})
