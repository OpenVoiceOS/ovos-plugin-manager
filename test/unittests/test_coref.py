import unittest
from unittest.mock import patch

from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes


class TestCorefTemplate(unittest.TestCase):
    def test_coref(self):
        from ovos_plugin_manager.templates.coreference import CoreferenceSolverEngine
        solver = CoreferenceSolverEngine()

        self.assertFalse(solver.contains_corefs("FOSS is awesome"))
        self.assertFalse(solver.contains_corefs("That is a cool story bro"))

        text = "Turn on the light and change it to blue"
        solved = "Turn on the light and change the light to blue"
        self.assertTrue(solver.contains_corefs(text))
        self.assertEqual(solver.extract_replacements(text, solved),
                         {'it': ['the light']})

        text = "My sister has a dog. She loves him"
        solved = "My sister has a dog. My sister loves a dog"
        self.assertTrue(solver.contains_corefs(text))
        self.assertEqual(solver.extract_replacements(text, solved),
                         {'him': ['a dog'], 'she': ['my sister']})

        solver.add_context("her", "mom")
        text = "tell her to buy eggs"
        self.assertTrue(solver.contains_corefs(text))
        self.assertEqual(solver.replace_coreferences_with_context(text),
                         "tell mom to buy eggs")
        text = "tell her to buy coffee"
        self.assertTrue(solver.contains_corefs(text))
        self.assertEqual(solver.replace_coreferences_with_context(text),
                         "tell mom to buy coffee")
        text = "tell her to buy milk"
        self.assertTrue(solver.contains_corefs(text))
        self.assertEqual(solver.replace_coreferences_with_context(text),
                         "tell mom to buy milk")

    def test_replace_coreferences(self):
        from ovos_plugin_manager.templates.coreference import replace_coreferences
        # TODO


class TestCoref(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.COREFERENCE_SOLVER
    CONFIG_TYPE = PluginConfigTypes.COREFERENCE_SOLVER
    TEST_CONFIG = {"test": True}
    CONFIG_SECTION = "coref"
    TEST_LANG = "en-US"

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.coreference import find_coref_plugins
        find_coref_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_plugin(self, load_plugin):
        from ovos_plugin_manager.coreference import load_coref_plugin
        load_coref_plugin("test_mod")
        load_plugin.assert_called_once_with("test_mod", self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_configs_for_plugin_type")
    def test_get_configs(self, load_configs):
        from ovos_plugin_manager.coreference import get_coref_configs
        get_coref_configs()
        load_configs.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_plugin_configs")
    def test_get_module_configs(self, load_plugin_configs):
        from ovos_plugin_manager.coreference import get_coref_module_configs
        get_coref_module_configs("test_mod")
        load_plugin_configs.assert_called_once_with("test_mod",
                                                    self.CONFIG_TYPE, True)

    @patch("ovos_plugin_manager.utils.config.get_plugin_language_configs")
    def test_get_lang_configs(self, get_language_configs):
        from ovos_plugin_manager.coreference import get_coref_lang_configs
        get_coref_lang_configs(self.TEST_LANG)
        get_language_configs.assert_called_once_with(self.PLUGIN_TYPE,
                                                     self.TEST_LANG, False)

    @patch("ovos_plugin_manager.utils.config.get_plugin_supported_languages")
    def test_get_supported_langs(self, get_supported_languages):
        from ovos_plugin_manager.coreference import get_coref_supported_langs
        get_coref_supported_langs()
        get_supported_languages.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.get_plugin_config")
    def test_get_config(self, get_config):
        from ovos_plugin_manager.coreference import get_coref_config
        get_coref_config(self.TEST_CONFIG)
        get_config.assert_called_once_with(self.TEST_CONFIG,
                                           self.CONFIG_SECTION)


class TestCorefSolverFactory(unittest.TestCase):
    from ovos_plugin_manager.coreference import OVOSCoreferenceSolverFactory
    # TODO
