import unittest
from typing import List
from unittest.mock import patch

from ovos_plugin_manager.templates.agent_tools import ToolBox
from ovos_plugin_manager.utils import PluginTypes


class _HidesId(ToolBox):
    """The shape every shipped toolbox uses: id is the plugin's own business."""
    toolbox_id = "hides-id"

    def __init__(self, config=None):
        super().__init__(toolbox_id=self.toolbox_id, config=config)

    def discover_tools(self) -> List:
        return []


class _TakesIdAndBus(ToolBox):
    """The base-class shape, spelled out in full."""

    def __init__(self, toolbox_id, config=None, bus=None):
        super().__init__(toolbox_id, config=config, bus=bus)

    def discover_tools(self) -> List:
        return []


class _TakesKwargs(ToolBox):
    """A plugin that forwards whatever it is given."""

    def __init__(self, **kwargs):
        kwargs.setdefault("toolbox_id", "takes-kwargs")
        super().__init__(**kwargs)

    def discover_tools(self) -> List:
        return []


class TestPersona(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.PERSONA
    TEST_CONFIG = {"test": True}
    CONFIG_SECTION = "persona"
    TEST_LANG = "en-US"

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.persona import find_persona_plugins
        find_persona_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)


class TestInitToolbox(unittest.TestCase):
    """init_toolbox must construct every signature plugins use in the wild."""

    def test_constructs_all_shapes(self):
        from ovos_plugin_manager.persona import init_toolbox
        for clazz in (_HidesId, _TakesIdAndBus, _TakesKwargs):
            with self.subTest(shape=clazz.__name__):
                tb = init_toolbox(clazz, "entry-point-name",
                                  config={"k": "v"})
                self.assertIsInstance(tb, ToolBox)
                self.assertTrue(tb.toolbox_id)

    def test_config_reaches_the_plugin(self):
        from ovos_plugin_manager.persona import init_toolbox
        for clazz in (_HidesId, _TakesIdAndBus, _TakesKwargs):
            with self.subTest(shape=clazz.__name__):
                tb = init_toolbox(clazz, "entry-point-name",
                                  config={"k": "v"})
                self.assertEqual(tb.config, {"k": "v"})

    def test_plugin_id_wins_over_entry_point_name(self):
        # a plugin that declares its own id keeps it; the entry-point name is
        # only a fallback for plugins that declare none
        from ovos_plugin_manager.persona import init_toolbox
        tb = init_toolbox(_HidesId, "some-other-name")
        self.assertEqual(tb.toolbox_id, "hides-id")

        tb = init_toolbox(_TakesIdAndBus, "some-other-name")
        self.assertEqual(tb.toolbox_id, "some-other-name")

    def test_bus_is_bound_whatever_the_signature(self):
        from ovos_utils.fakebus import FakeBus
        from ovos_plugin_manager.persona import init_toolbox
        for clazz in (_HidesId, _TakesIdAndBus, _TakesKwargs):
            with self.subTest(shape=clazz.__name__):
                bus = FakeBus()
                tb = init_toolbox(clazz, "entry-point-name", bus=bus)
                self.assertIs(tb.bus, bus)

    def test_no_bus_leaves_it_unbound(self):
        from ovos_plugin_manager.persona import init_toolbox
        tb = init_toolbox(_HidesId, "entry-point-name")
        self.assertIsNone(tb.bus)

    @patch("ovos_plugin_manager.persona.find_toolbox_plugins")
    def test_load_toolbox_plugin_missing_returns_none(self, find_toolboxes):
        from ovos_plugin_manager.persona import load_toolbox_plugin
        find_toolboxes.return_value = {}
        self.assertIsNone(load_toolbox_plugin("not-installed"))

    @patch("ovos_plugin_manager.persona.find_toolbox_plugins")
    def test_load_toolbox_plugins_skips_failures(self, find_toolboxes):
        from ovos_plugin_manager.persona import load_toolbox_plugins

        class _Explodes(ToolBox):
            def __init__(self, config=None):
                raise RuntimeError("boom")

            def discover_tools(self) -> List:
                return []

        find_toolboxes.return_value = {"good": _HidesId, "bad": _Explodes}
        loaded = load_toolbox_plugins()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].toolbox_id, "hides-id")
