import re
from typing import Any, List, Optional, Tuple, Callable, Union, Dict, Type

from ovos_bus_client.client import MessageBusClient
from ovos_bus_client.message import Message
from ovos_config import Configuration
from ovos_utils.fakebus import FakeBus

from ovos_plugin_manager.templates.pipeline import ConfidenceMatcherPipeline, PipelinePlugin, IntentHandlerMatch
from ovos_plugin_manager.utils import PluginTypes, find_plugins, load_plugin

# Typing aliases
UtteranceList = List[str]
LangCode = str
PipelineID = str
PipelineMatcherID = str
PipelineConfig = List[PipelineMatcherID]
MatcherFunction = Callable[[UtteranceList, LangCode, Message], Optional[IntentHandlerMatch]]


def find_pipeline_plugins() -> Dict[PipelineID, Type[PipelinePlugin]]:
    """
    Discover and return all installed pipeline plugins.

    Returns:
        A dictionary mapping pipeline plugin IDs to their classes.
    """
    return find_plugins(PluginTypes.PIPELINE)


def load_pipeline_plugin(module_name: str) -> Type[PipelinePlugin]:
    """
    Load a pipeline plugin class by name.

    Args:
        module_name: The name of the plugin to load.

    Returns:
        The uninstantiated plugin class.
    """
    return load_plugin(module_name, PluginTypes.PIPELINE)


class OVOSPipelineFactory:
    """
    Factory class for discovering, loading, and managing OVOS pipeline plugins.
    """
    _CACHE: Dict[PipelineID, PipelinePlugin] = {}
    _MAP: Dict[str, str] = {
        "converse": "ovos-converse-pipeline-plugin",
        "common_qa": "ovos-common-query-pipeline-plugin",
        "fallback_high": "ovos-fallback-pipeline-plugin-high",
        "fallback_medium": "ovos-fallback-pipeline-plugin-medium",
        "fallback_low": "ovos-fallback-pipeline-plugin-low",
        "stop_high": "ovos-stop-pipeline-plugin-high",
        "stop_medium": "ovos-stop-pipeline-plugin-medium",
        "stop_low": "ovos-stop-pipeline-plugin-low",
        "adapt_high": "ovos-adapt-pipeline-plugin-high",
        "adapt_medium": "ovos-adapt-pipeline-plugin-medium",
        "adapt_low": "ovos-adapt-pipeline-plugin-low",
        "padacioso_high": "ovos-padacioso-pipeline-plugin-high",
        "padacioso_medium": "ovos-padacioso-pipeline-plugin-medium",
        "padacioso_low": "ovos-padacioso-pipeline-plugin-low",
        "padatious_high": "ovos-padatious-pipeline-plugin-high",
        "padatious_medium": "ovos-padatious-pipeline-plugin-medium",
        "padatious_low": "ovos-padatious-pipeline-plugin-low",
        "ocp_high": "ovos-ocp-pipeline-plugin-high",
        "ocp_medium": "ovos-ocp-pipeline-plugin-medium",
        "ocp_low": "ovos-ocp-pipeline-plugin-low",
        "ocp_legacy": "ovos-ocp-pipeline-plugin-legacy"
    }

    @staticmethod
    def get_installed_pipeline_ids() -> List[PipelineID]:
        """
        List all installed pipeline plugin identifiers.

        Returns:
            A list of installed pipeline plugin IDs.
        """
        return list(find_pipeline_plugins().keys())

    @staticmethod
    def get_installed_pipeline_matcher_ids() -> List[PipelineMatcherID]:
        """
        List all available pipeline matcher identifiers, including confidence levels.

        Returns:
            A list of matcher IDs.
        """
        pipelines: List[PipelineMatcherID] = []
        for plug_id, clazz in find_pipeline_plugins().items():
            if issubclass(clazz, ConfidenceMatcherPipeline):
                pipelines.extend([
                    f"{plug_id}-low",
                    f"{plug_id}-medium",
                    f"{plug_id}-high"
                ])
            else:
                pipelines.append(plug_id)
        return pipelines

    @classmethod
    def load_plugin(
            cls,
            pipe_id: PipelineID,
            use_cache: bool = True,
            bus: Optional[Union[MessageBusClient, FakeBus]] = None,
            config: Optional[Dict[str, Any]] = None
    ) -> PipelinePlugin:
        """
        Load (and optionally cache) a pipeline plugin instance.

        Args:
            pipe_id: The pipeline plugin ID.
            use_cache: Whether to use a cached instance.
            bus: Optional message bus client.
            config: Optional configuration for the plugin.

        Returns:
            An instance of the loaded pipeline plugin.
        """
        if use_cache and pipe_id in cls._CACHE:
            return cls._CACHE[pipe_id]

        config = config or Configuration().get("intents", {}).get(pipe_id, {})
        clazz = find_pipeline_plugins().get(pipe_id)
        if not clazz:
            raise ValueError(f"Unknown pipeline plugin: {pipe_id}")

        plugin_instance = clazz(bus, config)
        if use_cache:
            cls._CACHE[pipe_id] = plugin_instance
        return plugin_instance

    @classmethod
    def get_pipeline_matcher(
            cls,
            matcher_id: PipelineMatcherID,
            use_cache: bool = True,
            bus: Optional[Union[MessageBusClient, FakeBus]] = None
    ) -> MatcherFunction:
        """
        Retrieve a matcher function for a given pipeline matcher ID.

        Args:
            matcher_id: The configured matcher ID (e.g. `adapt_high`).
            use_cache: Whether to use cached plugin instances.
            bus: Optional message bus client.

        Returns:
            A callable matcher function.
        """
        matcher_id = cls._MAP.get(matcher_id, matcher_id)
        pipe_id = re.sub(r'-(high|medium|low)$', '', matcher_id)
        plugin = cls.load_plugin(pipe_id, use_cache, bus)

        if isinstance(plugin, ConfidenceMatcherPipeline):
            if matcher_id.endswith("-high"):
                return plugin.match_high
            if matcher_id.endswith("-medium"):
                return plugin.match_medium
            if matcher_id.endswith("-low"):
                return plugin.match_low
        return plugin.match

    @classmethod
    def create(
            cls,
            pipeline: Optional[PipelineConfig] = None,
            use_cache: bool = True,
            bus: Optional[Union[MessageBusClient, FakeBus]] = None
    ) -> List[Tuple[PipelineMatcherID, MatcherFunction]]:
        """
        Create matcher functions from a list of pipeline matcher IDs.

        Args:
            pipeline: A list of matcher IDs.
            use_cache: Whether to use cached plugin instances.
            bus: Optional message bus client.

        Returns:
            A list of (matcher ID, matcher function) tuples.
        """
        return [(matcher_id, cls.get_pipeline_matcher(matcher_id, use_cache, bus))
                for matcher_id in (pipeline or [])]

    @staticmethod
    def shutdown() -> None:
        """
        Call shutdown on all cached plugin instances, if they define it.
        """
        for plugin in OVOSPipelineFactory._CACHE.values():
            shutdown_fn = getattr(plugin, "shutdown", None)
            if callable(shutdown_fn):
                try:
                    shutdown_fn()
                except Exception:
                    continue
