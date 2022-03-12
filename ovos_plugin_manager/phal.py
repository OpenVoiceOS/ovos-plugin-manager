from ovos_plugin_manager.utils import find_plugins, PluginTypes
from ovos_plugin_manager.templates.phal import PHALPlugin

def find_phal_plugins():
    return find_plugins(PluginTypes.PHAL)

