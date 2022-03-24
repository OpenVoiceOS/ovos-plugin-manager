from ovos_plugin_manager.utils import load_plugin, find_plugins, PluginTypes


def find_intent_engine_plugins():
    return find_plugins(PluginTypes.INTENT_ENGINE)


def load_intent_engine_plugin(module_name):
    """Wrapper function for loading text_transformer plugin.

    Arguments:
        (str) Mycroft text_transformer module name from config
    Returns:
        class: found text_transformer plugin class
    """
    return load_plugin(module_name, PluginTypes.INTENT_ENGINE)

