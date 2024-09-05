from ovos_plugin_manager.utils import normalize_lang, \
    PluginTypes, PluginConfigTypes
from ovos_config import Configuration
from ovos_utils.log import LOG
from ovos_plugin_manager.templates.tokenization import Tokenizer


def find_tokenization_plugins() -> dict:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.TOKENIZATION)


def load_tokenization_plugin(module_name: str) -> type(Tokenizer):
    """
    Get an uninstantiated class for the requested module_name
    @param module_name: Plugin entrypoint name to load
    @return: Uninstantiated class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.TOKENIZATION)


def get_tokenization_configs() -> dict:
    """
    Get valid plugin configurations by plugin name
    @return: dict plugin names to list of dict configurations
    """
    from ovos_plugin_manager.utils.config import load_configs_for_plugin_type
    return load_configs_for_plugin_type(PluginTypes.TOKENIZATION)


def get_tokenization_module_configs(module_name: str) -> dict:
    """
    Get valid configurations for the specified plugin
    @param module_name: plugin to get configuration for
    @return: dict configurations by language (if provided)
    """
    # TOKENIZATION plugins return {lang: [list of config dicts]}
    from ovos_plugin_manager.utils.config import load_plugin_configs
    return load_plugin_configs(module_name,
                               PluginConfigTypes.TOKENIZATION, True)


def get_tokenization_lang_configs(lang: str,
                                  include_dialects: bool = False) -> dict:
    """
    Get a dict of plugin names to list valid configurations for the requested
    lang.
    @param lang: Language to get configurations for
    @param include_dialects: consider configurations in different locales
    @return: dict {`plugin_name`: `valid_configs`]}
    """
    from ovos_plugin_manager.utils.config import get_plugin_language_configs
    return get_plugin_language_configs(PluginTypes.TOKENIZATION, lang,
                                       include_dialects)


def get_tokenization_supported_langs() -> dict:
    """
    Return a dict of plugin names to list supported languages
    @return: dict plugin names to list supported languages
    """
    from ovos_plugin_manager.utils.config import get_plugin_supported_languages
    return get_plugin_supported_languages(PluginTypes.TOKENIZATION)


def get_tokenization_config(config: dict = None) -> dict:
    """
    Get relevant configuration for factory methods
    @param config: global Configuration OR plugin class-specific configuration
    @return: plugin class-specific configuration
    """
    from ovos_plugin_manager.utils.config import get_plugin_config
    config = config or Configuration()
    return get_plugin_config(config, "tokenization")


class OVOSTokenizerFactory:
    """ reads mycroft.conf and returns the globally configured plugin """
    MAPPINGS = {
        # default split at sentence boundaries
        # usually helpful in other plugins and included in base class
        "dummy": "ovos-tokenization-plugin-quebrafrases"
    }

    @staticmethod
    def get_class(config=None):
        """Factory method to get a Tokenizer engine class based on configuration.

        The configuration file ``mycroft.conf`` contains a ``tokenization`` section with
        the name of a Tokenizer module to be read by this method.

        "tokenization": {
            "module": <engine_name>
        }
        """
        config = get_tokenization_config(config)
        tokenization_module = config.get("module", "ovos-tokenization-plugin-quebrafrases")
        if tokenization_module in OVOSTokenizerFactory.MAPPINGS:
            tokenization_module = OVOSTokenizerFactory.MAPPINGS[tokenization_module]
        return load_tokenization_plugin(tokenization_module)

    @staticmethod
    def create(config=None):
        """Factory method to create a Tokenizer engine based on configuration.

        The configuration file ``mycroft.conf`` contains a ``tokenization`` section with
        the name of a Tokenizer module to be read by this method.

        "tokenization": {
            "module": <engine_name>
        }
        """
        config = config or get_tokenization_config()
        plugin = config.get("module") or "ovos-tokenization-plugin-quebrafrases"
        plugin_config = config.get(plugin) or {}
        try:
            clazz = OVOSTokenizerFactory.get_class(config)
            return clazz(plugin_config)
        except Exception:
            LOG.exception(f'Tokenizer plugin {plugin} could not be loaded!')
            return Tokenizer()
