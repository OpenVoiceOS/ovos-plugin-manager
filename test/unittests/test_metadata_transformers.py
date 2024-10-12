import unittest

from unittest.mock import patch
from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes


class TestMetadataTransformerTemplate(unittest.TestCase):
    def test_metadata_transformer(self):
        from ovos_plugin_manager.templates.transformers import MetadataTransformer
        # TODO


class TestMedatadataTransformer(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.METADATA_TRANSFORMER
    CONFIG_TYPE = PluginConfigTypes.METADATA_TRANSFORMER
    TEST_CONFIG = {"test": True}
    CONFIG_SECTION = ""
    TEST_LANG = "en-US"

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.metadata_transformers import \
            find_metadata_transformer_plugins
        find_metadata_transformer_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_plugin(self, load_plugin):
        from ovos_plugin_manager.metadata_transformers import \
            load_metadata_transformer_plugin
        load_metadata_transformer_plugin("test_mod")
        load_plugin.assert_called_once_with("test_mod", self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_configs_for_plugin_type")
    def test_get_configs(self, load_configs):
        from ovos_plugin_manager.metadata_transformers import \
            get_metadata_transformer_configs
        get_metadata_transformer_configs()
        load_configs.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_plugin_configs")
    def test_get_module_configs(self, load_plugin_configs):
        from ovos_plugin_manager.metadata_transformers import \
            get_metadata_transformer_module_configs
        get_metadata_transformer_module_configs("test_mod")
        load_plugin_configs.assert_called_once_with("test_mod",
                                                    self.CONFIG_TYPE, True)

    @patch("ovos_plugin_manager.utils.config.get_plugin_language_configs")
    def test_get_lang_configs(self, get_language_configs):
        from ovos_plugin_manager.metadata_transformers import \
            get_metadata_transformer_lang_configs
        get_metadata_transformer_lang_configs(self.TEST_LANG)
        get_language_configs.assert_called_once_with(self.PLUGIN_TYPE,
                                                     self.TEST_LANG, False)

    @patch("ovos_plugin_manager.utils.config.get_plugin_supported_languages")
    def test_get_supported_langs(self, get_supported_languages):
        from ovos_plugin_manager.metadata_transformers import \
            get_metadata_transformer_supported_langs
        get_metadata_transformer_supported_langs()
        get_supported_languages.assert_called_once_with(self.PLUGIN_TYPE)
