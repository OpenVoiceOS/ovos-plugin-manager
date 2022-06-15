from ovos_plugin_manager.utils import load_plugin, find_plugins, PluginTypes


def find_metadata_transformer_plugins():
    return find_plugins(PluginTypes.METADATA_TRANSFORMER)


def load_metadata_transformer_plugin(module_name):
    """Wrapper function for loading metadata_transformer plugin.

    Arguments:
        (str) Mycroft metadata_transformer module name from config
    Returns:
        class: found metadata_transformer plugin class
    """
    return load_plugin(module_name, PluginTypes.METADATA_TRANSFORMER)