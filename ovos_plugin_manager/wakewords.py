from ovos_plugin_manager.utils import load_plugin, find_plugins, PluginTypes


def find_wake_word_plugins():
    return find_plugins(PluginTypes.WAKEWORD)


def load_wake_word_plugin(module_name):
    """Wrapper function for loading wake word plugin.

    Arguments:
        (str) Mycroft wake word module name from config
    """
    return load_plugin(module_name, PluginTypes.WAKEWORD)
