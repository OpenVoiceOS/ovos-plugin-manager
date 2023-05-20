import unittest
from unittest.mock import patch, Mock

from ovos_plugin_manager import PluginTypes

_TEST_CONFIG = {
    "microphone": {
        "module": "dummy",
        "dummy": {
            "sample_width": 1,
            "sample_channels": 1,
            "chunk_size": 2048
        },
        "ovos-microphone-plugin-alsa": {
            "sample_width": 2,
            "sample_channels": 1,
            "chunk_size": 4096
        }
    }
}


class TestMicrophoneFactory(unittest.TestCase):
    def test_create_microphone(self):
        from ovos_plugin_manager.microphone import OVOSMicrophoneFactory
        real_get_class = OVOSMicrophoneFactory.get_class
        mock_class = Mock()
        mock_get_class = Mock(return_value=mock_class)
        OVOSMicrophoneFactory.get_class = mock_get_class

        OVOSMicrophoneFactory.create(config=_TEST_CONFIG)
        mock_get_class.assert_called_once_with(
            {**_TEST_CONFIG['microphone']['dummy'], **{"module": "dummy"}})
        mock_class.assert_called_once_with(_TEST_CONFIG['microphone']['dummy'])
        OVOSMicrophoneFactory.get_class = real_get_class

    @patch("ovos_plugin_manager.microphone.load_plugin")
    def test_get_class(self, load_plugin):
        mock = Mock()
        load_plugin.return_value = mock
        from ovos_plugin_manager.microphone import OVOSMicrophoneFactory
        # Test valid module
        module = OVOSMicrophoneFactory.get_class(_TEST_CONFIG)
        load_plugin.assert_called_once_with("dummy",
                                            PluginTypes.MIC)
        self.assertEqual(mock, module)

    def test_get_microphone_config(self):
        from ovos_plugin_manager.microphone import get_microphone_config
        config = dict(_TEST_CONFIG)
        dummy_config = get_microphone_config(config)
        self.assertEqual(dummy_config, {**_TEST_CONFIG['microphone']['dummy'],
                                        **{'module': 'dummy'}})
        config['module'] = 'ovos-microphone-plugin-alsa'
        alsa_config = get_microphone_config(config)
        self.assertEqual(alsa_config,
                         {**_TEST_CONFIG['microphone']
                          ['ovos-microphone-plugin-alsa'],
                          **{'module': 'ovos-microphone-plugin-alsa'}})
        config['module'] = 'fake'
        fake_config = get_microphone_config(config)
        self.assertEqual(fake_config, {'module': 'fake'})
