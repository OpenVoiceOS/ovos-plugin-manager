from ovos_plugin_manager.utils import PluginTypes, \
    PluginConfigTypes
from ovos_plugin_manager.templates.phal import PHALPlugin, AdminPlugin
from ovos_utils.log import LOG


def find_phal_plugins() -> dict:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.PHAL)


def get_phal_configs() -> dict:
    """
    Get valid plugin configurations by plugin name
    @return: dict plugin names to list of dict configurations
    """
    from ovos_plugin_manager.utils.config import load_configs_for_plugin_type
    return load_configs_for_plugin_type(PluginTypes.PHAL)


def get_phal_module_configs(module_name: str) -> dict:
    """
    Get valid configurations for the specified plugin
    @param module_name: plugin to get configuration for
    @return: dict configurations (if provided)
    """
    from ovos_plugin_manager.utils.config import load_plugin_configs
    # PHAL plugins return [list of config dicts] or {module_name: [list of config dicts]}
    cfgs = load_plugin_configs(module_name, PluginConfigTypes.PHAL)
    return {module_name: cfgs} if isinstance(cfgs, list) else cfgs


def find_admin_plugins():
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.ADMIN)


def get_admin_configs() -> dict:
    """
    Get valid plugin configurations by plugin name
    @return: dict plugin names to list of dict configurations
    """
    from ovos_plugin_manager.utils.config import load_configs_for_plugin_type
    return load_configs_for_plugin_type(PluginTypes.ADMIN)


def get_admin_module_configs(module_name: str) -> dict:
    """
    Get valid configurations for the specified plugin
    @param module_name: plugin to get configuration for
    @return: dict configurations (if provided)
    """
    from ovos_plugin_manager.utils.config import load_plugin_configs
    # admin plugins return [list of config dicts] or {module_name: [list of config dicts]}
    cfgs = load_plugin_configs(module_name, PluginConfigTypes.ADMIN)
    return {module_name: cfgs} if isinstance(cfgs, list) else cfgs
