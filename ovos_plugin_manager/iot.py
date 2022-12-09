from ovos_plugin_manager.utils import load_plugin, find_plugins, PluginTypes, PluginConfigTypes
from ovos_config import Configuration
from ovos_plugin_manager.templates.iot import IOTPlugin


def find_iot_plugins():
    return find_plugins(PluginTypes.IOT)


def load_iot_plugin(module_name):
    """Wrapper function for loading iot plugin.

    Arguments:
        module_name (str): iot module name from config
    Returns:
        class: IOTPlugin plugin class
    """
    return load_plugin(module_name, PluginTypes.IOT)


def get_iot_config(config=None):
    from ovos_plugin_manager.utils.config import get_plugin_config
    config = config or Configuration()
    return get_plugin_config(config, "iot")


