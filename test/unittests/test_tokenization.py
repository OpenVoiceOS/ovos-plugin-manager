import unittest

from unittest.mock import patch
from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes


class TestTokenizationTemplate(unittest.TestCase):
    def test_tok(self):
        from ovos_plugin_manager.tokenization import Tokenizer
        tokenizer = Tokenizer()
        spans = tokenizer.span_tokenize("Once upon a time there was a free and open voice assistant")
        self.assertEqual(tokenizer.restore_spans(spans), "Once upon a time there was a free and open voice assistant")
        self.assertEqual(spans,
                         [(0, 4, 'Once'),
                          (5, 9, 'upon'),
                          (10, 11, 'a'),
                          (12, 16, 'time'),
                          (17, 22, 'there'),
                          (23, 26, 'was'),
                          (27, 28, 'a'),
                          (29, 33, 'free'),
                          (34, 37, 'and'),
                          (38, 42, 'open'),
                          (43, 48, 'voice'),
                          (49, 58, 'assistant')])


class TestTokenization(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.TOKENIZATION
    CONFIG_TYPE = PluginConfigTypes.TOKENIZATION
    TEST_CONFIG = {"test": True}
    CONFIG_SECTION = "tokenization"
    TEST_LANG = "en-US"

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.tokenization import find_tokenization_plugins
        find_tokenization_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_plugin(self, load_plugin):
        from ovos_plugin_manager.tokenization import load_tokenization_plugin
        load_tokenization_plugin("test_mod")
        load_plugin.assert_called_once_with("test_mod", self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_configs_for_plugin_type")
    def test_get_configs(self, load_configs):
        from ovos_plugin_manager.tokenization import get_tokenization_configs
        get_tokenization_configs()
        load_configs.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_plugin_configs")
    def test_get_module_configs(self, load_plugin_configs):
        from ovos_plugin_manager.tokenization import get_tokenization_module_configs
        get_tokenization_module_configs("test_mod")
        load_plugin_configs.assert_called_once_with("test_mod",
                                                    self.CONFIG_TYPE, True)

    @patch("ovos_plugin_manager.utils.config.get_plugin_language_configs")
    def test_get_lang_configs(self, get_language_configs):
        from ovos_plugin_manager.tokenization import get_tokenization_lang_configs
        get_tokenization_lang_configs(self.TEST_LANG)
        get_language_configs.assert_called_once_with(self.PLUGIN_TYPE,
                                                     self.TEST_LANG, False)

    @patch("ovos_plugin_manager.utils.config.get_plugin_supported_languages")
    def test_get_supported_langs(self, get_supported_languages):
        from ovos_plugin_manager.tokenization import get_tokenization_supported_langs
        get_tokenization_supported_langs()
        get_supported_languages.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.get_plugin_config")
    def test_get_config(self, get_config):
        from ovos_plugin_manager.tokenization import get_tokenization_config
        get_tokenization_config(self.TEST_CONFIG)
        get_config.assert_called_once_with(self.TEST_CONFIG,
                                           self.CONFIG_SECTION)


class TestTokenizerFactory(unittest.TestCase):
    from ovos_plugin_manager.tokenization import OVOSTokenizerFactory
    # TODO
