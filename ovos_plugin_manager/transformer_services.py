"""Canonical runner services for transformer plugin pipelines.

These services load, order and chain transformer plugins of each type
(utterance, metadata, intent, dialog, tts, audio). They are the single
shared implementation consumed by ovos-core, ovos-audio,
ovos-dinkum-listener, hivemind and the ovos tts/stt servers.

Loading is config-gated and opt-in: a plugin is only loaded if its name
appears in the service's config section and its entry does not set
``"active": false``.

Ordering follows OVOS-TRANSFORM-1 §4: lower ``priority`` number runs
first (``sort_ascending=True``, the default). Consumers that relied on
the legacy descending traversal ("priority 1 runs last and wins") can
pass ``sort_ascending=False``.
"""
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
        for plug_name, plug in self.find_plugins():
            if plug_name not in self.config:
                continue
            plug_config = self.config[plug_name] or {}
            if isinstance(plug_config, dict) and not plug_config.get("active", True):
                continue
            try:
                try:
                    plugin = plug(config=plug_config)
                except TypeError:
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

        With ``sort_ascending=True`` (OVOS-TRANSFORM-1 §4) a plugin with
        ``priority=1`` runs first; later plugins see and may override its
        output. With ``sort_ascending=False`` (legacy) a plugin with
        ``priority=1`` runs last and has the final say.
        """
        if self._sorted_plugins is None:
            self._sorted_plugins = sorted(self.loaded_plugins.values(),
                                          key=lambda k: k.priority,
                                          reverse=not self.sort_ascending)
        return self._sorted_plugins

    def shutdown(self) -> None:
        for module in self.plugins:
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
        context = context or {}
        for module in self.plugins:
            try:
                utterances, data = module.transform(utterances, context)
                _safe = {k: v for k, v in data.items() if k != "session"}  # no leaking TTS/STT creds in logs
                LOG.debug(f"{module.name}: {_safe}")
                context = merge_dict(context, data)
            except Exception as e:
                LOG.warning(f"{module.name} transform exception: {e}")
        return utterances, context


class MetadataTransformersService(TransformersService):
    """Transforms message context after utterance transformers, before intent matching."""
    transformer_type = "metadata"
    config_section = "metadata_transformers"
    plugin_finder = staticmethod(find_metadata_transformer_plugins)

    def transform(self, context: Optional[dict] = None) -> dict:
        context = context or {}
        for module in self.plugins:
            try:
                data = module.transform(context)
                _safe = {k: v for k, v in data.items() if k != "session"}  # no leaking TTS/STT creds in logs
                LOG.debug(f"{module.name}: {_safe}")
                context = merge_dict(context, data)
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
                intent = module.transform(intent)
                LOG.debug(f"{module.name}: {intent}")
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
        for module in self.plugins:
            try:
                dialog, context = module.transform(dialog, context=context)
                LOG.debug(f"{module.name}: {dialog}")
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
                LOG.debug(f"{module.name}: {wav_file}")
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

    @classmethod
    def _resolve_section(cls, config: Optional[dict]) -> dict:
        if config is None:
            config = Configuration()
        # legacy location: nested under the "listener" section
        listener = config.get("listener") or {}
        if cls.config_section in listener:
            if cls.config_section not in config:
                LOG.warning("'listener.audio_transformers' is deprecated, "
                            "move the section to top-level 'audio_transformers'")
                return dict(listener.get(cls.config_section) or {})
            # both defined: top-level wins, merged over legacy
            return merge_dict(dict(listener.get(cls.config_section) or {}),
                              dict(config.get(cls.config_section) or {}))
        return super()._resolve_section(config)

    def feed_audio(self, chunk: bytes) -> None:
        """Feed a chunk of untagged (not speech) audio to all loaded plugins."""
        for module in self.plugins:
            module.feed_audio_chunk(chunk)

    def feed_hotword(self, chunk: bytes) -> None:
        """Feed a chunk of hotword audio to all loaded plugins."""
        for module in self.plugins:
            module.feed_hotword_chunk(chunk)

    def feed_speech(self, chunk: bytes) -> None:
        """Feed a chunk of speech audio to all loaded plugins."""
        try:
            for module in self.plugins:
                module.feed_speech_chunk(chunk)
        except Exception:
            LOG.exception("error feeding speech chunk to audio transformers")

    def transform(self, chunk: bytes,
                  context: Optional[dict] = None) -> Tuple[bytes, dict]:
        """
        Get transformed audio and context for the preceding audio
        @param chunk: bytes of audio data
        @return: transformed audio data, dict context
        """
        context = context or dict(self.default_context)
        for module in self.plugins:
            try:
                chunk = module.feed_speech_utterance(chunk)
                chunk, data = module.transform(chunk)
                LOG.debug(f"{module.name}: {data}")
                context = merge_dict(context, data)
            except Exception:
                LOG.exception(f"{module.name} transform exception")
        return chunk, context
