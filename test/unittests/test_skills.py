import unittest
from unittest.mock import patch

from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes


class TestSkills(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.SKILL
    CONFIG_TYPE = PluginConfigTypes.SKILL
    TEST_CONFIG = {"test": True}
    CONFIG_SECTION = ""

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.skills import find_skill_plugins
        find_skill_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)

    def test_load_skill_plugins(self):
        from ovos_plugin_manager.skills import load_skill_plugins
        # TODO
