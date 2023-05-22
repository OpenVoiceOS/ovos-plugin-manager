import unittest
from unittest.mock import patch, Mock
from copy import copy, deepcopy
from ovos_plugin_manager import PluginTypes

_TEST_CONFIG = {
    "lang": "en-us",
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
        call_args = None

        def _copy_args(*args):
            nonlocal call_args
            call_args = deepcopy(args)
            return mock_class

        mock_get_class = Mock(side_effect=_copy_args)
        OVOSMicrophoneFactory.get_class = mock_get_class

        OVOSMicrophoneFactory.create(config=_TEST_CONFIG)
        mock_get_class.assert_called_once()
        self.assertEqual(call_args, ({**_TEST_CONFIG['microphone']['dummy'],
                                      **{"module": "dummy",
                                         "lang": "en-us"}},))
        mock_class.assert_called_once_with(**_TEST_CONFIG['microphone']['dummy'])
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
        config = copy(_TEST_CONFIG)
        dummy_config = get_microphone_config(config)
        self.assertEqual(dummy_config, {**_TEST_CONFIG['microphone']['dummy'],
                                        **{'module': 'dummy',
                                           'lang': 'en-us'}})
        config = copy(_TEST_CONFIG)
        config['microphone']['module'] = 'ovos-microphone-plugin-alsa'
        alsa_config = get_microphone_config(config)
        self.assertEqual(alsa_config,
                         {**_TEST_CONFIG['microphone']
                          ['ovos-microphone-plugin-alsa'],
                          **{'module': 'ovos-microphone-plugin-alsa',
                             'lang': 'en-us'}})
        config = copy(_TEST_CONFIG)
        config['microphone']['module'] = 'fake'
        fake_config = get_microphone_config(config)
        self.assertEqual(fake_config, {'module': 'fake', 'lang': 'en-us'})
