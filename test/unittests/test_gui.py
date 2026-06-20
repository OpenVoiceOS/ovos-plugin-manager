import unittest

from unittest.mock import patch, MagicMock
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
    TEST_LANG = "en-US"

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
                                                    self.CONFIG_TYPE)

    @patch("ovos_plugin_manager.utils.config.get_plugin_config")
    def test_get_config(self, get_config):
        from ovos_plugin_manager.gui import get_gui_config
        get_gui_config(self.TEST_CONFIG)
        get_config.assert_called_once_with(self.TEST_CONFIG,
                                           self.CONFIG_SECTION)


class TestGuiFactory(unittest.TestCase):
    from ovos_plugin_manager.gui import OVOSGuiFactory
    # TODO


class TestGuiAdapter(unittest.TestCase):
    """opm.gui_adapter loader functions."""
    PLUGIN_TYPE = PluginTypes.GUI_ADAPTER
    CONFIG_TYPE = PluginConfigTypes.GUI_ADAPTER

    def test_plugin_type_registered(self):
        self.assertEqual(PluginTypes.GUI_ADAPTER.value, "opm.gui_adapter")
        self.assertEqual(PluginConfigTypes.GUI_ADAPTER.value,
                         "opm.gui_adapter.config")

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.gui import find_gui_adapter_plugins
        find_gui_adapter_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_plugin(self, load_plugin):
        from ovos_plugin_manager.gui import load_gui_adapter_plugin
        load_gui_adapter_plugin("test_mod")
        load_plugin.assert_called_once_with("test_mod", self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_configs_for_plugin_type")
    def test_get_configs(self, load_configs):
        from ovos_plugin_manager.gui import get_gui_adapter_configs
        get_gui_adapter_configs()
        load_configs.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_plugin_configs")
    def test_get_module_configs(self, load_plugin_configs):
        from ovos_plugin_manager.gui import get_gui_adapter_module_configs
        load_plugin_configs.return_value = [{"a": 1}]
        cfgs = get_gui_adapter_module_configs("test_mod")
        load_plugin_configs.assert_called_once_with("test_mod", self.CONFIG_TYPE)
        self.assertEqual(cfgs, {"test_mod": [{"a": 1}]})


class TestGUIAdapterFactory(unittest.TestCase):
    """OVOSGUIAdapterFactory.create_all — additive multi-adapter loading."""

    @patch("ovos_plugin_manager.gui.find_gui_adapter_plugins")
    def test_create_all_empty_when_none_installed(self, find_adapters):
        from ovos_plugin_manager.gui import OVOSGUIAdapterFactory
        find_adapters.return_value = {}
        self.assertEqual(OVOSGUIAdapterFactory.create_all(), [])

    @patch("ovos_plugin_manager.gui.load_gui_adapter_plugin")
    @patch("ovos_plugin_manager.gui.find_gui_adapter_plugins")
    def test_create_all_instantiates_every_adapter(self, find_adapters, load):
        from ovos_plugin_manager.gui import OVOSGUIAdapterFactory
        find_adapters.return_value = {"a": object(), "b": object()}
        load.side_effect = lambda name: MagicMock(name=f"cls_{name}")
        bus = MagicMock()
        adapters = OVOSGUIAdapterFactory.create_all(bus=bus,
                                                    config={"a": {"k": 1}})
        self.assertEqual(len(adapters), 2)

    @patch("ovos_plugin_manager.gui.load_gui_adapter_plugin")
    @patch("ovos_plugin_manager.gui.find_gui_adapter_plugins")
    def test_create_all_skips_failing_adapter(self, find_adapters, load):
        from ovos_plugin_manager.gui import OVOSGUIAdapterFactory

        def _load(name):
            if name == "bad":
                raise RuntimeError("boom")
            return MagicMock()

        find_adapters.return_value = {"good": object(), "bad": object()}
        load.side_effect = _load
        adapters = OVOSGUIAdapterFactory.create_all()
        # one bad adapter must not prevent the good one from loading
        self.assertEqual(len(adapters), 1)


class TestAbstractGUIPlugin(unittest.TestCase):
    """Template dispatch + session_id-only contract."""

    def _adapter(self):
        from ovos_plugin_manager.templates.gui import AbstractGUIPlugin
        return AbstractGUIPlugin({}, bus=MagicMock())

    def test_dispatch_routes_to_handler(self):
        adapter = self._adapter()
        adapter.handle_show_weather = MagicMock()
        adapter.dispatch_template("SYSTEM_weather", "skill.test",
                                  {"current_temp": 22}, "default")
        adapter.handle_show_weather.assert_called_once_with(
            "skill.test", {"current_temp": 22}, "default")

    def test_dispatch_unknown_template_is_safe(self):
        adapter = self._adapter()
        # must not raise on an unknown template
        adapter.dispatch_template("SYSTEM_does_not_exist", "skill.test", {})

    def test_dispatch_swallows_handler_exception(self):
        adapter = self._adapter()
        adapter.handle_show_text = MagicMock(side_effect=RuntimeError("boom"))
        # a crashing adapter handler must not propagate to ovos-gui
        adapter.dispatch_template("SYSTEM_text", "skill.test", {"text": "hi"})

    def test_hooks_use_session_id(self):
        import inspect
        from ovos_plugin_manager.templates.gui import AbstractGUIPlugin
        for name in ("on_namespace_activated", "on_namespace_deactivated",
                     "on_status_event", "on_session_update", "dispatch_template"):
            params = inspect.signature(getattr(AbstractGUIPlugin, name)).parameters
            self.assertIn("session_id", params)
            self.assertNotIn("site_id", params)
