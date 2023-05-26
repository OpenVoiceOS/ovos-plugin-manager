import unittest
from unittest.mock import patch

from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes


class TestAudio2IPATemplate(unittest.TestCase):
    def test_audio2ipa(self):
        from ovos_plugin_manager.templates.audio2ipa import Audio2IPA
        # TODO


class TestAudio2IPA(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.AUDIO2IPA
    CONFIG_TYPE = PluginConfigTypes.AUDIO2IPA
    TEST_CONFIG = {"test": True}
    CONFIG_SECTION = "audio2ipa"

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.audio2ipa import find_audio2ipa_plugins
        find_audio2ipa_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_plugin(self, load_plugin):
        from ovos_plugin_manager.audio2ipa import load_audio2ipa_plugin
        load_audio2ipa_plugin("test_mod")
        load_plugin.assert_called_once_with("test_mod", self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.get_plugin_config")
    def test_get_config(self, get_config):
        from ovos_plugin_manager.audio2ipa import get_audio2ipa_config
        get_audio2ipa_config(self.TEST_CONFIG)
        get_config.assert_called_once_with(self.TEST_CONFIG,
                                           self.CONFIG_SECTION)
