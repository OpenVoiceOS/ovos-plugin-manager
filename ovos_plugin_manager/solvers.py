from ovos_plugin_manager.utils import normalize_lang, \
    PluginTypes, PluginConfigTypes
from ovos_plugin_manager.templates.solvers import QuestionSolver, TldrSolver, \
    EntailmentSolver, MultipleChoiceSolver, EvidenceSolver
from ovos_utils.log import LOG


def find_plugins(*args, **kwargs):
    # TODO: Deprecate in 0.1.0
    LOG.warning("This reference is deprecated. "
                "Import from ovos_plugin_manager.utils directly")
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(*args, **kwargs)


def load_plugin(*args, **kwargs):
    # TODO: Deprecate in 0.1.0
    LOG.warning("This reference is deprecated. "
                "Import from ovos_plugin_manager.utils directly")
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(*args, **kwargs)


def find_question_solver_plugins() -> dict:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.QUESTION_SOLVER)


def load_question_solver_plugin(module_name: str) -> type(QuestionSolver):
    """
    Get an uninstantiated class for the requested module_name
    @param module_name: Plugin entrypoint name to load
    @return: Uninstantiated class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.QUESTION_SOLVER)


def get_question_solver_configs() -> dict:
    """
    Get valid plugin configurations by plugin name
    @return: dict plugin names to list of dict configurations
    """
    from ovos_plugin_manager.utils.config import load_configs_for_plugin_type
    return load_configs_for_plugin_type(PluginTypes.QUESTION_SOLVER)


def get_question_solver_module_configs(module_name: str) -> dict:
    """
    Get valid configurations for the specified plugin
    @param module_name: plugin to get configuration for
    @return: lists of dict configurations by language (if provided)
    """
    from ovos_plugin_manager.utils.config import load_plugin_configs
    # solver plugins return {lang: [list of config dicts]}
    return load_plugin_configs(module_name, PluginConfigTypes.QUESTION_SOLVER,
                               True)


def get_question_solver_lang_configs(lang: str,
                                     include_dialects: bool = False) -> dict:
    """
    Get a dict of plugin names to list valid configurations for the requested
    lang.
    @param lang: Language to get configurations for
    @param include_dialects: consider configurations in different locales
    @return: dict {`plugin_name`: `valid_configs`]}
    """
    from ovos_plugin_manager.utils.config import get_plugin_language_configs
    return get_plugin_language_configs(PluginTypes.QUESTION_SOLVER, lang,
                                       include_dialects)


def get_question_solver_supported_langs() -> dict:
    """
    Return a dict of plugin names to list supported languages
    @return: dict plugin names to list supported languages
    """
    from ovos_plugin_manager.utils.config import get_plugin_supported_languages
    return get_plugin_supported_languages(PluginTypes.QUESTION_SOLVER)


def find_tldr_solver_plugins() -> dict:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.TLDR_SOLVER)


def load_tldr_solver_plugin(module_name: str) -> type(TldrSolver):
    """
    Get an uninstantiated class for the requested module_name
    @param module_name: Plugin entrypoint name to load
    @return: Uninstantiated class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.TLDR_SOLVER)


def get_tldr_solver_configs() -> dict:
    """
    Get valid plugin configurations by plugin name
    @return: dict plugin names to list of dict configurations
    """
    from ovos_plugin_manager.utils.config import load_configs_for_plugin_type
    return load_configs_for_plugin_type(PluginTypes.TLDR_SOLVER)


def get_tldr_solver_module_configs(module_name: str) -> dict:
    """
    Get valid configurations for the specified plugin
    @param module_name: plugin to get configuration for
    @return: lists of dict configurations by language (if provided)
    """
    from ovos_plugin_manager.utils.config import load_plugin_configs
    # solver plugins return {lang: [list of config dicts]}
    return load_plugin_configs(module_name, PluginConfigTypes.TLDR_SOLVER, True)


def get_tldr_solver_lang_configs(lang: str,
                                 include_dialects: bool = False) -> dict:
    """
    Get a dict of plugin names to list valid configurations for the requested
    lang.
    @param lang: Language to get configurations for
    @param include_dialects: consider configurations in different locales
    @return: dict {`plugin_name`: `valid_configs`]}
    """
    from ovos_plugin_manager.utils.config import get_plugin_language_configs
    return get_plugin_language_configs(PluginTypes.TLDR_SOLVER, lang,
                                       include_dialects)


def get_tldr_solver_supported_langs() -> dict:
    """
    Return a dict of plugin names to list supported languages
    @return: dict plugin names to list supported languages
    """
    from ovos_plugin_manager.utils.config import get_plugin_supported_languages
    return get_plugin_supported_languages(PluginTypes.TLDR_SOLVER)


def find_entailment_solver_plugins() -> dict:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.ENTAILMENT_SOLVER)


