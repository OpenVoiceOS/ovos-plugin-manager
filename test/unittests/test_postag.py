import unittest

from unittest.mock import patch
from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes


class TestPostagTemplate(unittest.TestCase):
    def test_PosTagger(self):
        from ovos_plugin_manager.templates.postag import PosTagger
        from ovos_plugin_manager.tokenization import Tokenizer
        solver = PosTagger()
        spans = Tokenizer().span_tokenize("Once upon a time there was a free and open voice assistant")
        # obviously it's almost completely wrong
        self.assertEqual(solver.postag(spans),
                         [(0, 4, 'Once', 'NOUN'),
                          (5, 9, 'upon', 'NOUN'),
                          (10, 11, 'a', 'DET'),
                          (12, 16, 'time', 'NOUN'),
                          (17, 22, 'there', 'NOUN'),
                          (23, 26, 'was', 'VERB'),
                          (27, 28, 'a', 'DET'),
                          (29, 33, 'free', 'NOUN'),
                          (34, 37, 'and', 'CONJ'),
                          (38, 42, 'open', 'NOUN'),
                          (43, 48, 'voice', 'NOUN'),
                          (49, 58, 'assistant', 'NOUN')])

    def test_dummy_postag_pt(self):
        from ovos_plugin_manager.templates.postag import _dummy_postag_pt
        # TODO

    def test_dummy_postag_en(self):
        from ovos_plugin_manager.templates.postag import _dummy_postag_en
        # TODO

    def test_dummy_postag(self):
        from ovos_plugin_manager.templates.postag import _dummy_postag
        # TODO


class TestPostag(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.POSTAG
    CONFIG_TYPE = PluginConfigTypes.POSTAG
    TEST_CONFIG = {"test": True}
    CONFIG_SECTION = "postag"
    TEST_LANG = "en-us"

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.postag import find_postag_plugins
        find_postag_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_plugin(self, load_plugin):
        from ovos_plugin_manager.postag import load_postag_plugin
        load_postag_plugin("test_mod")
        load_plugin.assert_called_once_with("test_mod", self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_configs_for_plugin_type")
    def test_get_configs(self, load_configs):
        from ovos_plugin_manager.postag import get_postag_configs
        get_postag_configs()
        load_configs.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_plugin_configs")
    def test_get_module_configs(self, load_plugin_configs):
        from ovos_plugin_manager.postag import get_postag_module_configs
        get_postag_module_configs("test_mod")
        load_plugin_configs.assert_called_once_with("test_mod",
                                                    self.CONFIG_TYPE, True)

    @patch("ovos_plugin_manager.utils.config.get_plugin_language_configs")
    def test_get_lang_configs(self, get_language_configs):
        from ovos_plugin_manager.postag import get_postag_lang_configs
        get_postag_lang_configs(self.TEST_LANG)
        get_language_configs.assert_called_once_with(self.PLUGIN_TYPE,
                                                     self.TEST_LANG, False)

    @patch("ovos_plugin_manager.utils.config.get_plugin_supported_languages")
    def test_get_supported_langs(self, get_supported_languages):
        from ovos_plugin_manager.postag import get_postag_supported_langs
        get_postag_supported_langs()
        get_supported_languages.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.get_plugin_config")
    def test_get_config(self, get_config):
        from ovos_plugin_manager.postag import get_postag_config
        get_postag_config(self.TEST_CONFIG)
        get_config.assert_called_once_with(self.TEST_CONFIG,
                                           self.CONFIG_SECTION)


class TestPosTaggerFactory(unittest.TestCase):
    from ovos_plugin_manager.postag import OVOSPosTaggerFactory
    # TODO
