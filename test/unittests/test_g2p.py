import unittest

from unittest.mock import patch
from enum import Enum
from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes


class TestG2PTemplate(unittest.TestCase):
    def test_phoneme_alphabet(self):
        from ovos_plugin_manager.templates.g2p import PhonemeAlphabet
        for alpha in (PhonemeAlphabet.ARPA, PhonemeAlphabet.IPA):
            self.assertIsInstance(alpha, Enum)
            self.assertIsInstance(alpha, str)
            self.assertIsInstance(alpha.value, str)

    def test_grapheme_to_phoneme(self):
        from ovos_plugin_manager.templates.g2p import Grapheme2PhonemePlugin
        # TODO


class TestG2P(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.PHONEME
    CONFIG_TYPE = PluginConfigTypes.PHONEME
    TEST_CONFIG = {"test": True}
    CONFIG_SECTION = "g2p"
    TEST_LANG = "en-us"

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.g2p import find_g2p_plugins
        find_g2p_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_plugin(self, load_plugin):
        from ovos_plugin_manager.g2p import load_g2p_plugin
        load_g2p_plugin("test_mod")
        load_plugin.assert_called_once_with("test_mod", self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_configs_for_plugin_type")
    def test_get_configs(self, load_configs):
        from ovos_plugin_manager.g2p import get_g2p_configs
        get_g2p_configs()
        load_configs.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_plugin_configs")
    def test_get_module_configs(self, load_plugin_configs):
        from ovos_plugin_manager.g2p import get_g2p_module_configs
        get_g2p_module_configs("test_mod")
        load_plugin_configs.assert_called_once_with("test_mod",
                                                    self.CONFIG_TYPE, True)

    @patch("ovos_plugin_manager.utils.config.get_plugin_language_configs")
    def test_get_lang_configs(self, get_language_configs):
        from ovos_plugin_manager.g2p import get_g2p_lang_configs
        get_g2p_lang_configs(self.TEST_LANG)
        get_language_configs.assert_called_once_with(self.PLUGIN_TYPE,
                                                     self.TEST_LANG, False)

    @patch("ovos_plugin_manager.utils.config.get_plugin_supported_languages")
    def test_get_supported_langs(self, get_supported_languages):
        from ovos_plugin_manager.g2p import get_g2p_supported_langs
        get_g2p_supported_langs()
        get_supported_languages.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.get_plugin_config")
    def test_get_config(self, get_config):
        from ovos_plugin_manager.g2p import get_g2p_config
        get_g2p_config(self.TEST_CONFIG)
        get_config.assert_called_once_with(self.TEST_CONFIG,
                                           self.CONFIG_SECTION)


class TestG2PFactory(unittest.TestCase):
    from ovos_plugin_manager.g2p import OVOSG2PFactory
    # TODO
