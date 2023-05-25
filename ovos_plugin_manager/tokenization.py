from ovos_plugin_manager.utils import normalize_lang, load_plugin, find_plugins, PluginTypes, PluginConfigTypes
from ovos_config import Configuration
from ovos_utils.log import LOG
from ovos_plugin_manager.templates.tokenization import Tokenizer


def find_tokenization_plugins():
    return find_plugins(PluginTypes.TOKENIZATION)


def get_tokenization_configs():
    from ovos_plugin_manager.utils import load_configs_for_plugin_type
    return load_configs_for_plugin_type(PluginTypes.TOKENIZATION)


def get_tokenization_module_configs(module_name):
    # TOKENIZATION plugins return {lang: [list of config dicts]}
    from ovos_plugin_manager.utils import load_plugin_configs
    return load_plugin_configs(module_name,
                               PluginConfigTypes.TOKENIZATION, True)


def get_tokenization_lang_configs(lang, include_dialects=False):
    from ovos_plugin_manager.utils import get_plugin_language_configs
    return get_plugin_language_configs(PluginTypes.TOKENIZATION, lang,
                                       include_dialects)


def get_tokenization_supported_langs():
    from ovos_plugin_manager.utils import get_plugin_supported_languages
    return get_plugin_supported_languages(PluginTypes.TOKENIZATION)


def load_tokenization_plugin(module_name):
    """Wrapper function for loading tokenization plugin.

    Arguments:
        module_name (str): tokenization module name from config
    Returns:
        class: Tokenizer plugin class
    """
    return load_plugin(module_name, PluginTypes.TOKENIZATION)


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


def get_tokenization_config(config=None):
    from ovos_plugin_manager.utils.config import get_plugin_config
    config = config or Configuration()
    return get_plugin_config(config, "tokenization")