def load_entailment_solver_plugin(module_name: str) -> type(EntailmentSolver):
    """
    Get an uninstantiated class for the requested module_name
    @param module_name: Plugin entrypoint name to load
    @return: Uninstantiated class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.ENTAILMENT_SOLVER)


def get_entailment_solver_configs() -> dict:
    """
    Get valid plugin configurations by plugin name
    @return: dict plugin names to list of dict configurations
    """
    from ovos_plugin_manager.utils.config import load_configs_for_plugin_type
    return load_configs_for_plugin_type(PluginTypes.ENTAILMENT_SOLVER)


def get_entailment_solver_module_configs(module_name: str) -> dict:
    """
    Get valid configurations for the specified plugin
    @param module_name: plugin to get configuration for
    @return: dict configurations by language (if provided)
    """
    from ovos_plugin_manager.utils.config import load_plugin_configs
    # solver plugins return {lang: [list of config dicts]}
    return load_plugin_configs(module_name, PluginConfigTypes.ENTAILMENT_SOLVER,
                               True)


def get_entailment_solver_lang_configs(lang: str,
                                     include_dialects: bool = False) -> dict:
    """
    Get a dict of plugin names to list valid configurations for the requested
    lang.
    @param lang: Language to get configurations for
    @param include_dialects: consider configurations in different locales
    @return: dict {`plugin_name`: `valid_configs`]}
    """
    from ovos_plugin_manager.utils.config import get_plugin_language_configs
    return get_plugin_language_configs(PluginTypes.ENTAILMENT_SOLVER, lang,
                                       include_dialects)


def get_entailment_solver_supported_langs() -> dict:
    """
    Return a dict of plugin names to list supported languages
    @return: dict plugin names to list supported languages
    """
    from ovos_plugin_manager.utils.config import get_plugin_supported_languages
    return get_plugin_supported_languages(PluginTypes.ENTAILMENT_SOLVER)


def find_multiple_choice_solver_plugins() -> dict:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.MULTIPLE_CHOICE_SOLVER)


def load_multiple_choice_solver_plugin(module_name: str) -> \
        type(MultipleChoiceSolver):
    """
    Get an uninstantiated class for the requested module_name
    @param module_name: Plugin entrypoint name to load
    @return: Uninstantiated class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.MULTIPLE_CHOICE_SOLVER)


def get_multiple_choice_solver_configs() -> dict:
    """
    Get valid plugin configurations by plugin name
    @return: dict plugin names to list of dict configurations
    """
    from ovos_plugin_manager.utils.config import load_configs_for_plugin_type
    return load_configs_for_plugin_type(PluginTypes.MULTIPLE_CHOICE_SOLVER)


def get_multiple_choice_solver_module_configs(module_name: str) -> dict:
    """
    Get valid configurations for the specified plugin
    @param module_name: plugin to get configuration for
    @return: dict configurations by language (if provided)
    """
    from ovos_plugin_manager.utils.config import load_plugin_configs
    # solver plugins return {lang: [list of config dicts]}
    return load_plugin_configs(module_name,
                               PluginConfigTypes.MULTIPLE_CHOICE_SOLVER, True)


def get_multiple_choice_solver_lang_configs(lang: str,
                                            include_dialects: bool = False) -> \
        dict:
    """
    Get a dict of plugin names to list valid configurations for the requested
    lang.
    @param lang: Language to get configurations for
    @param include_dialects: consider configurations in different locales
    @return: dict {`plugin_name`: `valid_configs`]}
    """
    from ovos_plugin_manager.utils.config import get_plugin_language_configs
    return get_plugin_language_configs(PluginTypes.MULTIPLE_CHOICE_SOLVER, lang,
                                       include_dialects)


def get_multiple_choice_solver_supported_langs() -> dict:
    """
    Return a dict of plugin names to list supported languages
    @return: dict plugin names to list supported languages
    """
    from ovos_plugin_manager.utils.config import get_plugin_supported_languages
    return get_plugin_supported_languages(PluginTypes.MULTIPLE_CHOICE_SOLVER)


def find_reading_comprehension_solver_plugins() -> dict:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.READING_COMPREHENSION_SOLVER)


def load_reading_comprehension_solver_plugin(module_name: str) -> \
        type(EvidenceSolver):
    """
    Get an uninstantiated class for the requested module_name
    @param module_name: Plugin entrypoint name to load
    @return: Uninstantiated class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.READING_COMPREHENSION_SOLVER)


def get_reading_comprehension_solver_configs() -> dict:
    """
    Get valid plugin configurations by plugin name
    @return: dict plugin names to list of dict configurations
    """
    from ovos_plugin_manager.utils.config import load_configs_for_plugin_type
    return load_configs_for_plugin_type(
        PluginTypes.READING_COMPREHENSION_SOLVER)


def get_reading_comprehension_solver_module_configs(module_name: str) -> dict:
    """
    Get valid configurations for the specified plugin
    @param module_name: plugin to get configuration for
    @return: dict configurations by language (if provided)
    """
    from ovos_plugin_manager.utils.config import load_plugin_configs
    # solver plugins return {lang: [list of config dicts]}
    return load_plugin_configs(module_name,
                               PluginConfigTypes.READING_COMPREHENSION_SOLVER,
                               True)


def get_reading_comprehension_solver_lang_configs(lang: str,
                                     include_dialects: bool = False) -> dict:
    """
    Get a dict of plugin names to list valid configurations for the requested
    lang.
    @param lang: Language to get configurations for
    @param include_dialects: consider configurations in different locales
    @return: dict {`plugin_name`: `valid_configs`]}
    """
    from ovos_plugin_manager.utils.config import get_plugin_language_configs
    return get_plugin_language_configs(PluginTypes.READING_COMPREHENSION_SOLVER,
                                       lang, include_dialects)


def get_reading_comprehension_solver_supported_langs() -> dict:
    """
    Return a dict of plugin names to list supported languages
    @return: dict plugin names to list supported languages
    """
    from ovos_plugin_manager.utils.config import get_plugin_supported_languages
    return get_plugin_supported_languages(
        PluginTypes.READING_COMPREHENSION_SOLVER)

