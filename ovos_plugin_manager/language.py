from ovos_plugin_manager.utils import load_plugin, find_plugins, PluginTypes


def find_tx_plugins():
    return find_plugins(PluginTypes.TRANSLATE)


def load_tx_plugin(module_name):
    return load_plugin(module_name, PluginTypes.TRANSLATE)


def find_lang_detect_plugins():
    return find_plugins(PluginTypes.LANG_DETECT)


def load_lang_detect_plugin(module_name):
    return load_plugin(module_name, PluginTypes.LANG_DETECT)


