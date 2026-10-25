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
        classes = {"a": MagicMock(name="cls_a"), "b": MagicMock(name="cls_b")}
        load.side_effect = lambda name: classes[name]
        bus = MagicMock()
        adapters = OVOSGUIAdapterFactory.create_all(bus=bus,
                                                    config={"a": {"k": 1}})
        self.assertEqual(len(adapters), 2)
        classes["a"].assert_called_once_with({"k": 1}, bus=bus)
        classes["b"].assert_called_once_with({}, bus=bus)

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

    @patch("ovos_plugin_manager.templates.gui.LOG")
    def test_dispatch_unknown_template_is_safe(self, log):
        adapter = self._adapter()
        # must not raise on an unknown template
        adapter.dispatch_template("SYSTEM_does_not_exist", "skill.test", {})
        log.warning.assert_called_once()
        self.assertIn("SYSTEM_does_not_exist", log.warning.call_args[0][0])

    @patch("ovos_plugin_manager.templates.gui.LOG")
    def test_dispatch_swallows_handler_exception(self, log):
        adapter = self._adapter()
        adapter.handle_show_text = MagicMock(side_effect=RuntimeError("boom"))
        # a crashing adapter handler must not propagate to ovos-gui
        adapter.dispatch_template("SYSTEM_text", "skill.test", {"text": "hi"})
        adapter.handle_show_text.assert_called_once_with(
            "skill.test", {"text": "hi"}, "default")
        log.exception.assert_called_once()

    def test_hooks_use_session_id(self):
        import inspect
        from ovos_plugin_manager.templates.gui import AbstractGUIPlugin
        for name in ("on_namespace_activated", "on_namespace_deactivated",
                     "on_status_event", "on_session_update", "dispatch_template",
                     "on_legacy_page", "on_idle"):
            params = inspect.signature(getattr(AbstractGUIPlugin, name)).parameters
            self.assertIn("session_id", params)
            self.assertNotIn("site_id", params)

    def test_legacy_page_defaults_to_noop(self):
        adapter = self._adapter()
        self.assertIsNone(adapter.on_legacy_page("skill.test", "time",
                                                 {"time_string": "10:36"}, "default"))
        adapter.bus.assert_not_called()
        self.assertEqual(adapter.bus.method_calls, [])

    def test_legacy_page_is_not_a_template(self):
        from ovos_plugin_manager.templates.gui import AbstractGUIPlugin
        self.assertNotIn("time", AbstractGUIPlugin._TEMPLATE_HANDLERS)
        self.assertNotIn("on_legacy_page", AbstractGUIPlugin._TEMPLATE_HANDLERS.values())

    def test_on_idle_takes_session_with_default(self):
        import inspect
        from ovos_plugin_manager.templates.gui import AbstractGUIPlugin
        param = inspect.signature(AbstractGUIPlugin.on_idle).parameters["session_id"]
        self.assertEqual(param.default, "default")
        self.assertIsNone(self._adapter().on_idle("kitchen"))

    def test_interactive_companions_are_dispatchable(self):
        adapter = self._adapter()
        for name in ("confirm", "select", "input"):
            with patch.object(adapter, f"handle_show_{name}") as handler:
                adapter.dispatch_template(f"SYSTEM_{name}", "skill.test", {"prompt": "?"},
                                          "kitchen")
                handler.assert_called_once_with("skill.test", {"prompt": "?"}, "kitchen")

    def test_any_client_connected_defaults_false(self):
        self.assertFalse(self._adapter().any_client_connected())


class TestGUITemplateImport(unittest.TestCase):
    """The adapter base must import without ovos-gui (ovos-gui depends on OPM)."""

    def test_module_load_does_not_import_ovos_gui(self):
        import builtins
        import importlib
        import ovos_plugin_manager.templates.gui as gui_templates
        real_import = builtins.__import__
        attempted = []

        def recording_import(name, *args, **kwargs):
            attempted.append(name)
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", recording_import):
            importlib.reload(gui_templates)
        importlib.reload(gui_templates)
        self.assertFalse([n for n in attempted if n.startswith("ovos_gui")])
