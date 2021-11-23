from ovos_plugin_manager.utils import load_plugin, find_plugins, PluginTypes


def find_utterance_transformer_plugins():
    return find_plugins(PluginTypes.UTTERANCE_TRANSFORMER)


def load_utterance_transformer_plugin(module_name):
    """Wrapper function for loading text_transformer plugin.

    Arguments:
        (str) Mycroft text_transformer module name from config
    Returns:
        class: found text_transformer plugin class
    """
    return load_plugin(module_name, PluginTypes.UTTERANCE_TRANSFORMER)


def find_text_transformer_plugins():
    return find_utterance_transformer_plugins()


def load_text_transformer_plugin(module_name):
    return load_utterance_transformer_plugin(module_name)
