import unittest

from unittest.mock import patch
from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes


class TestGuiTemplate(unittest.TestCase):
    def test_gui_extension(self):
        from ovos_plugin_manager.templates.gui import GUIExtension
        # TODO


class TestGui(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.GUI
    CONFIG_TYPE = PluginConfigTypes.GUI
    TEST_CONFIG = {"test": True}
    CONFIG_SECTION = "gui"
    TEST_LANG = "en-us"

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.gui import find_gui_plugins
        find_gui_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_plugin(self, load_plugin):
        from ovos_plugin_manager.gui import load_gui_plugin
        load_gui_plugin("test_mod")
        load_plugin.assert_called_once_with("test_mod", self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_configs_for_plugin_type")
    def test_get_configs(self, load_configs):
        from ovos_plugin_manager.gui import get_gui_configs
        get_gui_configs()
        load_configs.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_plugin_configs")
    def test_get_module_configs(self, load_plugin_configs):
        from ovos_plugin_manager.gui import get_gui_module_configs
        get_gui_module_configs("test_mod")
        load_plugin_configs.assert_called_once_with("test_mod",
                                                    self.CONFIG_TYPE, True)

    @patch("ovos_plugin_manager.utils.config.get_plugin_config")
    def test_get_config(self, get_config):
        from ovos_plugin_manager.gui import get_gui_config
        get_gui_config(self.TEST_CONFIG)
        get_config.assert_called_once_with(self.TEST_CONFIG,
                                           self.CONFIG_SECTION)


class TestGuiFactory(unittest.TestCase):
    from ovos_plugin_manager.gui import OVOSGuiFactory
    # TODO
