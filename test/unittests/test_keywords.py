import unittest

from unittest.mock import patch
from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes


class TestKeywordTemplate(unittest.TestCase):
    def test_keyword_extractor(self):
        from ovos_plugin_manager.templates.keywords import KeywordExtractor
        # TODO


class TestKeywords(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.KEYWORD_EXTRACTION
    CONFIG_TYPE = PluginConfigTypes.KEYWORD_EXTRACTION
    TEST_CONFIG = {"test": True}
    CONFIG_SECTION = "keyword_extract"
    TEST_LANG = "en-us"

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.keywords import find_keyword_extract_plugins
        find_keyword_extract_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_plugin(self, load_plugin):
        from ovos_plugin_manager.keywords import load_keyword_extract_plugin
        load_keyword_extract_plugin("test_mod")
        load_plugin.assert_called_once_with("test_mod", self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_configs_for_plugin_type")
    def test_get_configs(self, load_configs):
        from ovos_plugin_manager.keywords import get_keyword_extract_configs
        get_keyword_extract_configs()
        load_configs.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_plugin_configs")
    def test_get_module_configs(self, load_plugin_configs):
        from ovos_plugin_manager.keywords import \
            get_keyword_extract_module_configs
        get_keyword_extract_module_configs("test_mod")
        load_plugin_configs.assert_called_once_with("test_mod",
                                                    self.CONFIG_TYPE, True)

    @patch("ovos_plugin_manager.utils.config.get_plugin_language_configs")
    def test_get_lang_configs(self, get_language_configs):
        from ovos_plugin_manager.keywords import \
            get_keyword_extract_lang_configs
        get_keyword_extract_lang_configs(self.TEST_LANG)
        get_language_configs.assert_called_once_with(self.PLUGIN_TYPE,
                                                     self.TEST_LANG, False)

    @patch("ovos_plugin_manager.utils.config.get_plugin_supported_languages")
    def test_get_supported_langs(self, get_supported_languages):
        from ovos_plugin_manager.keywords import \
            get_keyword_extract_supported_langs
        get_keyword_extract_supported_langs()
        get_supported_languages.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.get_plugin_config")
    def test_get_config(self, get_config):
        from ovos_plugin_manager.keywords import get_keyword_extract_config
        get_keyword_extract_config(self.TEST_CONFIG)
        get_config.assert_called_once_with(self.TEST_CONFIG,
                                           self.CONFIG_SECTION)


class TestKeywordsFactory(unittest.TestCase):
    from ovos_plugin_manager.keywords import OVOSKeywordExtractorFactory
    # TODO
