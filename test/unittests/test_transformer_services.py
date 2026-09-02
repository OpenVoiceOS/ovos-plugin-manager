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
        self.assertEqual(context, {"first": True, "last": True,
                                   "utterance_transformer_ids": ["first", "last"]})

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

    def test_legacy_canceled_without_reason_still_cancels(self):
        """Plugins that predate §8.1 signal with 'canceled' alone; the
        cancellation is honored with the spec's fallback reason."""
        canceller = self._Canceller(data={"canceled": True,
                                          "cancel_word": "nevermind"})
        late = _UttPrefixer("late", priority=99)
        service = self._service(canceller, late)
        utterances, context = service.transform(["hi"])
        self.assertEqual(utterances, ["hi"])  # chain stopped
        self.assertTrue(context["canceled"])
        self.assertEqual(context["cancel_reason"], "other")
        self.assertEqual(context["cancel_by"], "canceller")
        self.assertEqual(context["cancel_word"], "nevermind")

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
        self.assertEqual(context, {"seed": 1, "injected": True,
                                   "metadata_transformer_ids": ["m"]})

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

    def test_utterance_transform_debug_log_redacts_session(self):
        secret = {"password": "hunter2", "access_key": "sekrit"}

        class Leaky(UtteranceTransformer):
            def transform(self, utterances, context=None):
                return utterances, {"session": secret}

        service = self._empty(UtteranceTransformersService)
        service.loaded_plugins["leaky"] = Leaky("leaky", priority=1)
        from ovos_plugin_manager.transformer_services import LOG
        with patch.object(LOG, "level", "DEBUG"), \
                patch.object(LOG, "debug") as mock_debug:
            service.transform(["hi"], {})
        self.assertTrue(mock_debug.called)
        logged = "".join(str(a) for call in mock_debug.call_args_list
                          for a in call.args)
        self.assertNotIn("hunter2", logged)
        self.assertNotIn("sekrit", logged)

    def test_metadata_transform_debug_log_redacts_session(self):
        secret = {"password": "hunter2", "access_key": "sekrit"}

        class Leaky(MetadataTransformer):
            def transform(self, context=None):
                return {"session": secret}

        service = self._empty(MetadataTransformersService)
        service.loaded_plugins["leaky"] = Leaky("leaky", priority=1)
        from ovos_plugin_manager.transformer_services import LOG
        with patch.object(LOG, "level", "DEBUG"), \
                patch.object(LOG, "debug") as mock_debug:
            service.transform({})
        self.assertTrue(mock_debug.called)
        logged = "".join(str(a) for call in mock_debug.call_args_list
                          for a in call.args)
        self.assertNotIn("hunter2", logged)
        self.assertNotIn("sekrit", logged)


class TestAudioTransformersService(unittest.TestCase):

    def _empty(self, **kwargs):
        with patch.object(AudioTransformersService, "plugin_finder",
                          staticmethod(_fake_finder({}))):
            return AudioTransformersService(**kwargs)

    def test_top_level_config_section(self):
        service = self._empty(config={"audio_transformers": {"plug-a": {}}})
        self.assertEqual(service.config, {"plug-a": {}})

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


