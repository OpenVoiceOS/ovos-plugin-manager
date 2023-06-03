from typing import Optional

from ovos_plugin_manager.utils import normalize_lang, PluginTypes, \
    PluginConfigTypes
from ovos_config import Configuration
from ovos_utils.log import LOG
from ovos_plugin_manager.templates.coreference import CoreferenceSolverEngine, \
    replace_coreferences


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


def find_coref_plugins() -> dict:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.COREFERENCE_SOLVER)


def load_coref_plugin(module_name: str) -> type(CoreferenceSolverEngine):
    """
    Get an uninstantiated class for the requested module_name
    @param module_name: Plugin entrypoint name to load
    @return: Uninstantiated class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.COREFERENCE_SOLVER)


def get_coref_configs() -> dict:
    """
    Get valid plugin configurations by plugin name
    @return: dict plugin names to list of dict configurations
    """
    from ovos_plugin_manager.utils.config import load_configs_for_plugin_type
    return load_configs_for_plugin_type(PluginTypes.COREFERENCE_SOLVER)


def get_coref_module_configs(module_name: str) -> dict:
    """
    Get valid configuration for the specified plugin
    @param module_name: plugin to get configuration for
    @return: dict configuration (if provided)
    """
    from ovos_plugin_manager.utils.config import load_plugin_configs
    return load_plugin_configs(module_name,
                               PluginConfigTypes.COREFERENCE_SOLVER, True)


def get_coref_lang_configs(lang: str, include_dialects: bool = False) -> dict:
    """
    Get a dict of plugin names to list valid configurations for the requested
    lang.
    @param lang: Language to get configurations for
    @param include_dialects: consider configurations in different locales
    @return: dict {`plugin_name`: [`valid_configs`]}
    """
    from ovos_plugin_manager.utils.config import get_plugin_language_configs
    return get_plugin_language_configs(PluginTypes.COREFERENCE_SOLVER, lang,
                                       include_dialects)


def get_coref_supported_langs() -> dict:
    """
    Return a dict of plugin names to list supported languages
    @return: dict plugin names to list supported languages
    """
    from ovos_plugin_manager.utils.config import get_plugin_supported_languages
    return get_plugin_supported_languages(PluginTypes.COREFERENCE_SOLVER)


def get_coref_config(config: Optional[dict] = None) -> dict:
    """
    Get relevant configuration for factory methods
    @param config: global Configuration OR plugin class-specific configuration
    @return: plugin class-specific configuration
    """
    from ovos_plugin_manager.utils.config import get_plugin_config
    config = config or Configuration()
    return get_plugin_config(config, "coref")


class OVOSCoreferenceSolverFactory:
    """ replicates the base mycroft class, but uses only OPM enabled plugins"""
    MAPPINGS = {
        "pronomial": "ovos-coref-plugin-pronomial"
    }

    @staticmethod
    def get_class(config=None):
        """Factory method to get a CoreferenceSolver engine class based on configuration.

        The configuration file ``mycroft.conf`` contains a ``coref`` section with
        the name of a CoreferenceSolver module to be read by this method.

        "coref": {
            "module": <engine_name>
        }
        """
        config = get_coref_config(config)
        coref_module = config.get("module", "dummy")
        if coref_module == "dummy":
            return CoreferenceSolverEngine
        if coref_module in OVOSCoreferenceSolverFactory.MAPPINGS:
            coref_module = OVOSCoreferenceSolverFactory.MAPPINGS[coref_module]
        return load_coref_plugin(coref_module)

    @staticmethod
    def create(config=None):
        """Factory method to create a CoreferenceSolver engine based on configuration.

        The configuration file ``mycroft.conf`` contains a ``coref`` section with
        the name of a CoreferenceSolver module to be read by this method.

        "coref": {
            "module": <engine_name>
        }
        """
        config = config or get_coref_config()
        plugin = config.get("module") or "dummy"
        plugin_config = config.get(plugin) or {}
        try:
            clazz = OVOSCoreferenceSolverFactory.get_class(config)
            return clazz(plugin_config)
        except Exception:
            LOG.exception(f'CoreferenceSolver plugin {plugin} '
                          f'could not be loaded!')
            raise
