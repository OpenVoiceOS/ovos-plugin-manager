"""Canonical runner services for transformer plugin pipelines.

These services load, order and chain transformer plugins of each type
(utterance, metadata, intent, dialog, tts, audio). They are the single
shared implementation consumed by ovos-core, ovos-audio,
ovos-dinkum-listener, hivemind and the ovos tts/stt servers.

Loading is config-gated and opt-in: a plugin is only loaded if its name
appears in the service's config section and its entry does not set
``"active": false``.

Ordering follows OVOS-TRANSFORM §4: lower ``priority`` number runs
first (``sort_ascending=True``, the default). An explicit deployer
order — an ``"order"`` list of plugin names in the config section —
wins over priorities; loaded plugins absent from that list are not
run. Consumers that relied on the legacy descending traversal
("priority 1 runs last and wins") can pass ``sort_ascending=False``;
this escape hatch is deprecated and will be removed.

Cancellation follows OVOS-TRANSFORM §8.1: a plugin signals by
returning both ``"canceled": true`` and ``"cancel_reason"`` in its
context; the runner stamps ``"cancel_by"`` and stops the chain. An
incomplete pair is a shape violation: logged, stripped, chain
continues. Terminal bus events (§8.2) are the consumer's concern.
"""
import inspect
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

from ovos_config import Configuration
from ovos_utils.json_helper import merge_dict
from ovos_utils.log import LOG

from ovos_plugin_manager.audio_transformers import find_audio_transformer_plugins
from ovos_plugin_manager.dialog_transformers import find_dialog_transformer_plugins
from ovos_plugin_manager.intent_transformers import find_intent_transformer_plugins
from ovos_plugin_manager.metadata_transformers import find_metadata_transformer_plugins
from ovos_plugin_manager.templates.pipeline import IntentHandlerMatch
from ovos_plugin_manager.text_transformers import find_utterance_transformer_plugins
from ovos_plugin_manager.tts_transformers import find_tts_transformer_plugins


def _debug_enabled() -> bool:
    """Return whether the shared OVOS logger will emit debug records.

    ``LOG.debug`` resolves its caller with ``inspect.stack`` before the
    standard logger rejects a disabled record. Transformer runners are hot
    paths, so avoid that comparatively expensive work at INFO and above.

    ``LOG`` is ovos-utils' custom logger class: it has no ``isEnabledFor``
    and no level inheritance -- ``LOG.level`` (stdlib name string or int) is
    the single source of truth. ``NOTSET`` makes the stdlib logger underneath
    defer to the root logger (WARNING by default), which drops debug records,
    so treat it as debug-disabled rather than letting it fall through the
    ``<=`` comparison as 0.
    """
    level = LOG.level
    if isinstance(level, str):
        resolved = logging.getLevelName(level.upper())
        level = resolved if isinstance(resolved, int) else logging.INFO
    return logging.NOTSET < level <= logging.DEBUG


def _stamp_provenance(context: dict, key: str, transformer_id: str) -> None:
    """Stamp transformer self-identification per OVOS-TRANSFORM-1 §1.3.

    On every touch a transformer performs, its own ``transformer_id`` MUST be
    the last element of the corresponding ``<type>_transformer_ids`` list. The
    orchestrator enforces this by appending the id once per execution window,
    creating the list if absent.
    """
    ids = context.get(key)
    if not isinstance(ids, list):
        ids = []
    context[key] = ids + [transformer_id]


