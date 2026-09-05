import unittest

from unittest.mock import patch
from ovos_plugin_manager.utils import PluginTypes


class TestIntentTransformerTemplate(unittest.TestCase):
    def test_intent_transformer(self):
        from ovos_plugin_manager.templates.transformers import IntentTransformer
        # Template is abstract, tested via concrete implementations
        self.assertTrue(hasattr(IntentTransformer, 'transform'))


class TestIntentTransformers(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.INTENT_TRANSFORMER

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.intent_transformers import find_intent_transformer_plugins
        find_intent_transformer_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_plugin(self, load_plugin):
        from ovos_plugin_manager.intent_transformers import load_intent_transformer_plugin
        load_intent_transformer_plugin("test_mod")
        load_plugin.assert_called_once_with("test_mod", self.PLUGIN_TYPE)