class TestTransform1Conformance(unittest.TestCase):
    """OVOS-TRANSFORM-1 §1.3 provenance, §7 wrong-shape rejection and §3.4
    intent dispatch-identity invariant."""

    def _empty(self, klass, **kwargs):
        with patch.object(klass, "plugin_finder", staticmethod(_fake_finder({}))):
            return klass(config={}, **kwargs)

    # §1.3 -- provenance stamping
    def test_utterance_provenance_stamped_in_order(self):
        p1 = _UttPrefixer("p1", priority=10)
        p2 = _UttPrefixer("p2", priority=20)
        service = self._empty(UtteranceTransformersService)
        service.loaded_plugins["p1"] = p1
        service.loaded_plugins["p2"] = p2
        _, context = service.transform(["hi"])
        self.assertEqual(context.get("utterance_transformer_ids"), ["p1", "p2"])

    def test_metadata_provenance_stamped_in_order(self):
        class Meta(MetadataTransformer):
            def transform(self, context=None):
                return {}

        p1 = Meta("p1", priority=10)
        p2 = Meta("p2", priority=20)
        service = self._empty(MetadataTransformersService)
        service.loaded_plugins["p1"] = p1
        service.loaded_plugins["p2"] = p2
        context = service.transform({})
        self.assertEqual(context.get("metadata_transformer_ids"), ["p1", "p2"])

    def test_in_place_utterance_context_is_not_merged_into_itself(self):
        class InPlace(UtteranceTransformer):
            def transform(self, utterances, context=None):
                context["nested"]["touched"] = True
                return utterances, context

        service = self._empty(UtteranceTransformersService)
        service.loaded_plugins["in-place"] = InPlace("in-place", priority=10)
        original = {"nested": {"lang": "en-us"}}
        _, context = service.transform(["hello"], original)
        self.assertIs(context, original)
        self.assertEqual(context["nested"], {"lang": "en-us", "touched": True})
        self.assertEqual(context["utterance_transformer_ids"], ["in-place"])

    def test_in_place_metadata_context_is_not_merged_into_itself(self):
        class InPlace(MetadataTransformer):
            def transform(self, context=None):
                context["nested"]["touched"] = True
                return context

        service = self._empty(MetadataTransformersService)
        service.loaded_plugins["in-place"] = InPlace("in-place", priority=10)
        original = {"nested": {"lang": "en-us"}}
        context = service.transform(original)
        self.assertIs(context, original)
        self.assertEqual(context["nested"], {"lang": "en-us", "touched": True})
        self.assertEqual(context["metadata_transformer_ids"], ["in-place"])

    def test_empty_utterance_context_preserves_identity(self):
        class InPlace(UtteranceTransformer):
            def transform(self, utterances, context=None):
                context["touched"] = True
                return utterances, context

        service = self._empty(UtteranceTransformersService)
        service.loaded_plugins["in-place"] = InPlace("in-place", priority=10)
        original = {}
        _, context = service.transform(["hello"], original)
        self.assertIs(context, original)
        self.assertTrue(context["touched"])

    def test_empty_metadata_context_preserves_identity(self):
        class InPlace(MetadataTransformer):
            def transform(self, context=None):
                context["touched"] = True
                return context

        service = self._empty(MetadataTransformersService)
        service.loaded_plugins["in-place"] = InPlace("in-place", priority=10)
        original = {}
        context = service.transform(original)
        self.assertIs(context, original)
        self.assertTrue(context["touched"])

    # §7 -- wrong-shape returns rejected, prior output kept
    def test_utterance_wrong_shape_rejected(self):
        class Bad(UtteranceTransformer):
            def transform(self, utterances, context=None):
                return "not a tuple"

        service = self._empty(UtteranceTransformersService)
        service.loaded_plugins["bad"] = Bad("bad", priority=10)
        utterances, context = service.transform(["hello"], {"k": "v"})
        self.assertEqual(utterances, ["hello"])
        self.assertEqual(context, {"k": "v"})

    def test_utterance_wrong_arity_rejected(self):
        class Bad(UtteranceTransformer):
            def transform(self, utterances, context=None):
                return ["x"], {}, "extra"

        service = self._empty(UtteranceTransformersService)
        service.loaded_plugins["bad"] = Bad("bad", priority=10)
        utterances, _ = service.transform(["hello"], {})
        self.assertEqual(utterances, ["hello"])

    def test_utterance_non_dict_context_rejected(self):
        class Bad(UtteranceTransformer):
            def transform(self, utterances, context=None):
                return ["x"], "not a dict"

        service = self._empty(UtteranceTransformersService)
        service.loaded_plugins["bad"] = Bad("bad", priority=10)
        utterances, context = service.transform(["hello"], {"k": "v"})
        self.assertEqual(utterances, ["hello"])
        self.assertEqual(context, {"k": "v"})

    def test_metadata_wrong_shape_rejected(self):
        class Bad(MetadataTransformer):
            def transform(self, context=None):
                return ["not", "a", "dict"]

        service = self._empty(MetadataTransformersService)
        service.loaded_plugins["bad"] = Bad("bad", priority=10)
        context = service.transform({"k": "v"})
        self.assertEqual(context, {"k": "v"})

    def test_intent_wrong_shape_rejected(self):
        from ovos_plugin_manager.templates.pipeline import IntentHandlerMatch
        from ovos_plugin_manager.templates.transformers import IntentTransformer

        class Bad(IntentTransformer):
            def transform(self, intent):
                return {"not": "a match"}

        original = IntentHandlerMatch(match_type="skillA:foo", match_data={},
                                      skill_id="skillA", utterance="hello")
        service = self._empty(IntentTransformersService)
        service.loaded_plugins["bad"] = Bad("bad", priority=10)
        result = service.transform(original)
        self.assertEqual(result.match_type, "skillA:foo")

    # §3.4 -- intent dispatch-identity invariant
    def test_intent_identity_change_rejected(self):
        from ovos_plugin_manager.templates.pipeline import IntentHandlerMatch
        from ovos_plugin_manager.templates.transformers import IntentTransformer

        class Rogue(IntentTransformer):
            def transform(self, intent):
                return IntentHandlerMatch(match_type="skillB:bar", match_data={},
                                          skill_id="skillB", utterance="hello")

        original = IntentHandlerMatch(match_type="skillA:foo", match_data={},
                                      skill_id="skillA", utterance="hello")
        service = self._empty(IntentTransformersService)
        service.loaded_plugins["rogue"] = Rogue("rogue", priority=50)
        result = service.transform(original)
        self.assertEqual(result.match_type, "skillA:foo")
        self.assertEqual(result.skill_id, "skillA")

    def test_intent_skill_id_change_rejected(self):
        from ovos_plugin_manager.templates.pipeline import IntentHandlerMatch
        from ovos_plugin_manager.templates.transformers import IntentTransformer

        class Rogue(IntentTransformer):
            def transform(self, intent):
                return IntentHandlerMatch(match_type="skillA:foo", match_data={},
                                          skill_id="evil", utterance="hello")

        original = IntentHandlerMatch(match_type="skillA:foo", match_data={},
                                      skill_id="skillA", utterance="hello")
        service = self._empty(IntentTransformersService)
        service.loaded_plugins["rogue"] = Rogue("rogue", priority=50)
        result = service.transform(original)
        self.assertEqual(result.skill_id, "skillA")

    def test_intent_identity_preserving_change_accepted(self):
        """§3.4 permits enriching match_data while identity is unchanged."""
        from ovos_plugin_manager.templates.pipeline import IntentHandlerMatch
        from ovos_plugin_manager.templates.transformers import IntentTransformer

        class Enricher(IntentTransformer):
            def transform(self, intent):
                return IntentHandlerMatch(match_type=intent.match_type,
                                          match_data={"slot": "value"},
                                          skill_id=intent.skill_id,
                                          utterance=intent.utterance)

        original = IntentHandlerMatch(match_type="skillA:foo", match_data={},
                                      skill_id="skillA", utterance="hello")
        service = self._empty(IntentTransformersService)
        service.loaded_plugins["e"] = Enricher("e", priority=50)
        result = service.transform(original)
        self.assertEqual(result.match_data.get("slot"), "value")


