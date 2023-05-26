import unittest
from unittest.mock import patch

from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes


class TestTextTransformersTemplate(unittest.TestCase):
    def test_utterance_transformer(self):
        from ovos_plugin_manager.templates.transformers import UtteranceTransformer
        # TODO


class TestTextTransformers(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.UTTERANCE_TRANSFORMER
    CONFIG_TYPE = PluginConfigTypes.UTTERANCE_TRANSFORMER
    TEST_CONFIG = {"test": True}
    CONFIG_SECTION = ""
    TEST_LANG = "en-us"

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.text_transformers import \
            find_utterance_transformer_plugins
        find_utterance_transformer_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_plugin(self, load_plugin):
        from ovos_plugin_manager.text_transformers import \
            load_utterance_transformer_plugin
        load_utterance_transformer_plugin("test_mod")
        load_plugin.assert_called_once_with("test_mod", self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_configs_for_plugin_type")
    def test_get_configs(self, load_configs):
        from ovos_plugin_manager.text_transformers import \
            get_utterance_transformer_configs
        get_utterance_transformer_configs()
        load_configs.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_plugin_configs")
    def test_get_module_configs(self, load_plugin_configs):
        from ovos_plugin_manager.text_transformers import \
            get_utterance_transformer_module_configs
        get_utterance_transformer_module_configs("test_mod")
        load_plugin_configs.assert_called_once_with("test_mod",
                                                    self.CONFIG_TYPE, True)

    @patch("ovos_plugin_manager.utils.config.get_plugin_language_configs")
    def test_get_lang_configs(self, get_language_configs):
        from ovos_plugin_manager.text_transformers import \
            get_utterance_transformer_lang_configs
        get_utterance_transformer_lang_configs(self.TEST_LANG)
        get_language_configs.assert_called_once_with(self.PLUGIN_TYPE,
                                                     self.TEST_LANG, False)

    @patch("ovos_plugin_manager.utils.config.get_plugin_supported_languages")
    def test_get_supported_langs(self, get_supported_languages):
        from ovos_plugin_manager.text_transformers import \
            get_utterance_transformer_supported_langs
        get_utterance_transformer_supported_langs()
        get_supported_languages.assert_called_once_with(self.PLUGIN_TYPE)
