from ovos_plugin_manager.utils import load_plugin, find_plugins, PluginTypes
from ovos_utils.configuration import read_mycroft_config
from ovos_utils.log import LOG
from ovos_plugin_manager.templates.postag import PosTagger


def find_postag_plugins():
    return find_plugins(PluginTypes.POSTAG)


def load_postag_plugin(module_name):
    """Wrapper function for loading postag plugin.

    Arguments:
        module_name (str): postag module name from config
    Returns:
        class: PosTagger plugin class
    """
    return load_plugin(module_name, PluginTypes.POSTAG)


class OVOSPosTaggerFactory:
    """ reads mycroft.conf and returns the globally configured plugin """
    MAPPINGS = {
        # default split at sentence boundaries
        # usually helpful in other plugins and included in base class
        "dummy": "ovos-postag-plugin-dummy"
    }

    @staticmethod
    def get_class(config=None):
        """Factory method to get a PosTagger engine class based on configuration.

        The configuration file ``mycroft.conf`` contains a ``postag`` section with
        the name of a PosTagger module to be read by this method.

        "postag": {
            "module": <engine_name>
        }
        """
        config = config or get_postag_config()
        postag_module = config.get("module", "ovos-postag-plugin-dummy")
        if postag_module in OVOSPosTaggerFactory.MAPPINGS:
            postag_module = OVOSPosTaggerFactory.MAPPINGS[postag_module]
        return load_postag_plugin(postag_module)

    @staticmethod
    def create(config=None):
        """Factory method to create a PosTagger engine based on configuration.

        The configuration file ``mycroft.conf`` contains a ``postag`` section with
        the name of a PosTagger module to be read by this method.

        "postag": {
            "module": <engine_name>
        }
        """
        config = config or get_postag_config()
        plugin = config.get("module") or "ovos-postag-plugin-dummy"
        plugin_config = config.get(plugin) or {}
        try:
            clazz = OVOSPosTaggerFactory.get_class(config)
            return clazz(plugin_config)
        except Exception:
            LOG.error(f'Postag plugin {plugin} could not be loaded!')
            return PosTagger()


def get_postag_config(config=None):
    config = config or read_mycroft_config()
    lang = config.get("lang")
    if "intentBox" in config and "postag" not in config:
        config = config["intentBox"] or {}
        lang = config.get("lang") or lang
    if "postag" in config:
        config = config["postag"]
        lang = config.get("lang") or lang
    config["lang"] = lang or "en-us"
    postag_module = config.get('module') or 'ovos-postag-plugin-dummy'
    postag_config = config.get(postag_module, {})
    postag_config["module"] = postag_module
    return postag_config


