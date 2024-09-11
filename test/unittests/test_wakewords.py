import unittest
from unittest.mock import patch, Mock

from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes

_TEST_CONFIG = {
    "hotwords": {
        "hey_neon": {
            "module": "ovos-ww-plugin-vosk",
            "listen": True,
            "active": True
        },
        "hey_mycroft": {
            "module": "ovos-ww-plugin-precise",
            "listen": True,
            "active": True
        }
    }
}


class TestHotwordsTemplate(unittest.TestCase):
    from ovos_plugin_manager.templates.hotwords import HotWordEngine
    # TODO

    def test_msec_to_sec(self):
        from ovos_plugin_manager.templates.hotwords import msec_to_sec
        self.assertEqual(msec_to_sec(1000), 1)
        self.assertEqual(msec_to_sec(-100), -0.1)
        self.assertEqual(msec_to_sec(0.1), 0.0001)


class TestWakewords(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.WAKEWORD
    CONFIG_TYPE = PluginConfigTypes.WAKEWORD
    TEST_CONFIG = {"test": True}
    CONFIG_SECTION = "hotwords"
    TEST_LANG = "en-us"

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.wakewords import find_wake_word_plugins
        find_wake_word_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_plugin(self, load_plugin):
        from ovos_plugin_manager.wakewords import load_wake_word_plugin
        load_wake_word_plugin("test_mod")
        load_plugin.assert_called_once_with("test_mod", self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_configs_for_plugin_type")
    def test_get_configs(self, load_configs):
        from ovos_plugin_manager.wakewords import get_ww_configs
        get_ww_configs()
        load_configs.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_plugin_configs")
    def test_get_module_configs(self, load_plugin_configs):
        from ovos_plugin_manager.wakewords import get_ww_module_configs
        get_ww_module_configs("test_mod")
        load_plugin_configs.assert_called_once_with("test_mod",
                                                    self.CONFIG_TYPE)

    @patch("ovos_plugin_manager.utils.config.get_plugin_language_configs")
    def test_get_lang_configs(self, get_language_configs):
        from ovos_plugin_manager.wakewords import get_ww_lang_configs
        get_ww_lang_configs(self.TEST_LANG)
        get_language_configs.assert_called_once_with(self.PLUGIN_TYPE,
                                                     self.TEST_LANG, False)

    @patch("ovos_plugin_manager.utils.config.get_plugin_supported_languages")
    def test_get_supported_langs(self, get_supported_languages):
        from ovos_plugin_manager.wakewords import get_ww_supported_langs
        get_ww_supported_langs()
        get_supported_languages.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.get_plugin_config")
    def test_get_config(self, get_config):
        from ovos_plugin_manager.wakewords import get_hotwords_config
        get_hotwords_config(self.TEST_CONFIG)
        get_config.assert_called_once_with(self.TEST_CONFIG,
                                           self.CONFIG_SECTION)

    def test_get_ww_id(self):
        from ovos_plugin_manager.wakewords import get_ww_id
        # TODO

    def test_scan_wws(self):
        from ovos_plugin_manager.wakewords import scan_wws
        # TODO

    def test_get_wws(self):
        from ovos_plugin_manager.wakewords import get_wws
        # TODO


class TestWakeWordFactory(unittest.TestCase):
    def test_create_hotword(self):
        from ovos_plugin_manager.wakewords import OVOSWakeWordFactory
        real_load_module = OVOSWakeWordFactory.load_module
        mock_load = Mock()
        OVOSWakeWordFactory.load_module = mock_load

        OVOSWakeWordFactory.create_hotword(config=_TEST_CONFIG)
        mock_load.assert_called_once_with("ovos-ww-plugin-precise", "hey_mycroft",
                                          _TEST_CONFIG["hotwords"]
                                          ['hey_mycroft'], "en-us", None)

        OVOSWakeWordFactory.create_hotword("hey_neon", _TEST_CONFIG)
        mock_load.assert_called_with("ovos-ww-plugin-vosk", "hey_neon",
                                     _TEST_CONFIG["hotwords"]
                                     ['hey_neon'], "en-us", None)
        OVOSWakeWordFactory.load_module = real_load_module

    @patch("ovos_plugin_manager.utils.load_plugin")
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
        real_get_class = OVOSWakeWordFactory.get_class
        mock_get_class = Mock()
        OVOSWakeWordFactory.get_class = mock_get_class

        # Test valid return
        mock_return = Mock()
        mock_get_class.return_value = mock_return
        module = OVOSWakeWordFactory.load_module(
            "ovos-ww-plugin-precise", "hey_mycroft", _TEST_CONFIG['hotwords']['hey_mycroft'],
            'en-us')
        mock_get_class.assert_called_once_with(
            "hey_mycroft", {"lang": "en-us", "hotwords": {
                "hey_mycroft": _TEST_CONFIG['hotwords']['hey_mycroft']}})
        self.assertEqual(module, mock_return())

        # Test no return
        mock_get_class.return_value = None
        with self.assertRaises(ImportError):
            OVOSWakeWordFactory.load_module("dummy", "test", {}, "en-us")

        OVOSWakeWordFactory.get_class = real_get_class
