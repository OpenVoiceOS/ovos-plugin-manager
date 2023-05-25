from ovos_plugin_manager.utils import load_plugin, normalize_lang, find_plugins, PluginTypes, PluginConfigTypes, \
    load_configs_for_plugin_type, load_plugin_configs


def find_question_solver_plugins():
    return find_plugins(PluginTypes.QUESTION_SOLVER)


def get_question_solver_configs():
    return load_configs_for_plugin_type(PluginTypes.QUESTION_SOLVER)


def get_question_solver_module_configs(module_name):
    # solver plugins return {lang: [list of config dicts]}
    return load_plugin_configs(module_name, PluginConfigTypes.QUESTION_SOLVER,
                               True)


def get_question_solver_lang_configs(lang, include_dialects=False):
    from ovos_plugin_manager.utils import get_plugin_language_configs
    return get_plugin_language_configs(PluginTypes.QUESTION_SOLVER, lang,
                                       include_dialects)


def get_question_solver_supported_langs():
    from ovos_plugin_manager.utils import get_plugin_supported_languages
    return get_plugin_supported_languages(PluginTypes.QUESTION_SOLVER)


def load_question_solver_plugin(module_name):
    """Wrapper function for loading text_transformer plugin.

    Arguments:
        (str) Mycroft text_transformer module name from config
    Returns:
        class: found text_transformer plugin class
    """
    return load_plugin(module_name, PluginTypes.QUESTION_SOLVER)


def find_tldr_solver_plugins():
    return find_plugins(PluginTypes.TLDR_SOLVER)


def get_tldr_solver_configs():
    return load_configs_for_plugin_type(PluginTypes.TLDR_SOLVER)


def get_tldr_solver_module_configs(module_name):
    # solver plugins return {lang: [list of config dicts]}
    return load_plugin_configs(module_name, PluginConfigTypes.TLDR_SOLVER, True)


def get_tldr_solver_lang_configs(lang, include_dialects=False):
    from ovos_plugin_manager.utils import get_plugin_language_configs
    return get_plugin_language_configs(PluginTypes.TLDR_SOLVER, lang, include_dialects)


def get_tldr_solver_supported_langs():
    from ovos_plugin_manager.utils import get_plugin_supported_languages
    return get_plugin_supported_languages(PluginTypes.TLDR_SOLVER)


def load_tldr_solver_plugin(module_name):
    """Wrapper function for loading text_transformer plugin.

    Arguments:
        (str) Mycroft text_transformer module name from config
    Returns:
        class: found text_transformer plugin class
    """
    return load_plugin(module_name, PluginTypes.TLDR_SOLVER)


def find_entailment_solver_plugins():
    return find_plugins(PluginTypes.ENTAILMENT_SOLVER)


def get_entailment_solver_configs():
    return load_configs_for_plugin_type(PluginTypes.ENTAILMENT_SOLVER)


def get_entailment_solver_module_configs(module_name):
    # solver plugins return {lang: [list of config dicts]}
    return load_plugin_configs(module_name, PluginConfigTypes.ENTAILMENT_SOLVER,
                               True)


def get_entailment_solver_lang_configs(lang, include_dialects=False):
    from ovos_plugin_manager.utils import get_plugin_language_configs
    return get_plugin_language_configs(PluginTypes.ENTAILMENT_SOLVER, lang,
                                       include_dialects)


def get_entailment_solver_supported_langs():
    from ovos_plugin_manager.utils import get_plugin_supported_languages
    return get_plugin_supported_languages(PluginTypes.ENTAILMENT_SOLVER)


def load_entailment_solver_plugin(module_name):
    """Wrapper function for loading text_transformer plugin.

    Arguments:
        (str) Mycroft text_transformer module name from config
    Returns:
        class: found text_transformer plugin class
    """
    return load_plugin(module_name, PluginTypes.ENTAILMENT_SOLVER)


def find_multiple_choice_solver_plugins():
    return find_plugins(PluginTypes.MULTIPLE_CHOICE_SOLVER)


def get_multiple_choice_solver_configs():
    return load_configs_for_plugin_type(PluginTypes.MULTIPLE_CHOICE_SOLVER)


def get_multiple_choice_solver_module_configs(module_name):
    # solver plugins return {lang: [list of config dicts]}
    return load_plugin_configs(module_name,
                               PluginConfigTypes.MULTIPLE_CHOICE_SOLVER, True)


def get_multiple_choice_solver_lang_configs(lang, include_dialects=False):
    from ovos_plugin_manager.utils import get_plugin_language_configs
    return get_plugin_language_configs(PluginTypes.MULTIPLE_CHOICE_SOLVER, lang,
                                       include_dialects)


def get_multiple_choice_solver_supported_langs():
    from ovos_plugin_manager.utils import get_plugin_supported_languages
    return get_plugin_supported_languages(PluginTypes.MULTIPLE_CHOICE_SOLVER)


def load_multiple_choice_solver_plugin(module_name):
    """Wrapper function for loading text_transformer plugin.

    Arguments:
        (str) Mycroft text_transformer module name from config
    Returns:
        class: found text_transformer plugin class
    """
    return load_plugin(module_name, PluginTypes.MULTIPLE_CHOICE_SOLVER)


def find_reading_comprehension_solver_plugins():
    return find_plugins(PluginTypes.READING_COMPREHENSION_SOLVER)


def get_reading_comprehension_solver_configs():
    return load_configs_for_plugin_type(PluginTypes.READING_COMPREHENSION_SOLVER)


def get_reading_comprehension_solver_module_configs(module_name):
    # solver plugins return {lang: [list of config dicts]}
    return load_plugin_configs(module_name,
                               PluginConfigTypes.READING_COMPREHENSION_SOLVER,
                               True)


def get_reading_comprehension_solver_lang_configs(lang, include_dialects=False):
    from ovos_plugin_manager.utils import get_plugin_language_configs
    return get_plugin_language_configs(PluginTypes.READING_COMPREHENSION_SOLVER,
                                       lang, include_dialects)


def get_reading_comprehension_solver_supported_langs():
    from ovos_plugin_manager.utils import get_plugin_supported_languages
    return get_plugin_supported_languages(PluginTypes.READING_COMPREHENSION_SOLVER)


def load_reading_comprehension_solver_plugin(module_name):
    """Wrapper function for loading text_transformer plugin.

    Arguments:
        (str) Mycroft text_transformer module name from config
    Returns:
        class: found text_transformer plugin class
    """
    return load_plugin(module_name, PluginTypes.READING_COMPREHENSION_SOLVER)
