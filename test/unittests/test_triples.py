import unittest

from unittest.mock import patch
from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes


class TestTriplesTemplate(unittest.TestCase):
    def test_triples_extractor_init_with_config(self):
        from ovos_plugin_manager.templates.triples import TriplesExtractor
        config = {"first_person_token": "I"}

        # Create a concrete implementation for testing
        class ConcreteTriples(TriplesExtractor):
            def extract_triples(self, documents):
                return []

        extractor = ConcreteTriples(config=config)
        self.assertEqual(extractor.config, config)
        self.assertEqual(extractor.first_person_token, "I")

    def test_triples_extractor_init_without_config(self):
        from ovos_plugin_manager.templates.triples import TriplesExtractor

        # Create a concrete implementation for testing
        class ConcreteTriples(TriplesExtractor):
            def extract_triples(self, documents):
                return []

        extractor = ConcreteTriples()
        self.assertEqual(extractor.config, {})
        self.assertEqual(extractor.first_person_token, "USER")


class TestTriples(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.COREFERENCE_SOLVER
    CONFIG_TYPE = PluginConfigTypes.TRIPLES
    TEST_CONFIG = {"test": True}
    CONFIG_SECTION = "triples"
    TEST_LANG = "en-US"

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.triples import find_triples_plugins
        find_triples_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_plugin(self, load_plugin):
        from ovos_plugin_manager.triples import load_triples_plugin
        load_triples_plugin("test_mod")
        load_plugin.assert_called_once_with("test_mod", self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_configs_for_plugin_type")
    def test_get_configs(self, load_configs):
        from ovos_plugin_manager.triples import get_triples_configs
        get_triples_configs()
        load_configs.assert_called_once_with(PluginTypes.TRIPLES)

    @patch("ovos_plugin_manager.utils.config.load_plugin_configs")
    def test_get_module_configs(self, load_plugin_configs):
        from ovos_plugin_manager.triples import get_triples_module_configs
        get_triples_module_configs("test_mod")
        load_plugin_configs.assert_called_once_with("test_mod",
                                                    self.CONFIG_TYPE, True)
