from ovos_plugin_manager.utils import normalize_lang, PluginTypes, \
    PluginConfigTypes
from ovos_plugin_manager.templates.transformers import MetadataTransformer
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


def find_metadata_transformer_plugins() -> dict:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.METADATA_TRANSFORMER)


def load_metadata_transformer_plugin(module_name: str) -> \
        type(MetadataTransformer):
    """
    Get an uninstantiated class for the requested module_name
    @param module_name: Plugin entrypoint name to load
    @return: Uninstantiated class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.METADATA_TRANSFORMER)


def get_metadata_transformer_configs() -> dict:
    """
    Get valid plugin configurations by plugin name
    @return: dict plugin names to list of dict configurations
    """
    from ovos_plugin_manager.utils.config import load_configs_for_plugin_type
    return load_configs_for_plugin_type(PluginTypes.METADATA_TRANSFORMER)


def get_metadata_transformer_module_configs(module_name) -> dict:
    """
    Get valid configurations for the specified plugin
    @param module_name: plugin to get configuration for
    @return: dict configurations by language (if provided)
    """
    from ovos_plugin_manager.utils.config import load_plugin_configs
    return load_plugin_configs(module_name,
                               PluginConfigTypes.METADATA_TRANSFORMER, True)


def get_metadata_transformer_lang_configs(lang: str,
                                     include_dialects: bool = False) -> dict:
    """
    Get a dict of plugin names to list valid configurations for the requested
    lang.
    @param lang: Language to get configurations for
    @param include_dialects: consider configurations in different locales
    @return: dict {`plugin_name`: `valid_configs`]}
    """
    from ovos_plugin_manager.utils.config import get_plugin_language_configs
    return get_plugin_language_configs(PluginTypes.METADATA_TRANSFORMER, lang,
                                       include_dialects)


def get_metadata_transformer_supported_langs() -> dict:
    """
    Return a dict of plugin names to list supported languages
    @return: dict plugin names to list supported languages
    """
    from ovos_plugin_manager.utils.config import get_plugin_supported_languages
    return get_plugin_supported_languages(PluginTypes.METADATA_TRANSFORMER)
