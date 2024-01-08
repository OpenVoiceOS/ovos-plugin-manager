import unittest
from unittest.mock import patch

from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes


class TestAudioTemplate(unittest.TestCase):
    def test_audio_backend(self):
        from ovos_plugin_manager.templates.media import AudioBackend
        # TODO

    def test_remote_audio_backend(self):
        from ovos_plugin_manager.templates.media import RemoteAudioBackend


class TestAudio(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.AUDIO
    CONFIG_TYPE = PluginConfigTypes.AUDIO
    TEST_CONFIG = {"test": True}
    CONFIG_SECTION = ""

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.audio import find_audio_service_plugins
        find_audio_service_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_configs_for_plugin_type")
    def test_get_configs(self, load_configs):
        from ovos_plugin_manager.audio import get_audio_service_configs
        get_audio_service_configs()
        load_configs.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_plugin_configs")
    def test_get_module_configs(self, load_plugin_configs):
        from ovos_plugin_manager.audio import get_audio_service_module_configs
        get_audio_service_module_configs("test_mod")
        load_plugin_configs.assert_called_once_with("test_mod",
                                                    self.CONFIG_TYPE)

    def test_setup_audio_service(self):
        from ovos_plugin_manager.audio import setup_audio_service
        # TODO

    def test_load_audio_service_plugins(self):
        from ovos_plugin_manager.audio import load_audio_service_plugins
        # TODO
