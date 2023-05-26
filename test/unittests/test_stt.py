import unittest

from unittest.mock import patch
from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes


class TestSTTTemplate(unittest.TestCase):
    def test_stt(self):
        from ovos_plugin_manager.templates.stt import STT
        # TODO
        
    def test_token_stt(self):
        from ovos_plugin_manager.templates.stt import TokenSTT
        # TODO

    def test_google_json_stt(self):
        from ovos_plugin_manager.templates.stt import GoogleJsonSTT
        # TODO

    def test_basic_stt(self):
        from ovos_plugin_manager.templates.stt import BasicSTT
        # TODO

    def test_key_stt(self):
        from ovos_plugin_manager.templates.stt import KeySTT
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
    TEST_LANG = "en-us"

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
    def test_get_config(self, get_config):
        from ovos_plugin_manager.stt import get_stt_config
        get_stt_config(self.TEST_CONFIG)
        get_config.assert_called_once_with(self.TEST_CONFIG,
                                           self.CONFIG_SECTION)


class TestSTTFactory(unittest.TestCase):
    from ovos_plugin_manager.stt import OVOSSTTFactory
    # TODO
