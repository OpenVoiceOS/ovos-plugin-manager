from typing import Type, Dict, Any

from ovos_plugin_manager.templates.agent_tools import ToolBox
from ovos_plugin_manager.utils import PluginTypes


def find_persona_plugins() -> Dict[str, Dict[str, Any]]:
    """
    Find all installed persona definitions
    @return: dict plugin names to entrypoints (persona entrypoint are just dicts)
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.PERSONA)


def find_toolbox_plugins() -> Dict[str, Type[ToolBox]]:
    """
    Find all installed Toolbox plugins
    @return: dict toolbox_id to entrypoints (ToolBox)
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.PERSONA_TOOL)
