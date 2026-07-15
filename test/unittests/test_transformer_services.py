import unittest
from unittest.mock import Mock, patch

from ovos_plugin_manager.templates.transformers import (AudioTransformer,
                                                        DialogTransformer,
                                                        MetadataTransformer,
                                                        TTSTransformer,
                                                        UtteranceTransformer)
from ovos_plugin_manager.transformer_services import (
    AudioTransformersService, DialogTransformersService,
    IntentTransformersService, MetadataTransformersService,
    TTSTransformersService, UtteranceTransformersService)


class _UttPrefixer(UtteranceTransformer):
    def __init__(self, name="prefixer", priority=50, config=None):
        super().__init__(name, priority, config or {})

    def transform(self, utterances, context=None):
        return [f"{self.name}:{u}" for u in utterances], {self.name: True}


def _fake_finder(plugins):
    return lambda: plugins


class TestLoadingGate(unittest.TestCase):

    def _service(self, config):
        with patch.object(UtteranceTransformersService, "plugin_finder",
                          staticmethod(_fake_finder({"plug-a": _UttPrefixer,
                                                     "plug-b": _UttPrefixer}))):
            return UtteranceTransformersService(config=config)

    def test_optin_only_named_plugins_load(self):
        service = self._service({"plug-a": {}})
        self.assertEqual(list(service.loaded_plugins), ["plug-a"])
        self.assertTrue(service.has_loaded)

    def test_inactive_plugin_skipped(self):
        service = self._service({"plug-a": {"active": False}, "plug-b": {}})
        self.assertEqual(list(service.loaded_plugins), ["plug-b"])

    def test_empty_config_loads_nothing(self):
        service = self._service({})
        self.assertEqual(service.loaded_plugins, {})

    def test_full_core_config_section_extracted(self):
        service = self._service({"utterance_transformers": {"plug-a": {}},
                                 "lang": "en-US"})
        self.assertEqual(list(service.loaded_plugins), ["plug-a"])

    def test_plugin_receives_config(self):
        plug = Mock()
        with patch.object(UtteranceTransformersService, "plugin_finder",
                          staticmethod(_fake_finder({"plug-a": plug}))):
            UtteranceTransformersService(config={"plug-a": {"key": "val"}})
        plug.assert_called_once_with(config={"key": "val"})

    def test_plugin_without_config_kwarg_falls_back(self):
        class NoConfigPlugin:
            def __init__(self):
                self.priority = 50
                self.name = "no-config"

        with patch.object(UtteranceTransformersService, "plugin_finder",
                          staticmethod(_fake_finder({"plug-a": NoConfigPlugin}))):
            service = UtteranceTransformersService(config={"plug-a": {}})
        self.assertIn("plug-a", service.loaded_plugins)

    def test_constructor_type_error_is_not_masked(self):
        """A TypeError raised INSIDE a config-accepting constructor must not
        trigger a silent no-config retry."""
        calls = []

        class BuggyPlugin:
            def __init__(self, config=None):
                calls.append(config)
                raise TypeError("bug inside constructor")

        with patch.object(UtteranceTransformersService, "plugin_finder",
                          staticmethod(_fake_finder({"plug-a": BuggyPlugin}))):
            service = UtteranceTransformersService(config={"plug-a": {}})
        self.assertNotIn("plug-a", service.loaded_plugins)
        self.assertEqual(calls, [{}])  # constructed once, never retried

    def test_failed_plugin_does_not_break_loading(self):
        bad = Mock(side_effect=Exception("boom"))
        with patch.object(UtteranceTransformersService, "plugin_finder",
                          staticmethod(_fake_finder({"bad": bad,
                                                     "plug-a": _UttPrefixer}))):
            service = UtteranceTransformersService(config={"bad": {}, "plug-a": {}})
        self.assertEqual(list(service.loaded_plugins), ["plug-a"])


class TestPriorityOrdering(unittest.TestCase):

    def _service(self, sort_ascending=True):
        first = _UttPrefixer("first", priority=1)
        last = _UttPrefixer("last", priority=99)
        service = UtteranceTransformersService.__new__(UtteranceTransformersService)
        service.bus = None
        service.sort_ascending = sort_ascending
        service._sorted_plugins = None
        service.loaded_plugins = {"first": first, "last": last}
        service.config = {}
        service.has_loaded = True
        return service

    def test_ascending_default_low_priority_runs_first(self):
        service = self._service(sort_ascending=True)
        self.assertEqual([p.name for p in service.plugins], ["first", "last"])
        utterances, context = service.transform(["hello"])
        self.assertEqual(utterances, ["last:first:hello"])
        self.assertEqual(context, {"first": True, "last": True})

    def test_legacy_descending_low_priority_runs_last(self):
        service = self._service(sort_ascending=False)
        self.assertEqual([p.name for p in service.plugins], ["last", "first"])
        utterances, _ = service.transform(["hello"])
        self.assertEqual(utterances, ["first:last:hello"])


