from ovos_plugin_manager.utils import find_plugins, PluginTypes


def find_intent_plugins():
    return find_plugins(PluginTypes.INTENT)
