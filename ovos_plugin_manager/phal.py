from ovos_plugin_manager.utils import load_plugin, find_plugins, PluginTypes, PluginConfigTypes
from ovos_plugin_manager.templates.phal import PHALPlugin


def find_phal_plugins():
    return find_plugins(PluginTypes.PHAL)


def get_phal_config_examples(module_name):
    return load_plugin(module_name + ".config",
                       PluginConfigTypes.PHAL)