class TestExplicitOrder(unittest.TestCase):
    """OVOS-TRANSFORM §4: explicit deployer order wins over priorities."""

    def _service(self, config):
        plugins = {"plug-a": _UttPrefixer, "plug-b": _UttPrefixer,
                   "plug-c": _UttPrefixer}
        with patch.object(UtteranceTransformersService, "plugin_finder",
                          staticmethod(_fake_finder(plugins))):
            service = UtteranceTransformersService(config=config)
        for name, plugin in service.loaded_plugins.items():
            plugin.name = name
        return service

    def test_order_overrides_priorities(self):
        service = self._service({"plug-a": {"priority": 1}, "plug-b": {},
                                 "order": ["plug-b", "plug-a"]})
        self.assertEqual([p.name for p in service.plugins],
                         ["plug-b", "plug-a"])

    def test_loaded_but_unlisted_plugins_do_not_run(self):
        service = self._service({"plug-a": {}, "plug-b": {},
                                 "order": ["plug-b"]})
        self.assertEqual([p.name for p in service.plugins], ["plug-b"])

    def test_order_enables_plugins_without_config_entry(self):
        service = self._service({"order": ["plug-c"]})
        self.assertEqual(list(service.loaded_plugins), ["plug-c"])

    def test_order_key_is_not_a_plugin(self):
        service = self._service({"plug-a": {}, "order": ["plug-a"]})
        self.assertNotIn("order", service.loaded_plugins)

    def test_shutdown_reaches_plugins_excluded_from_order(self):
        service = self._service({"plug-a": {}, "plug-b": {},
                                 "order": ["plug-b"]})
        stopped = []
        for plugin in service.loaded_plugins.values():
            plugin.shutdown = lambda name=plugin.name: stopped.append(name)
        service.shutdown()
        self.assertEqual(sorted(stopped), ["plug-a", "plug-b"])


class TestCancellation(unittest.TestCase):
    """OVOS-TRANSFORM §8.1 cancellation signal handling."""

    class _Canceller(UtteranceTransformer):
        def __init__(self, name="canceller", priority=1, data=None):
            super().__init__(name, priority, {})
            self.data = data or {"canceled": True, "cancel_reason": "stop_word"}

        def transform(self, utterances, context=None):
            return utterances, dict(self.data)

    def _service(self, *plugins):
        with patch.object(UtteranceTransformersService, "plugin_finder",
                          staticmethod(_fake_finder({}))):
            service = UtteranceTransformersService(config={})
        for p in plugins:
            service.loaded_plugins[p.name] = p
        return service

    def test_valid_signal_stops_chain_and_stamps_cancel_by(self):
        late = _UttPrefixer("late", priority=99)
        service = self._service(self._Canceller(), late)
        utterances, context = service.transform(["hi"])
        self.assertEqual(utterances, ["hi"])  # late plugin never ran
        self.assertTrue(context["canceled"])
        self.assertEqual(context["cancel_reason"], "stop_word")
        self.assertEqual(context["cancel_by"], "canceller")

    def test_cancel_by_cannot_be_spoofed(self):
        canceller = self._Canceller(data={"canceled": True,
                                          "cancel_reason": "policy_block",
                                          "cancel_by": "someone-else"})
        service = self._service(canceller)
        _, context = service.transform(["hi"])
        self.assertEqual(context["cancel_by"], "canceller")

    def test_incomplete_pair_is_stripped_and_chain_continues(self):
        canceller = self._Canceller(data={"canceled": True})  # no reason
        late = _UttPrefixer("late", priority=99)
        service = self._service(canceller, late)
        utterances, context = service.transform(["hi"])
        self.assertEqual(utterances, ["late:hi"])
        self.assertNotIn("canceled", context)
        self.assertNotIn("cancel_by", context)

    def test_reason_without_canceled_is_stripped(self):
        canceller = self._Canceller(data={"cancel_reason": "stop_word"})
        service = self._service(canceller)
        _, context = service.transform(["hi"])
        self.assertNotIn("cancel_reason", context)

    def test_stray_cancel_by_is_stripped(self):
        """cancel_by is orchestrator-stamped only; a plugin-supplied value
        outside a valid cancellation signal never reaches the context."""
        canceller = self._Canceller(data={"cancel_by": "impostor"})
        service = self._service(canceller)
        _, context = service.transform(["hi"])
        self.assertNotIn("cancel_by", context)

    def test_dialog_chain_cancellation(self):
        class CancellingDialog(DialogTransformer):
            def transform(self, dialog, context=None):
                context = context or {}
                context.update({"canceled": True,
                                "cancel_reason": "policy_block"})
                return dialog, context

        class Upper(DialogTransformer):
            def transform(self, dialog, context=None):
                return dialog.upper(), context or {}

        with patch.object(DialogTransformersService, "plugin_finder",
                          staticmethod(_fake_finder({}))):
            service = DialogTransformersService(config={})
        service.loaded_plugins["c"] = CancellingDialog("c", priority=1)
        service.loaded_plugins["u"] = Upper("u", priority=99)
        dialog, context = service.transform("hello")
        self.assertEqual(dialog, "hello")  # chain stopped before Upper
        self.assertEqual(context["cancel_by"], "c")


