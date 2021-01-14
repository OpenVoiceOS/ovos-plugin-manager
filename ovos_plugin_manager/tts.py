from ovos_plugin_manager.utils import load_plugin, find_plugins, PluginTypes


def find_tts_plugins():
    return find_plugins(PluginTypes.TTS)


def load_tts_plugin(module_name):
    """Wrapper function for loading tts plugin.

    Arguments:
        (str) Mycroft tts module name from config
    Returns:
        class: found tts plugin class
    """
    return load_plugin(module_name, PluginTypes.TTS)