class TransformersService:
    """Base class for transformer pipeline runners.

    Args:
        bus: optional messagebus client, bound to plugins that support it
        config: either the full core configuration (the service extracts
            its own section) or the section mapping itself
            (``{plugin_name: plugin_config}``). When omitted, the section
            is read from ``Configuration()``.
        sort_ascending: OVOS-TRANSFORM-1 §4 ordering (lower priority
            number runs first). Set False for legacy descending order.
    """
    transformer_type: str = "generic"
    config_section: Optional[str] = None
    plugin_finder: Callable[[], Dict[str, Any]] = None

    def __init__(self, bus=None, config: Optional[dict] = None,
                 sort_ascending: bool = True):
        self.bus = bus
        self.loaded_plugins = {}
        self.has_loaded = False
        self.sort_ascending = sort_ascending
        self._sorted_plugins = None
        self.config = self._resolve_section(config)
        self.load_plugins()

    @classmethod
    def _resolve_section(cls, config: Optional[dict]) -> dict:
        """Accept either a full core config or the section mapping itself."""
        if config is None:
            config = Configuration()
        if cls.config_section and cls.config_section in config:
            return dict(config.get(cls.config_section) or {})
        return dict(config)

    @classmethod
    def find_plugins(cls):
        return cls.plugin_finder().items()

    @classmethod
    def get_available_plugins(cls) -> List[str]:
        return list(cls.plugin_finder().keys())

    def load_plugins(self) -> None:
        # reserved config keys that are not plugin entries
        enabled = set(self.config.keys()) - {"order", "blacklisted_skills"}
        explicit_order = self.config.get("order")
        if isinstance(explicit_order, list):
            # plugins in the explicit chain are enabled even without
            # their own config entry
            enabled |= set(explicit_order)
        for plug_name, plug in self.find_plugins():
            if plug_name not in enabled:
                continue
            plug_config = self.config.get(plug_name) or {}
            if isinstance(plug_config, dict) and not plug_config.get("active", True):
                continue
            try:
                if self._accepts_config_kwarg(plug):
                    plugin = plug(config=plug_config)
                else:
                    # plugin does not accept a config kwarg, it self-reads
                    # its section from Configuration()
                    plugin = plug()
                if self.bus:
                    self._bind_plugin(plugin)
                self.loaded_plugins[plug_name] = plugin
                LOG.info(f"loaded {self.transformer_type} transformer plugin: {plug_name}")
            except Exception:
                LOG.exception(f"Failed to load {self.transformer_type} "
                              f"transformer plugin: {plug_name}")
        self._sorted_plugins = None
        self.has_loaded = True

    @staticmethod
    def _accepts_config_kwarg(plug) -> bool:
        """Check whether a plugin constructor takes a ``config`` kwarg.

        Signature inspection instead of try/except so a TypeError raised
        inside the constructor propagates instead of being masked by a
        silent no-config retry.
        """
        try:
            params = inspect.signature(plug).parameters.values()
        except (TypeError, ValueError):
            return True
        return any(p.name == "config" or p.kind == inspect.Parameter.VAR_KEYWORD
                   for p in params)

    def _bind_plugin(self, plugin) -> None:
        try:
            plugin.bind(self.bus)
        except Exception:
            LOG.exception(f"Failed to bind bus to {self.transformer_type} "
                          f"transformer plugin: {getattr(plugin, 'name', plugin)}")

    def set_bus(self, bus) -> None:
        """Attach (or replace) the messagebus and bind all loaded plugins."""
        self.bus = bus
        for plugin in self.loaded_plugins.values():
            self._bind_plugin(plugin)

    @property
    def plugins(self) -> list:
        """Loaded plugins in execution order.

        An explicit deployer order (an ``"order"`` list of plugin names in
        the config section) wins over priorities per OVOS-TRANSFORM §4;
        loaded plugins absent from the list are not run.

        Otherwise, with ``sort_ascending=True`` (OVOS-TRANSFORM §4) a
        plugin with ``priority=1`` runs first; later plugins see and may
        override its output. With ``sort_ascending=False`` (deprecated
        legacy behavior) a plugin with ``priority=1`` runs last and has
        the final say.
        """
        if self._sorted_plugins is None:
            explicit_order = self.config.get("order")
            if isinstance(explicit_order, list):
                self._sorted_plugins = [self.loaded_plugins[name]
                                        for name in explicit_order
                                        if name in self.loaded_plugins]
            else:
                self._sorted_plugins = sorted(self.loaded_plugins.values(),
                                              key=lambda k: k.priority,
                                              reverse=not self.sort_ascending)
        return self._sorted_plugins

    def _check_cancellation(self, data: dict, module) -> bool:
        """Validate a §8.1 cancellation signal in a plugin's returned context.

        Returns True when a valid ``canceled``/``cancel_reason`` pair is
        present, stamping ``cancel_by`` from the emitting plugin (never
        from a value the plugin set itself). An incomplete pair is a
        shape violation: logged, stripped from ``data`` in place, and the
        chain proceeds as if the plugin returned its input unchanged.
        """
        if not isinstance(data, dict):
            return False
        if data.get("canceled") is True:
            if not data.get("cancel_reason"):
                # legacy plugins (pre OVOS-TRANSFORM §8.1) signal with
                # "canceled" alone — honor the cancellation and default the
                # reason to the spec's universal fallback
                LOG.warning(f"{module.name} signalled 'canceled' without a "
                            "'cancel_reason' (required by OVOS-TRANSFORM "
                            "§8.1), defaulting to 'other'")
                data["cancel_reason"] = "other"
            data["cancel_by"] = module.name
            LOG.info(f"{self.transformer_type} chain canceled by "
                     f"{module.name}: {data['cancel_reason']}")
            return True
        if "canceled" in data or "cancel_reason" in data:
            LOG.warning(f"{module.name} signalled an incomplete cancellation "
                        "pair (OVOS-TRANSFORM §8.1 requires both 'canceled' "
                        "and 'cancel_reason'), ignoring it")
            data.pop("canceled", None)
            data.pop("cancel_reason", None)
        # cancel_by is orchestrator-stamped only — never accept a
        # plugin-supplied value outside a valid cancellation signal
        data.pop("cancel_by", None)
        return False

    def shutdown(self) -> None:
        # iterate everything loaded, not self.plugins — an explicit "order"
        # list excludes unlisted plugins from execution but they still need
        # to be shut down
        for module in self.loaded_plugins.values():
            try:
                if hasattr(module, "shutdown"):
                    module.shutdown()
                else:
                    module.default_shutdown()
            except Exception as e:
                LOG.warning(f"Error shutting down {getattr(module, 'name', module)}: {e}")


