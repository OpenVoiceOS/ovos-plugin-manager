import unittest
from copy import copy

from unittest.mock import patch, Mock
from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes


class TestSTTTemplate(unittest.TestCase):
    def test_stt(self):
        from ovos_plugin_manager.templates.stt import STT
        # TODO

    def test_stream_thread(self):
        from ovos_plugin_manager.templates.stt import StreamThread
        # TODO

    def test_streaming_stt(self):
        from ovos_plugin_manager.templates.stt import StreamingSTT
        # TODO
    

class TestSTT(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.STT
    CONFIG_TYPE = PluginConfigTypes.STT
    TEST_CONFIG = {"test": True}
    CONFIG_SECTION = "stt"
    TEST_LANG = "en-US"

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.stt import find_stt_plugins
        find_stt_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_plugin(self, load_plugin):
        from ovos_plugin_manager.stt import load_stt_plugin
        load_stt_plugin("test_mod")
        load_plugin.assert_called_once_with("test_mod", self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_configs_for_plugin_type")
    def test_get_configs(self, load_configs):
        from ovos_plugin_manager.stt import get_stt_configs
        get_stt_configs()
        load_configs.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_plugin_configs")
    def test_get_module_configs(self, load_plugin_configs):
        from ovos_plugin_manager.stt import get_stt_module_configs
        get_stt_module_configs("test_mod")
        load_plugin_configs.assert_called_once_with("test_mod",
                                                    self.CONFIG_TYPE, True)

    @patch("ovos_plugin_manager.utils.config.get_plugin_language_configs")
    def test_get_lang_configs(self, get_language_configs):
        from ovos_plugin_manager.stt import get_stt_lang_configs
        get_stt_lang_configs(self.TEST_LANG)
        get_language_configs.assert_called_once_with(self.PLUGIN_TYPE,
                                                     self.TEST_LANG, False)

    @patch("ovos_plugin_manager.utils.config.get_plugin_supported_languages")
    def test_get_supported_langs(self, get_supported_languages):
        from ovos_plugin_manager.stt import get_stt_supported_langs
        get_stt_supported_langs()
        get_supported_languages.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.get_plugin_config")
    def test_get_stt_config(self, get_config):
        from ovos_plugin_manager.stt import get_stt_config
        config = copy(self.TEST_CONFIG)
        get_stt_config(self.TEST_CONFIG)
        get_config.assert_called_once_with(self.TEST_CONFIG,
                                           self.CONFIG_SECTION, None)
        self.assertEqual(config, self.TEST_CONFIG)


class TestSTTFactory(unittest.TestCase):

    @patch("ovos_plugin_manager.stt.load_stt_plugin")
    def test_get_class(self, load_plugin):
        from ovos_plugin_manager.stt import OVOSSTTFactory
        global_config = {"stt": {"module": "ovos-stt-plugin-dummy"}}
        tts_config = {"module": "test-stt-plugin-test"}

        # Test load plugin mapped global config
        OVOSSTTFactory.get_class(global_config)
        load_plugin.assert_called_with("ovos-stt-plugin-dummy")

        # Test load plugin explicit STT config
        OVOSSTTFactory.get_class(tts_config)
        load_plugin.assert_called_with("test-stt-plugin-test")

    @patch("ovos_plugin_manager.stt.OVOSSTTFactory.get_class")
    def test_create(self, get_class):
        from ovos_plugin_manager.stt import OVOSSTTFactory
        plugin_class = Mock()
        get_class.return_value = plugin_class

        global_config = {"lang": "en-gb",
                         "stt": {"module": "ovos-stt-plugin-dummy",
                                 "ovos-stt-plugin-dummy": {"config": True,
                                                           "lang": "en-ca"}}}
        stt_config = {"lang": "es-es",
                      "module": "test-stt-plugin-test"}

        stt_config_2 = {"lang": "es-es",
                        "module": "test-stt-plugin-test",
                        "test-stt-plugin-test": {"config": True,
                                                 "lang": "es-mx"}}

        # Test create with global config and lang override
        plugin = OVOSSTTFactory.create(global_config)
        expected_config = {"module": "ovos-stt-plugin-dummy",
                           "config": True,
                           "lang": "en-ca"}
        get_class.assert_called_once_with(expected_config)
        plugin_class.assert_called_once_with(expected_config)
        self.assertEqual(plugin, plugin_class())

        # Test create with STT config and no module config
        plugin = OVOSSTTFactory.create(stt_config)
        get_class.assert_called_with(stt_config)
        plugin_class.assert_called_with(stt_config)
        self.assertEqual(plugin, plugin_class())

        # Test create with STT config with module-specific config
        plugin = OVOSSTTFactory.create(stt_config_2)
        expected_config = {"module": "test-stt-plugin-test",
                           "config": True, "lang": "es-mx"}
        get_class.assert_called_with(expected_config)
        plugin_class.assert_called_with(expected_config)
        self.assertEqual(plugin, plugin_class())

