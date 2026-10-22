import unittest

from unittest.mock import patch, MagicMock
from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes


class TestPHALTemplate(unittest.TestCase):
    def test_PHAL_Validator(self):
        from ovos_plugin_manager.templates.phal import PHALValidator
        self.assertTrue(PHALValidator.validate())
        self.assertTrue(PHALValidator.validate({"test": "val"}))
        self.assertTrue(PHALValidator.validate({"enabled": True}))
        self.assertFalse(PHALValidator.validate({"enabled": False}))
        self.assertFalse(PHALValidator.validate({"enabled": None}))

    @patch("ovos_plugin_manager.templates.phal.get_mycroft_bus")
    @patch("ovos_plugin_manager.templates.phal.Configuration", return_value={})
    def test_PHAL_Plugin(self, mock_cfg, mock_bus):
        from ovos_plugin_manager.templates.phal import PHALPlugin
        mock_bus_instance = MagicMock()
        mock_bus.return_value = mock_bus_instance

        # Prevent the daemon thread from actually starting
        with patch.object(PHALPlugin, "start"):
            plugin = PHALPlugin(bus=mock_bus_instance,
                                name="test-phal",
                                config={"key": "val"})

        self.assertEqual(plugin.name, "test-phal")
        self.assertEqual(plugin.config, {"key": "val"})
        self.assertIs(plugin.bus, mock_bus_instance)
        self.assertIsInstance(plugin.validator, type)

        # emit() should call bus.emit with a correctly scoped message type
        plugin.emit("ready")
        mock_bus_instance.emit.assert_called_once()
        emitted_msg = mock_bus_instance.emit.call_args[0][0]
        self.assertIn("ovos.PHAL.test-phal.ready", emitted_msg.msg_type)

    def test_Admin_Validator(self):
        from ovos_plugin_manager.templates.phal import AdminValidator
        self.assertTrue(AdminValidator.validate())
        self.assertTrue(AdminValidator.validate({"test": "val"}))
        self.assertTrue(AdminValidator.validate({"enabled": True}))
        self.assertFalse(AdminValidator.validate({"enabled": False}))
        self.assertFalse(AdminValidator.validate({"enabled": None}))

    @patch("ovos_plugin_manager.templates.phal.get_mycroft_bus")
    @patch("ovos_plugin_manager.templates.phal.Configuration", return_value={})
    def test_Admin_Plugin(self, mock_cfg, mock_bus):
        from ovos_plugin_manager.templates.phal import AdminPlugin, PHALPlugin
        mock_bus_instance = MagicMock()
        mock_bus.return_value = mock_bus_instance

        with patch.object(AdminPlugin, "start"):
            plugin = AdminPlugin(bus=mock_bus_instance,
                                 name="test-admin",
                                 config={})

        self.assertIsInstance(plugin, PHALPlugin)
        self.assertEqual(plugin.name, "test-admin")

class TestPHAL(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.PHAL
    CONFIG_TYPE = PluginConfigTypes.PHAL
    TEST_CONFIG = {"test": True}
    CONFIG_SECTION = ""
    TEST_LANG = "en-US"

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
    TEST_LANG = "en-US"

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