class UtteranceTransformersService(TransformersService):
    """Transforms utterances after STT and before intent matching."""
    transformer_type = "utterance"
    config_section = "utterance_transformers"
    plugin_finder = staticmethod(find_utterance_transformer_plugins)

    def transform(self, utterances: List[str],
                  context: Optional[dict] = None) -> Tuple[List[str], dict]:
        if context is None:
            context = {}
        for module in self.plugins:
            try:
                result = module.transform(utterances, context)
                # OVOS-TRANSFORM-1 §7: a wrong-shape return is treated the
                # same as a raised exception -> log and proceed with the
                # prior transformer's output unchanged.
                if not (isinstance(result, (tuple, list)) and len(result) == 2):
                    LOG.warning(f"{module.name} returned wrong shape "
                                f"(expected (utterances, context)): {type(result)}; "
                                f"ignoring its output")
                    continue
                new_utterances, data = result
                if not isinstance(data, dict):
                    LOG.warning(f"{module.name} returned non-dict context; "
                                f"ignoring its output")
                    continue
                if _debug_enabled():
                    # Do not leak TTS/STT credentials from the session.
                    safe = {k: v for k, v in data.items() if k != "session"}
                    LOG.debug("%s: %s", module.name, safe)
                canceled = self._check_cancellation(data, module)
                # In-place transformers commonly return the exact context
                # object they received. Merging an object into itself is a
                # no-op for flat data and recursively walks identical nested
                # mappings until RecursionError. Preserve the same object and
                # only merge when a plugin returned a distinct delta/result.
                if data is not context:
                    context = merge_dict(context, data)
                utterances = new_utterances
                # OVOS-TRANSFORM-1 §1.3: stamp the transformer's self-identification
                _stamp_provenance(context, "utterance_transformer_ids", module.name)
                if canceled:
                    break
            except Exception as e:
                LOG.warning(f"{module.name} transform exception: {e}")
        return utterances, context


class MetadataTransformersService(TransformersService):
    """Transforms message context after utterance transformers, before intent matching."""
    transformer_type = "metadata"
    config_section = "metadata_transformers"
    plugin_finder = staticmethod(find_metadata_transformer_plugins)

    def transform(self, context: Optional[dict] = None) -> dict:
        if context is None:
            context = {}
        for module in self.plugins:
            try:
                data = module.transform(context)
                # OVOS-TRANSFORM-1 §7: reject wrong-shape returns; a metadata
                # transformer's only output is a Message.context dict (§3.3).
                if not isinstance(data, dict):
                    LOG.warning(f"{module.name} returned wrong shape "
                                f"(expected context dict): {type(data)}; "
                                f"ignoring its output")
                    continue
                if _debug_enabled():
                    # Do not leak TTS/STT credentials from the session.
                    safe = {k: v for k, v in data.items() if k != "session"}
                    LOG.debug("%s: %s", module.name, safe)
                canceled = self._check_cancellation(data, module)
                if data is not context:
                    context = merge_dict(context, data)
                # OVOS-TRANSFORM-1 §1.3: stamp the transformer's self-identification
                _stamp_provenance(context, "metadata_transformer_ids", module.name)
                if canceled:
                    break
            except Exception as e:
                LOG.warning(f"{module.name} transform exception: {e}")
        return context


class IntentTransformersService(TransformersService):
    """Transforms the selected intent match before its handler is triggered."""
    transformer_type = "intent"
    config_section = "intent_transformers"
    plugin_finder = staticmethod(find_intent_transformer_plugins)

    def transform(self, intent: IntentHandlerMatch) -> IntentHandlerMatch:
        for module in self.plugins:
            try:
                result = module.transform(intent)
                # OVOS-TRANSFORM-1 §7 / §3.4: reject wrong-shape returns.
                if not isinstance(result, IntentHandlerMatch):
                    LOG.warning(f"{module.name} returned wrong shape "
                                f"(expected IntentHandlerMatch): {type(result)}; "
                                f"ignoring its output")
                    continue
                # OVOS-TRANSFORM-1 §3.4 identity invariant: an intent
                # transformer MUST NOT change the dispatch identity
                # (skill_id / match_type). If it does, discard the output
                # and keep the prior Match — this is the orchestrator-side
                # safety net for a MUST NOT the transformer already owes.
                if (result.match_type != intent.match_type or
                        result.skill_id != intent.skill_id):
                    LOG.warning(f"{module.name} attempted to change intent "
                                f"identity (match_type/skill_id); ignoring its "
                                f"output per OVOS-TRANSFORM-1 §3.4")
                    continue
                intent = result
                LOG.debug("%s: %s", module.name, intent)
            except Exception as e:
                LOG.warning(f"{module.name} transform exception: {e}")
        return intent


