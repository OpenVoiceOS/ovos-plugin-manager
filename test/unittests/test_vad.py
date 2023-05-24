import unittest
from unittest.mock import patch, Mock
from copy import copy, deepcopy
from ovos_plugin_manager import PluginTypes

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

    @patch("ovos_plugin_manager.vad.load_plugin")
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
