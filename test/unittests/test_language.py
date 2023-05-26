import unittest

from unittest.mock import patch
from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes


class TestLanguageTemplate(unittest.TestCase):
    def test_language_detector(self):
        from ovos_plugin_manager.templates.language import LanguageDetector
        # TODO
        
    def test_language_translator(self):
        from ovos_plugin_manager.templates.language import LanguageTranslator
        # TODO


class TestLanguageTranslator(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.TRANSLATE
    CONFIG_TYPE = PluginConfigTypes.TRANSLATE
    TEST_CONFIG = {"test": True}
    CONFIG_SECTION = ""
    TEST_LANG = "en-us"

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.language import find_tx_plugins
        find_tx_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_plugin(self, load_plugin):
        from ovos_plugin_manager.language import load_tx_plugin
        load_tx_plugin("test_mod")
        load_plugin.assert_called_once_with("test_mod", self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_configs_for_plugin_type")
    def test_get_configs(self, load_configs):
        from ovos_plugin_manager.language import get_tx_configs
        get_tx_configs()
        load_configs.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_plugin_configs")
    def test_get_module_configs(self, load_plugin_configs):
        from ovos_plugin_manager.language import \
            get_tx_module_configs
        get_tx_module_configs("test_mod")
        load_plugin_configs.assert_called_once_with("test_mod",
                                                    self.CONFIG_TYPE, True)


class TestLanguageDetector(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.LANG_DETECT
    CONFIG_TYPE = PluginConfigTypes.LANG_DETECT
    TEST_CONFIG = {"test": True}
    CONFIG_SECTION = ""
    TEST_LANG = "en-us"

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.language import find_lang_detect_plugins
        find_lang_detect_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_plugin(self, load_plugin):
        from ovos_plugin_manager.language import load_lang_detect_plugin
        load_lang_detect_plugin("test_mod")
        load_plugin.assert_called_once_with("test_mod", self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_configs_for_plugin_type")
    def test_get_configs(self, load_configs):
        from ovos_plugin_manager.language import get_lang_detect_configs
        get_lang_detect_configs()
        load_configs.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_plugin_configs")
    def test_get_module_configs(self, load_plugin_configs):
        from ovos_plugin_manager.language import \
            get_lang_detect_module_configs
        get_lang_detect_module_configs("test_mod")
        load_plugin_configs.assert_called_once_with("test_mod",
                                                    self.CONFIG_TYPE, True)


class TestLangTranslationFactory(unittest.TestCase):
    from ovos_plugin_manager.language import OVOSLangTranslationFactory
    # TODO


class TestLangDetectionFactory(unittest.TestCase):
    from ovos_plugin_manager.language import OVOSLangDetectionFactory
    # TODO
