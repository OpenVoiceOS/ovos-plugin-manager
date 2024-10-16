from typing import List, Optional, Tuple, Callable, Union, Dict, Type

from ovos_bus_client.client import MessageBusClient
from ovos_config import Configuration
from ovos_utils.fakebus import FakeBus
from ovos_utils.log import log_deprecation

from ovos_plugin_manager.templates.pipeline import ConfidenceMatcherPipeline, PipelineStageMatcher, PipelinePlugin
from ovos_plugin_manager.utils import PluginTypes


def find_pipeline_plugins() -> Dict[str, Type[PipelinePlugin]]:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.PIPELINE)


def load_pipeline_plugin(module_name: str) -> Type[PipelinePlugin]:
    """
    Load and return an uninstantiated class for the specified pipeline plugin.

    @param module_name: The name of the plugin to load.
    @return: The uninstantiated plugin class.
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.PIPELINE)


class OVOSPipelineFactory:
    """
    Factory class for managing and creating pipeline plugins.
    """

    _CACHE = {}
    _MAP = {
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
    def get_installed_pipelines() -> List[str]:
        """
        Get a list of installed pipelines.

        @return: A list of installed pipeline identifiers.
        """
        pipelines = []
        for plug_id, clazz in find_pipeline_plugins().items():
            if issubclass(clazz, ConfidenceMatcherPipeline):
                pipelines.append(f"{plug_id}-low")
                pipelines.append(f"{plug_id}-medium")
                pipelines.append(f"{plug_id}-high")
            else:
                pipelines.append(plug_id)
        return pipelines

    @staticmethod
    def get_pipeline_classes(pipeline: Optional[List[str]] = None) -> List[Tuple[str, type(PipelinePlugin)]]:
        """
        Get a list of pipeline plugin classes based on the pipeline configuration.

        @param pipeline: A list of pipeline plugin identifiers to load.
        @return: A list of tuples containing the plugin identifier and the corresponding plugin class.
        """
        default_p = [
            "stop_high", "converse", "ocp_high", "padatious_high", "adapt_high",
            "ocp_medium", "fallback_high", "stop_medium", "adapt_medium",
            "padatious_medium", "adapt_low", "common_qa", "fallback_medium", "fallback_low"
        ]
        pipeline = pipeline or Configuration().get("intents", {}).get("pipeline",
                                                                      [OVOSPipelineFactory._MAP[p] for p in default_p])

        deprecated = [p for p in pipeline if p in OVOSPipelineFactory._MAP]
        if deprecated:
            log_deprecation(f"pipeline names have changed, "
                            f"please migrate: '{deprecated}' to '{[OVOSPipelineFactory._MAP[p] for p in deprecated]}'",
                            "1.0.0")

        valid_pipeline = [OVOSPipelineFactory._MAP.get(p, p) for p in pipeline]
        matchers = []
        for plug_id, clazz in find_pipeline_plugins().items():
            if issubclass(clazz, ConfidenceMatcherPipeline):
                if f"{plug_id}-low" in valid_pipeline:
                    matchers.append((f"{plug_id}-low", clazz))
                if f"{plug_id}-medium" in valid_pipeline:
                    matchers.append((f"{plug_id}-medium", clazz))
                if f"{plug_id}-high" in valid_pipeline:
                    matchers.append((f"{plug_id}-high", clazz))
            else:
                matchers.append((plug_id, clazz))

        return matchers

    @staticmethod
    def create(pipeline: Optional[List[str]] = None, use_cache: bool = True,
               bus: Optional[Union[MessageBusClient, FakeBus]] = None,
               skip_stage_matchers: bool = False) -> List[Tuple[str, Callable]]:
        """
        Factory method to create pipeline matchers.

        @param pipeline: A list of pipeline plugin identifiers to load.
        @param use_cache: Whether to cache the created matchers for reuse.
        @param bus: The message bus client to use for the pipelines.
        @param skip_stage_matchers: Whether to skip the stage matchers (i.e., matchers with side effects).
        @return: A list of tuples containing the pipeline identifier and the matcher callable.
        """
        matchers = []
        for pipe_id, clazz in OVOSPipelineFactory.get_pipeline_classes(pipeline):
            if use_cache and pipe_id in OVOSPipelineFactory._CACHE:
                m = OVOSPipelineFactory._CACHE[pipe_id]
            else:
                config = Configuration().get("intents", {}).get(pipe_id)
                m = clazz(bus, config)
                if use_cache:
                    OVOSPipelineFactory._CACHE[pipe_id] = m
            if isinstance(m, ConfidenceMatcherPipeline):
                if pipe_id.endswith("-high"):
                    matchers.append((pipe_id, m.match_high))
                elif pipe_id.endswith("-medium"):
                    matchers.append((pipe_id, m.match_medium))
                elif pipe_id.endswith("-low"):
                    matchers.append((pipe_id, m.match_low))
            elif isinstance(m, PipelineStageMatcher) and not skip_stage_matchers:
                matchers.append((pipe_id, m.match))
        return matchers

    @staticmethod
    def shutdown() -> None:
        """
        Shutdown all cached pipeline plugins by calling their shutdown methods if available.
        """
        for pipe in OVOSPipelineFactory._CACHE.values():
            if hasattr(pipe, "shutdown"):
                try:
                    pipe.shutdown()
                except:
                    continue
