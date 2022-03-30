from ovos_plugin_manager.utils import load_plugin, find_plugins, PluginTypes
from ovos_utils.configuration import read_mycroft_config
from ovos_utils.log import LOG
from ovos_plugin_manager.templates.tokenization import Tokenizer


def find_tokenization_plugins():
    return find_plugins(PluginTypes.TOKENIZATION)


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
        config = config or get_tokenization_config()
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
            LOG.error(f'Tokenizer plugin {plugin} could not be loaded!')
            return Tokenizer()


def get_tokenization_config(config=None):
    config = config or read_mycroft_config()
    lang = config.get("lang")
    if "intentBox" in config and "tokenization" not in config:
        config = config["intentBox"] or {}
        lang = config.get("lang") or lang
    if "tokenization" in config:
        config = config["tokenization"]
        lang = config.get("lang") or lang
    config["lang"] = lang or "en-us"
    tokenization_module = config.get('module') or 'ovos-tokenization-plugin-quebrafrases'
    tokenization_config = config.get(tokenization_module, {})
    tokenization_config["module"] = tokenization_module
    return tokenization_config


