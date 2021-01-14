from ovos_plugin_manager.utils import load_plugin, find_plugins, PluginTypes


def find_stt_plugins():
    return find_plugins(PluginTypes.STT)


def load_stt_plugin(module_name):
    """Wrapper function for loading stt plugin.

    Arguments:
        module_name (str): Mycroft stt module name from config
    Returns:
        class: STT plugin class
    """
    return load_plugin(module_name, PluginTypes.STT)
