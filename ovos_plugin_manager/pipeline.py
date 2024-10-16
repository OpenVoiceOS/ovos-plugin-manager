from typing import List, Optional, Tuple, Callable, Union

from ovos_bus_client.client import MessageBusClient
from ovos_utils.fakebus import FakeBus
from ovos_config import Configuration
from ovos_plugin_manager.templates.pipeline import ConfidenceMatcherPipeline, PipelineStageMatcher, PipelinePlugin
from ovos_plugin_manager.utils import PluginTypes


def find_pipeline_plugins() -> dict:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.PIPELINE)


def load_pipeline_plugin(module_name: str) -> type(PipelinePlugin):
    """
    Get an uninstantiated class for the requested module_name
    @param module_name: Plugin entrypoint name to load
    @return: Uninstantiated class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.PIPELINE)


class OVOSPipelineFactory:
    _CACHE = {}

    @staticmethod
    def get_installed_pipelines() -> List[str]:
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

        default_p = [
            "stop_high",
            "converse",
            "ocp_high",
            "padatious_high",
            "adapt_high",
            "ocp_medium",
            "fallback_high",
            "stop_medium",
            "adapt_medium",
            "padatious_medium",
            "adapt_low",
            "common_qa",
            "fallback_medium",
            "fallback_low"
        ]
        pipeline = pipeline or Configuration().get("intents", {}).get("pipeline", default_p)

        # TODO - deprecate around ovos-core 2.0.0
        MAP = {
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
            "ocp_low": "ovos-ocp-pipeline-plugin-low"
        }
        valid_pipeline = [MAP.get(p, p) for p in pipeline]
        matchers = []
        for plug_id, clazz in find_pipeline_plugins().items():
            if issubclass(clazz, ConfidenceMatcherPipeline):
                if f"{plug_id}-low" in valid_pipeline:
                    matchers.append((f"{plug_id}-low", clazz))
                if f"{plug_id}-medium" in valid_pipeline:
                    matchers.append((f"{plug_id}-medium", clazz))
                if f"{plug_id}-high" in valid_pipeline:
                    matchers.append((plug_id, clazz))
            else:
                matchers.append((plug_id, clazz))

        return matchers

    @staticmethod
    def create(pipeline: Optional[List[str]] = None, use_cache: bool = True,
               bus: Optional[Union[MessageBusClient, FakeBus]] = None) -> List[Tuple[str, Callable]]:
        """Factory method to create pipeline matchers"""
        default_p = [
            "stop_high",
            "converse",
            "ocp_high",
            "padatious_high",
            "adapt_high",
            "ocp_medium",
            "fallback_high",
            "stop_medium",
            "adapt_medium",
            "padatious_medium",
            "adapt_low",
            "common_qa",
            "fallback_medium",
            "fallback_low"
        ]
        pipeline = pipeline or Configuration().get("intents", {}).get("pipeline", default_p)

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
            elif isinstance(m, PipelineStageMatcher):
                matchers.append((pipe_id, m.match))
        return matchers

    @staticmethod
    def shutdown():
        for pipe in OVOSPipelineFactory._CACHE.values():
            if hasattr(pipe, "shutdown"):
                try:
                    pipe.shutdown()
                except:
                    continue


if __name__ == "__main__":
    matchers = OVOSPipelineFactory.create()
    print(matchers)
