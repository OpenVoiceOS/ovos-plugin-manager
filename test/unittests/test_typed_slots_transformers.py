import unittest
from unittest.mock import patch

from ovos_plugin_manager.utils import PluginTypes


class TestTypedSlotsTransformerTemplate(unittest.TestCase):

    @patch("ovos_plugin_manager.templates.transformers.Configuration", return_value={})
    def test_init_defaults(self, _):
        from ovos_plugin_manager.templates.transformers import TypedSlotsTransformer
        t = TypedSlotsTransformer("typed-slots")
        self.assertEqual(t.name, "typed-slots")
        self.assertEqual(t.priority, 50)
        self.assertEqual(t.config, {})
        self.assertIsNone(t.bus)
        self.assertEqual(t.supported_types, frozenset())

    @patch("ovos_plugin_manager.templates.transformers.Configuration", return_value={})
    def test_init_custom_priority_and_config(self, _):
        from ovos_plugin_manager.templates.transformers import TypedSlotsTransformer
        t = TypedSlotsTransformer("typed-slots", priority=10, config={"key": "val"})
        self.assertEqual(t.priority, 10)
        self.assertEqual(t.config, {"key": "val"})

    @patch("ovos_plugin_manager.templates.transformers.Configuration", return_value={})
    def test_transform_base_returns_empty_map_and_no_mutation(self, _):
        from ovos_plugin_manager.templates.transformers import TypedSlotsTransformer
        t = TypedSlotsTransformer("typed-slots")
        utterances = ["set an alarm for tomorrow"]
        snapshot = list(utterances)  # independent copy to detect in-place mutation
        result = t.transform(utterances, frozenset({"date"}), session=None)
        self.assertIsInstance(result, dict)
        self.assertEqual(result, {})
        # the base implementation MUST NOT mutate the utterance list in place
        self.assertEqual(utterances, snapshot)

    @patch("ovos_plugin_manager.templates.transformers.get_mycroft_bus")
    @patch("ovos_plugin_manager.templates.transformers.Configuration", return_value={})
    def test_bind(self, _, mock_bus):
        from unittest.mock import MagicMock
        from ovos_plugin_manager.templates.transformers import TypedSlotsTransformer
        fake_bus = MagicMock()
        mock_bus.return_value = fake_bus
        t = TypedSlotsTransformer("typed-slots")
        t.bind()
        self.assertIs(t.bus, fake_bus)

    @patch("ovos_plugin_manager.templates.transformers.Configuration", return_value={})
    def test_default_shutdown(self, _):
        from ovos_plugin_manager.templates.transformers import TypedSlotsTransformer
        TypedSlotsTransformer("typed-slots").default_shutdown()  # must not raise

    @patch("ovos_plugin_manager.templates.transformers.Configuration", return_value={})
    def test_subclass_map_passthrough(self, _):
        from ovos_plugin_manager.templates.transformers import TypedSlotsTransformer

        class _DateTransformer(TypedSlotsTransformer):
            supported_types = frozenset({"date"})

            def transform(self, utterances, declared_types, session):
                return {"date": [{"span": [12, 21], "surface": "tomorrow",
                                   "value": "2026-09-07"}]}

        t = _DateTransformer("date-transformer")
        expected = {"date": [{"span": [12, 21], "surface": "tomorrow",
                               "value": "2026-09-07"}]}
        result = t.transform(["set an alarm for tomorrow"], frozenset({"date"}), session=None)
        self.assertEqual(result, expected)
        self.assertEqual(t.supported_types, frozenset({"date"}))


class TestTypedSlotsTransformerPluginUtils(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.TYPED_SLOTS_TRANSFORMER

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.typed_slots_transformers import find_typed_slots_transformer_plugins
        find_typed_slots_transformer_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_plugin(self, load_plugin):
        from ovos_plugin_manager.typed_slots_transformers import load_typed_slots_transformer_plugin
        load_typed_slots_transformer_plugin("test_mod")
        load_plugin.assert_called_once_with("test_mod", self.PLUGIN_TYPE)

    def test_find_plugins_discovers_entry_point_stub(self):
        """Simulate a plugin registered under the ``opm.transformer.typed_slots``
        entry-point group and confirm discovery returns it, mirroring how
        the other transformer kinds are exercised via ``find_plugins``.
        """
        from ovos_plugin_manager.templates.transformers import TypedSlotsTransformer

        class _StubTypedSlotsTransformer(TypedSlotsTransformer):
            supported_types = frozenset({"date"})

        fake_entry_point = type(
            "FakeEntryPoint", (), {
                "name": "ovos-typed-slots-transformer-stub-plugin",
                "load": lambda self: _StubTypedSlotsTransformer,
            }
        )()

        with patch("ovos_plugin_manager.utils._iter_entrypoints",
                   return_value=[fake_entry_point]):
            from ovos_plugin_manager.typed_slots_transformers import find_typed_slots_transformer_plugins
            plugins = find_typed_slots_transformer_plugins()

        self.assertIn("ovos-typed-slots-transformer-stub-plugin", plugins)
        self.assertIs(plugins["ovos-typed-slots-transformer-stub-plugin"],
                      _StubTypedSlotsTransformer)
