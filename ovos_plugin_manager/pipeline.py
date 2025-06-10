from typing import Any, List, Optional, Union, Dict, Type

from ovos_bus_client.client import MessageBusClient
from ovos_config import Configuration
from ovos_utils.fakebus import FakeBus

from ovos_plugin_manager.templates.pipeline import ConfidenceMatcherPipeline, PipelinePlugin
from ovos_plugin_manager.utils import PluginTypes, find_plugins, load_plugin

# Typing aliases
PipelineID = str
PipelineMatcherID = str


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
            bus: Optional[Union[MessageBusClient, FakeBus]] = None,
            config: Optional[Dict[str, Any]] = None
    ) -> PipelinePlugin:
        """
        Load a pipeline plugin instance.

        Args:
            pipe_id: The pipeline plugin ID.
            bus: Optional message bus client.
            config: Optional configuration for the plugin.

        Returns:
            An instance of the loaded pipeline plugin.
        """
        config = config or Configuration().get("intents", {}).get(pipe_id, {})
        clazz = find_pipeline_plugins().get(pipe_id)
        if not clazz:
            raise ValueError(f"Unknown pipeline plugin: {pipe_id}")
        plugin_instance = clazz(bus, config)
        return plugin_instance
