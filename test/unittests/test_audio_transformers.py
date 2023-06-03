import unittest
from unittest.mock import patch

from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes


class TestAudioTransformersTemplate(unittest.TestCase):
    def test_audio_transformer(self):
        from ovos_plugin_manager.templates.transformers import AudioTransformer
        # TODO


class TestAudioTransformers(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.AUDIO_TRANSFORMER
    CONFIG_TYPE = PluginConfigTypes.AUDIO_TRANSFORMER
    TEST_CONFIG = {"test": True}
    CONFIG_SECTION = ""

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.audio_transformers import \
            find_audio_transformer_plugins
        find_audio_transformer_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_plugin(self, load_plugin):
        from ovos_plugin_manager.audio_transformers import \
            load_audio_transformer_plugin
        load_audio_transformer_plugin("test_mod")
        load_plugin.assert_called_once_with("test_mod", self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_configs_for_plugin_type")
    def test_get_configs(self, load_configs):
        from ovos_plugin_manager.audio_transformers import \
            get_audio_transformer_configs
        get_audio_transformer_configs()
        load_configs.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_plugin_configs")
    def test_get_module_configs(self, load_plugin_configs):
        from ovos_plugin_manager.audio_transformers import \
            get_audio_transformer_module_configs
        get_audio_transformer_module_configs("test_mod")
        load_plugin_configs.assert_called_once_with("test_mod",
                                                    self.CONFIG_TYPE)
