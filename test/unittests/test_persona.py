import unittest
from unittest.mock import patch

from ovos_plugin_manager.utils import PluginTypes


class TestPersona(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.PERSONA
    TEST_CONFIG = {"test": True}
    CONFIG_SECTION = "persona"
    TEST_LANG = "en-us"

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.persona import find_persona_plugins
        find_persona_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)