class DialogTransformersService(TransformersService):
    """Transforms dialog text before it is sent to TTS."""
    transformer_type = "dialog"
    config_section = "dialog_transformers"
    plugin_finder = staticmethod(find_dialog_transformer_plugins)

    @property
    def blacklisted_skills(self) -> List[str]:
        # dialog should NEVER be rewritten if it comes from these skills
        return self.config.get("blacklisted_skills",
                               ["skill-ovos-icanhazdadjokes.openvoiceos"]  # blacklist jokes by default
                               )

    def transform(self, dialog: str, context: Optional[dict] = None,
                  sess=None) -> Tuple[str, dict]:
        """
        @param dialog: str to be spoken
        @return: transformed dialog to be sent to TTS
        """
        context = context or {}
        skill_id = context.get("skill_id")
        if skill_id and skill_id in self.blacklisted_skills:
            LOG.debug(f"dialog from blacklisted skill {skill_id} "
                      "not transformed")
            return dialog, context
        for module in self.plugins:
            try:
                dialog, context = module.transform(dialog, context=context)
                LOG.debug("%s: %s", module.name, dialog)
                if self._check_cancellation(context, module):
                    break
            except Exception:
                LOG.exception(f"{module.name} transform exception")
        return dialog, context


class TTSTransformersService(TransformersService):
    """Transforms synthesized audio files after TTS and before playback."""
    transformer_type = "tts"
    config_section = "tts_transformers"
    plugin_finder = staticmethod(find_tts_transformer_plugins)

    def transform(self, wav_file: str, context: Optional[dict] = None,
                  sess=None) -> Tuple[str, dict]:
        """
        @param wav_file: str path for the TTS wav file
        @return: path to transformed wav file
        """
        context = context or {}
        for module in self.plugins:
            try:
                wav_file, context = module.transform(wav_file, context=context)
                LOG.debug("%s: %s", module.name, wav_file)
                if self._check_cancellation(context, module):
                    break
            except Exception:
                LOG.exception(f"{module.name} transform exception")
        return wav_file, context


class AudioTransformersService(TransformersService):
    """Transforms raw audio before the STT stage."""
    transformer_type = "audio"
    config_section = "audio_transformers"
    plugin_finder = staticmethod(find_audio_transformer_plugins)

    def __init__(self, bus=None, config: Optional[dict] = None,
                 sort_ascending: bool = True,
                 default_context: Optional[dict] = None):
        self.default_context = default_context or {}
        super().__init__(bus=bus, config=config, sort_ascending=sort_ascending)

    def feed_audio(self, chunk: bytes) -> None:
        """Feed a chunk of untagged (not speech) audio to all loaded plugins."""
        for module in self.plugins:
            try:
                module.feed_audio_chunk(chunk)
            except Exception:
                LOG.exception(f"{module.name} failed to consume audio chunk")

    def feed_hotword(self, chunk: bytes) -> None:
        """Feed a chunk of hotword audio to all loaded plugins."""
        for module in self.plugins:
            try:
                module.feed_hotword_chunk(chunk)
            except Exception:
                LOG.exception(f"{module.name} failed to consume hotword chunk")

    def feed_speech(self, chunk: bytes) -> None:
        """Feed a chunk of speech audio to all loaded plugins."""
        for module in self.plugins:
            try:
                module.feed_speech_chunk(chunk)
            except Exception:
                LOG.exception(f"{module.name} failed to consume speech chunk")

    def transform(self, chunk: bytes,
                  context: Optional[dict] = None) -> Tuple[bytes, dict]:
        """
        Get transformed audio and context for the preceding audio
        @param chunk: bytes of audio data
        @return: transformed audio data, dict context
        """
        # start from the defaults, caller-provided keys override them
        context = {**self.default_context, **(context or {})}
        for module in self.plugins:
            try:
                chunk = module.feed_speech_utterance(chunk)
                chunk, data = module.transform(chunk)
                LOG.debug("%s: %s", module.name, data)
                canceled = self._check_cancellation(data, module)
                context = merge_dict(context, data)
                if canceled:
                    break
            except Exception:
                LOG.exception(f"{module.name} transform exception")
        return chunk, context
