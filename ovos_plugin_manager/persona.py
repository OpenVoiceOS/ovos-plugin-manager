from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes
from ovos_config import Configuration
from ovos_utils.log import LOG
from ovos_plugin_manager.templates.persona import Persona


def find_persona_plugins() -> dict:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.PERSONA)


def load_persona_plugin(module_name: str) -> type(Persona):
    """
    Get an uninstantiated class for the requested module_name
    @param module_name: Plugin entrypoint name to load
    @return: Uninstantiated class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.PERSONA)


def get_persona_configs() -> dict:
    """
    Get valid plugin configurations by plugin name
    @return: dict plugin names to list of dict configurations
    """
    from ovos_plugin_manager.utils.config import load_configs_for_plugin_type
    return load_configs_for_plugin_type(PluginTypes.PERSONA)


def get_persona_module_configs(module_name: str) -> dict:
    """
    Get valid configurations for the specified plugin
    @param module_name: plugin to get configuration for
    @return: dict configurations by language (if provided)
    """
    # TOKENIZATION plugins return {lang: [list of config dicts]}
    from ovos_plugin_manager.utils.config import load_plugin_configs
    return load_plugin_configs(module_name,
                               PluginConfigTypes.PERSONA, True)


def get_persona_lang_configs(lang: str,
                             include_dialects: bool = False) -> dict:
    """
    Get a dict of plugin names to list valid configurations for the requested
    lang.
    @param lang: Language to get configurations for
    @param include_dialects: consider configurations in different locales
    @return: dict {`plugin_name`: `valid_configs`]}
    """
    from ovos_plugin_manager.utils.config import get_plugin_language_configs
    return get_plugin_language_configs(PluginTypes.PERSONA, lang,
                                       include_dialects)


def get_persona_supported_langs() -> dict:
    """
    Return a dict of plugin names to list supported languages
    @return: dict plugin names to list supported languages
    """
    from ovos_plugin_manager.utils.config import get_plugin_supported_languages
    return get_plugin_supported_languages(PluginTypes.PERSONA)


def get_persona_config(config: dict = None) -> dict:
    """
    Get relevant configuration for factory methods
    @param config: global Configuration OR plugin class-specific configuration
    @return: plugin class-specific configuration
    """
    from ovos_plugin_manager.utils.config import get_plugin_config
    config = config or Configuration()
    return get_plugin_config(config, "persona")


class OVOSPersonaFactory:
    """ reads mycroft.conf and returns the globally configured plugin """
    @staticmethod
    def get_class(config=None):
        """Factory method to get a Tokenizer engine class based on configuration.

        The configuration file ``mycroft.conf`` contains a ``tokenization`` section with
        the name of a Tokenizer module to be read by this method.

        "tokenization": {
            "module": <engine_name>
        }
        """
        config = get_persona_config(config)
        tokenization_module = config.get("module")
        return load_persona_plugin(tokenization_module)

    @staticmethod
    def create(config=None):
        """Factory method to create a Tokenizer engine based on configuration.

        The configuration file ``mycroft.conf`` contains a ``tokenization`` section with
        the name of a Tokenizer module to be read by this method.

        "tokenization": {
            "module": <engine_name>
        }
        """
        config = config or get_persona_config()
        plugin = config.get("module")
        plugin_config = config.get(plugin) or {}
        try:
            clazz = OVOSPersonaFactory.get_class(config)
            return clazz(plugin_config)
        except Exception:
            LOG.exception(f'Persona plugin {plugin} could not be loaded!')
