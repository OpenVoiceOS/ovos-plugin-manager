from ovos_plugin_manager.utils import load_plugin, find_plugins, PluginTypes
from ovos_utils.configuration import read_mycroft_config
from ovos_utils.log import LOG
from ovos_plugin_manager.templates.coreference import CoreferenceSolverEngine, replace_coreferences


def find_coref_plugins():
    return find_plugins(PluginTypes.COREFERENCE_SOLVER)


def load_coref_plugin(module_name):
    """Wrapper function for loading coref plugin.

    Arguments:
        module_name (str): coref module name from config
    Returns:
        class: CoreferenceSolver plugin class
    """
    return load_plugin(module_name, PluginTypes.COREFERENCE_SOLVER)


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
        config = config or get_coref_config()
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
            LOG.error(f'CoreferenceSolver plugin {plugin} could not be loaded!')
            raise


def get_coref_config(config=None):
    config = config or read_mycroft_config()
    lang = config.get("lang")
    if "intentBox" in config and "coref" not in config:
        config = config["intentBox"] or {}
        lang = config.get("lang") or lang
    if "coref" in config:
        config = config["coref"]
        lang = config.get("lang") or lang
    config["lang"] = lang or "en-us"
    coref_module = config.get('module') or 'dummy'
    coref_config = config.get(coref_module, {})
    coref_config["module"] = coref_module
    return coref_config


