from typing import Dict, Type
from ovos_plugin_manager.templates.agents import AgentContextManager, MultimodalAdapter
from ovos_plugin_manager.utils import PluginTypes


def find_memory_plugins() -> Dict[str, Type[AgentContextManager]]:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.AGENT_MEMORY)


def load_memory_plugin(module_name: str) -> Type[AgentContextManager]:
    """
    Get an uninstantiated class for the requested module_name
    @param module_name: Plugin entrypoint name to load
    @return: Uninstantiated class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.AGENT_MEMORY)


def find_multimodal_adapter_plugins() -> Dict[str, Type[MultimodalAdapter]]:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.AGENT_MULTIMODAL_ADAPTER)


def load_multimodal_adapter_plugin(module_name: str) -> Type[MultimodalAdapter]:
    """
    Get an uninstantiated class for the requested module_name
    @param module_name: Plugin entrypoint name to load
    @return: Uninstantiated class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.AGENT_MULTIMODAL_ADAPTER)
