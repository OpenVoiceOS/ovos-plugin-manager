import unittest
from unittest.mock import patch, Mock
from copy import copy, deepcopy
from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes

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
_FALLBACK_CONFIG = {
    "lang": "en-us",
    "microphone": {
        "module": "bad",
        "bad": {
            "sample_width": 1,
            "sample_channels": 1,
            "chunk_size": 2048,
            "fallback_module": "dummy"
        },
        "dummy": {
            "sample_width": 1,
            "sample_channels": 1,
            "chunk_size": 2048
        },
    }
}


class TestMicrophoneTemplate(unittest.TestCase):
    def test_microphone_init(self):
        from ovos_plugin_manager.templates.microphone import Microphone
        # Default
        mic = Microphone()
        self.assertIsInstance(mic, Microphone)
        self.assertIsInstance(mic.sample_rate, int)
        self.assertIsInstance(mic.sample_width, int)
        self.assertIsInstance(mic.sample_channels, int)
        self.assertIsInstance(mic.chunk_size, int)

        # Partial override with kwargs
        mic_2 = Microphone(**_TEST_CONFIG['microphone']['dummy'])
        self.assertIsInstance(mic_2, Microphone)
        self.assertIsInstance(mic_2.sample_rate, int)
        self.assertEqual(mic_2.sample_width, 1)
        self.assertEqual(mic_2.sample_channels, 1)
        self.assertEqual(mic_2.chunk_size, 2048)

        # Override positional params
        mic_3 = Microphone(1, 2, 3, 4)
        self.assertIsInstance(mic_3, Microphone)
        self.assertEqual(mic_3.sample_rate, 1)
        self.assertEqual(mic_3.sample_width, 2)
        self.assertEqual(mic_3.sample_channels, 3)
        self.assertEqual(mic_3.chunk_size, 4)

        self.assertNotEquals(mic, mic_2)
        self.assertNotEquals(mic, mic_3)

    def test_properties(self):
        from ovos_plugin_manager.templates.microphone import Microphone
        mic = Microphone()
        self.assertIsInstance(mic.frames_per_chunk, int)
        self.assertGreaterEqual(mic.frames_per_chunk, 0)
        self.assertIsInstance(mic.seconds_per_chunk, float)
        self.assertGreaterEqual(mic.seconds_per_chunk, 0)

    def test_methods(self):
        from ovos_plugin_manager.templates.microphone import Microphone
        # Test failure cases
        mic = Microphone()
        with self.assertRaises(NotImplementedError):
            mic.start()
        with self.assertRaises(NotImplementedError):
            mic.read_chunk()
        with self.assertRaises(NotImplementedError):
            mic.stop()

        mock_start = Mock()
        mock_read = Mock(return_value=b'1234')
        mock_stop = Mock()

        class MockMic(Microphone):
            def start(self):
                mock_start()

            def read_chunk(self):
                return mock_read()

            def stop(self):
                mock_stop()

        # Test mic
        mic = MockMic()
        mic.start()
        mock_start.assert_called_once()
        chunk = mic.read_chunk()
        self.assertEqual(chunk, b'1234')
        mock_read.assert_called_once()
        mic.stop()
        mock_stop.assert_called_once()


class TestMicrophone(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.MIC
    CONFIG_TYPE = PluginConfigTypes.MIC
    TEST_CONFIG = {"test": True}
    CONFIG_SECTION = "microphone"
    TEST_LANG = "en-us"

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.microphone import find_microphone_plugins
        find_microphone_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_plugin(self, load_plugin):
        from ovos_plugin_manager.microphone import load_microphone_plugin
        load_microphone_plugin("test_mod")
        load_plugin.assert_called_once_with("test_mod", self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.get_plugin_config")
    def test_get_config(self, get_config):
        from ovos_plugin_manager.microphone import get_microphone_config
        get_microphone_config(self.TEST_CONFIG)
        get_config.assert_called_once_with(self.TEST_CONFIG,
                                           self.CONFIG_SECTION)


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

    def test_create_microphone_fallback(self):
        from ovos_plugin_manager.microphone import OVOSMicrophoneFactory
        real_get_class = OVOSMicrophoneFactory.get_class
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
        OVOSMicrophoneFactory.get_class = mock_get_class

        OVOSMicrophoneFactory.create(config=_FALLBACK_CONFIG)
        mock_get_class.assert_called()
        self.assertEqual(call_args[0]["module"], 'dummy')
        self.assertEqual(bad_call_args[0]["module"], 'bad')
        mock_class.assert_called_once_with(**_FALLBACK_CONFIG['microphone']['dummy'])
        OVOSMicrophoneFactory.get_class = real_get_class

    @patch("ovos_plugin_manager.utils.load_plugin")
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
