from ovos_plugin_manager.utils import normalize_lang, load_plugin, find_plugins, PluginTypes, PluginConfigTypes


def find_utterance_transformer_plugins():
    return find_plugins(PluginTypes.UTTERANCE_TRANSFORMER)


def get_utterance_transformer_configs():
    from ovos_plugin_manager.utils import load_configs_for_plugin_type
    return load_configs_for_plugin_type(PluginTypes.UTTERANCE_TRANSFORMER)


def get_utterance_transformer_module_configs(module_name):
    # utterance plugins return {lang: [list of config dicts]}
    from ovos_plugin_manager.utils import load_plugin_configs
    return load_plugin_configs(module_name,
                               PluginConfigTypes.UTTERANCE_TRANSFORMER, True)


def get_utterance_transformer_lang_configs(lang, include_dialects=False):
    from ovos_plugin_manager.utils import get_plugin_language_configs
    return get_plugin_language_configs(PluginTypes.UTTERANCE_TRANSFORMER, lang,
                                       include_dialects)


def get_utterance_transformer_supported_langs():
    from ovos_plugin_manager.utils import get_plugin_supported_languages
    return get_plugin_supported_languages(PluginTypes.UTTERANCE_TRANSFORMER)


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
