import unittest

from unittest.mock import patch
from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes


class TestPHALTemplate(unittest.TestCase):
    def test_PHAL_Validator(self):
        from ovos_plugin_manager.templates.phal import PHALValidator
        self.assertTrue(PHALValidator.validate())
        self.assertTrue(PHALValidator.validate({"test": "val"}))
        self.assertTrue(PHALValidator.validate({"enabled": True}))
        self.assertFalse(PHALValidator.validate({"enabled": False}))
        self.assertFalse(PHALValidator.validate({"enabled": None}))

    def test_PHAL_Plugin(self):
        from ovos_plugin_manager.templates.phal import PHALValidator
        # TODO

    def test_Admin_Validator(self):
        from ovos_plugin_manager.templates.phal import AdminValidator
        self.assertTrue(AdminValidator.validate())
        self.assertTrue(AdminValidator.validate({"test": "val"}))
        self.assertTrue(AdminValidator.validate({"enabled": True}))
        self.assertFalse(AdminValidator.validate({"enabled": False}))
        self.assertFalse(AdminValidator.validate({"enabled": None}))

    def test_Admin_Plugin(self):
        from ovos_plugin_manager.templates.phal import AdminPlugin
        # TODO

class TestPHAL(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.PHAL
    CONFIG_TYPE = PluginConfigTypes.PHAL
    TEST_CONFIG = {"test": True}
    CONFIG_SECTION = ""
    TEST_LANG = "en-us"

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.phal import find_phal_plugins
        find_phal_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_configs_for_plugin_type")
    def test_get_configs(self, load_configs):
        from ovos_plugin_manager.phal import get_phal_configs
        get_phal_configs()
        load_configs.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_plugin_configs")
    def test_get_module_configs(self, load_plugin_configs):
        from ovos_plugin_manager.phal import get_phal_module_configs
        get_phal_module_configs("test_mod")
        load_plugin_configs.assert_called_once_with("test_mod",
                                                    self.CONFIG_TYPE)


class TestAdminPHAL(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.ADMIN
    CONFIG_TYPE = PluginConfigTypes.ADMIN
    TEST_CONFIG = {"test": True}
    CONFIG_SECTION = ""
    TEST_LANG = "en-us"

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.phal import find_admin_plugins
        find_admin_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_configs_for_plugin_type")
    def test_get_configs(self, load_configs):
        from ovos_plugin_manager.phal import get_admin_configs
        get_admin_configs()
        load_configs.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_plugin_configs")
    def test_get_module_configs(self, load_plugin_configs):
        from ovos_plugin_manager.phal import get_admin_module_configs
        get_admin_module_configs("test_mod")
        load_plugin_configs.assert_called_once_with("test_mod",
                                                    self.CONFIG_TYPE)