class TestBusBinding(unittest.TestCase):

    def test_bus_bound_on_load(self):
        bus = Mock()
        plugin = Mock()
        plug = Mock(return_value=plugin)
        with patch.object(IntentTransformersService, "plugin_finder",
                          staticmethod(_fake_finder({"plug-a": plug}))):
            IntentTransformersService(bus=bus, config={"plug-a": {}})
        plugin.bind.assert_called_once_with(bus)

    def test_no_bind_without_bus(self):
        plugin = Mock()
        plug = Mock(return_value=plugin)
        with patch.object(IntentTransformersService, "plugin_finder",
                          staticmethod(_fake_finder({"plug-a": plug}))):
            IntentTransformersService(config={"plug-a": {}})
        plugin.bind.assert_not_called()

    def test_set_bus_binds_loaded_plugins(self):
        bus = Mock()
        plugin = Mock()
        plug = Mock(return_value=plugin)
        with patch.object(TTSTransformersService, "plugin_finder",
                          staticmethod(_fake_finder({"plug-a": plug}))):
            service = TTSTransformersService(config={"plug-a": {}})
        service.set_bus(bus)
        plugin.bind.assert_called_once_with(bus)


class TestServiceTransforms(unittest.TestCase):

    def _empty(self, klass, **kwargs):
        with patch.object(klass, "plugin_finder", staticmethod(_fake_finder({}))):
            return klass(config={}, **kwargs)

    def test_metadata_transform(self):
        class Meta(MetadataTransformer):
            def transform(self, context=None):
                return {"injected": True}

        service = self._empty(MetadataTransformersService)
        service.loaded_plugins["m"] = Meta("m")
        context = service.transform({"seed": 1})
        self.assertEqual(context, {"seed": 1, "injected": True})

    def test_dialog_transform(self):
        class Dialog(DialogTransformer):
            def transform(self, dialog, context=None):
                return dialog.upper(), context or {}

        service = self._empty(DialogTransformersService)
        service.loaded_plugins["d"] = Dialog("d")
        dialog, _ = service.transform("hello")
        self.assertEqual(dialog, "HELLO")

    def test_dialog_blacklisted_skills_default(self):
        service = self._empty(DialogTransformersService)
        self.assertIn("skill-ovos-icanhazdadjokes.openvoiceos",
                      service.blacklisted_skills)

    def test_dialog_from_blacklisted_skill_not_transformed(self):
        class Upper(DialogTransformer):
            def transform(self, dialog, context=None):
                return dialog.upper(), context or {}

        service = self._empty(DialogTransformersService)
        service.loaded_plugins["u"] = Upper("u")
        context = {"skill_id": "skill-ovos-icanhazdadjokes.openvoiceos"}
        dialog, _ = service.transform("why did the chicken", context)
        self.assertEqual(dialog, "why did the chicken")
        dialog, _ = service.transform("hello", {"skill_id": "other.skill"})
        self.assertEqual(dialog, "HELLO")

    def test_tts_transform(self):
        class Tts(TTSTransformer):
            def transform(self, wav_file, context=None):
                return wav_file + ".transformed", context or {}

        service = self._empty(TTSTransformersService)
        service.loaded_plugins["t"] = Tts("t")
        wav, _ = service.transform("/tmp/audio.wav")
        self.assertEqual(wav, "/tmp/audio.wav.transformed")

    def test_plugin_exception_does_not_break_chain(self):
        class Boom(UtteranceTransformer):
            def transform(self, utterances, context=None):
                raise RuntimeError("boom")

        service = self._empty(UtteranceTransformersService)
        service.loaded_plugins["boom"] = Boom("boom", priority=1)
        service.loaded_plugins["ok"] = _UttPrefixer("ok", priority=2)
        utterances, _ = service.transform(["hi"])
        self.assertEqual(utterances, ["ok:hi"])

    def test_shutdown_swallows_errors(self):
        plugin = Mock()
        plugin.shutdown.side_effect = Exception("boom")
        plugin.priority = 50
        service = self._empty(UtteranceTransformersService)
        service.loaded_plugins["p"] = plugin
        service.shutdown()  # must not raise
        plugin.shutdown.assert_called_once()


