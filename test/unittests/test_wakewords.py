import unittest
from unittest.mock import patch, Mock

from ovos_plugin_manager import PluginTypes

_TEST_CONFIG = {
    "hotwords": {
        "hey_neon": {
            "module": "ovos-ww-plugin-vosk",
            "listen": True,
            "active": True
        },
        "hey_mycroft": {
            "module": "precise",
            "listen": True,
            "active": True
        }
    }
}


class TestWakeWordFactory(unittest.TestCase):
    def test_create_hotword(self):
        from ovos_plugin_manager.wakewords import OVOSWakeWordFactory
        real_load_module = OVOSWakeWordFactory.load_module
        mock_load = Mock()
        OVOSWakeWordFactory.load_module = mock_load

        OVOSWakeWordFactory.create_hotword(config=_TEST_CONFIG)
        mock_load.assert_called_once_with("precise", "hey_mycroft",
                                          _TEST_CONFIG["hotwords"]
                                          ['hey_mycroft'], "en-us", None)

        OVOSWakeWordFactory.create_hotword("hey_neon", _TEST_CONFIG)
        mock_load.assert_called_with("ovos-ww-plugin-vosk", "hey_neon",
                                     _TEST_CONFIG["hotwords"]
                                     ['hey_neon'], "en-us", None)
        OVOSWakeWordFactory.load_module = real_load_module

    @patch("ovos_plugin_manager.wakewords.load_plugin")
    def test_get_class(self, load_plugin):
        mock = Mock()
        load_plugin.return_value = mock
        from ovos_plugin_manager.wakewords import OVOSWakeWordFactory
        # Test valid module
        module = OVOSWakeWordFactory.get_class("hey_neon", _TEST_CONFIG)
        load_plugin.assert_called_once_with("ovos-ww-plugin-vosk",
                                            PluginTypes.WAKEWORD)
        self.assertEqual(mock, module)

        # Test mapped module
        load_plugin.reset_mock()
        module = OVOSWakeWordFactory.get_class("hey_mycroft", _TEST_CONFIG)
        load_plugin.assert_called_once_with("ovos-ww-plugin-precise",
                                            PluginTypes.WAKEWORD)
        self.assertEqual(mock, module)

        # Test invalid module
        load_plugin.reset_mock()
        module = OVOSWakeWordFactory.get_class("invalid_ww", _TEST_CONFIG)
        load_plugin.assert_not_called()
        from ovos_plugin_manager.templates.hotwords import HotWordEngine
        self.assertEqual(module, HotWordEngine)

    def test_load_module(self):
        from ovos_plugin_manager.wakewords import OVOSWakeWordFactory
        # TODO