class TestDebugEnabledGate(unittest.TestCase):
    """ovos-utils' LOG is a custom class: no isEnabledFor, no inheritance --
    LOG.level is the single source of truth for the hot-path debug gate."""

    def _gate(self, level):
        from ovos_plugin_manager.transformer_services import (LOG,
                                                              _debug_enabled)
        with patch.object(LOG, "level", level):
            return _debug_enabled()

    def test_debug_levels_enable(self):
        import logging
        self.assertTrue(self._gate("DEBUG"))
        self.assertTrue(self._gate(logging.DEBUG))
        self.assertTrue(self._gate(5))  # custom level below DEBUG

    def test_info_and_above_disable(self):
        import logging
        self.assertFalse(self._gate("INFO"))
        self.assertFalse(self._gate("WARNING"))
        self.assertFalse(self._gate(logging.ERROR))

    def test_notset_disables(self):
        """NOTSET defers to the stdlib root logger (WARNING by default),
        which drops debug records -- the gate must not treat 0 as enabled."""
        import logging
        self.assertFalse(self._gate("NOTSET"))
        self.assertFalse(self._gate(logging.NOTSET))

    def test_unknown_level_name_disables(self):
        self.assertFalse(self._gate("VERBOSE_NONSENSE"))


if __name__ == "__main__":
    unittest.main()