class TestAudioTransformersService(unittest.TestCase):

    def _empty(self, **kwargs):
        with patch.object(AudioTransformersService, "plugin_finder",
                          staticmethod(_fake_finder({}))):
            return AudioTransformersService(**kwargs)

    def test_top_level_config_section(self):
        service = self._empty(config={"audio_transformers": {"plug-a": {}}})
        self.assertEqual(service.config, {"plug-a": {}})

    def test_legacy_listener_nested_section(self):
        service = self._empty(
            config={"listener": {"audio_transformers": {"plug-a": {}}}})
        self.assertEqual(service.config, {"plug-a": {}})

    def test_top_level_wins_over_legacy(self):
        service = self._empty(config={
            "audio_transformers": {"plug-a": {"x": 2}},
            "listener": {"audio_transformers": {"plug-a": {"x": 1},
                                                "plug-b": {}}}})
        self.assertEqual(service.config,
                         {"plug-a": {"x": 2}, "plug-b": {}})

    def test_transform_merges_context_over_default(self):
        class Audio(AudioTransformer):
            def __init__(self):
                super().__init__("lang-detect", config={})

            def transform(self, audio_data):
                return audio_data, {"stt_lang": "pt-PT"}

        service = self._empty(config={},
                              default_context={"source": "audio"})
        service.loaded_plugins["a"] = Audio()
        chunk, context = service.transform(b"audio-bytes")
        self.assertEqual(chunk, b"audio-bytes")
        self.assertEqual(context, {"source": "audio", "stt_lang": "pt-PT"})

    def test_caller_context_overlays_defaults(self):
        service = self._empty(config={},
                              default_context={"source": "audio",
                                               "destination": ["skills"]})
        _, context = service.transform(b"x", {"source": "hivemind"})
        self.assertEqual(context, {"source": "hivemind",
                                   "destination": ["skills"]})

    def test_broken_feeder_does_not_starve_the_rest(self):
        bad = Mock()
        bad.priority = 1
        bad.name = "bad"
        bad.feed_audio_chunk.side_effect = Exception("boom")
        good = Mock()
        good.priority = 2
        good.name = "good"
        service = self._empty(config={})
        service.loaded_plugins = {"bad": bad, "good": good}
        service._sorted_plugins = None
        service.feed_audio(b"1")
        good.feed_audio_chunk.assert_called_once_with(b"1")

    def test_feed_helpers_reach_plugins(self):
        plugin = Mock()
        plugin.priority = 50
        service = self._empty(config={})
        service.loaded_plugins["a"] = plugin
        service.feed_audio(b"1")
        service.feed_hotword(b"2")
        service.feed_speech(b"3")
        plugin.feed_audio_chunk.assert_called_once_with(b"1")
        plugin.feed_hotword_chunk.assert_called_once_with(b"2")
        plugin.feed_speech_chunk.assert_called_once_with(b"3")


class TestTTSTransformerTemplateConfig(unittest.TestCase):

    @patch("ovos_plugin_manager.templates.transformers.Configuration")
    def test_reads_tts_transformers_section(self, config):
        config.return_value = {"tts_transformers": {"my-plug": {"pitch": 2}},
                               "dialog_transformers": {"my-plug": {"pitch": 1}}}
        plugin = TTSTransformer("my-plug")
        self.assertEqual(plugin.config, {"pitch": 2})


class TestTTSTransformersModule(unittest.TestCase):

    @patch("ovos_plugin_manager.tts_transformers.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.tts_transformers import find_tts_transformer_plugins
        from ovos_plugin_manager.utils import PluginTypes
        find_tts_transformer_plugins()
        find_plugins.assert_called_once_with(PluginTypes.TTS_TRANSFORMER)

    def test_backwards_compat_reexport(self):
        from ovos_plugin_manager.dialog_transformers import (
            find_tts_transformer_plugins, load_tts_transformer_plugin)
        self.assertTrue(callable(find_tts_transformer_plugins))
        self.assertTrue(callable(load_tts_transformer_plugin))


if __name__ == "__main__":
    unittest.main()
