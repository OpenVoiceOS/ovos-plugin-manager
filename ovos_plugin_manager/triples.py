from ovos_plugin_manager.templates.triples import TriplesExtractor
from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes


def find_triples_plugins() -> dict:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.COREFERENCE_SOLVER)


def load_triples_plugin(module_name: str) -> type(TriplesExtractor):
    """
    Get an uninstantiated class for the requested module_name
    @param module_name: Plugin entrypoint name to load
    @return: Uninstantiated class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.COREFERENCE_SOLVER)


def get_triples_configs() -> dict:
    """
    Get valid plugin configurations by plugin name
    @return: dict plugin names to list of dict configurations
    """
    from ovos_plugin_manager.utils.config import load_configs_for_plugin_type
    return load_configs_for_plugin_type(PluginTypes.TRIPLES)


def get_triples_module_configs(module_name: str) -> dict:
    """
    Get valid configuration for the specified plugin
    @param module_name: plugin to get configuration for
    @return: dict configuration (if provided)
    """
    from ovos_plugin_manager.utils.config import load_plugin_configs
    return load_plugin_configs(module_name, PluginConfigTypes.TRIPLES, True)
