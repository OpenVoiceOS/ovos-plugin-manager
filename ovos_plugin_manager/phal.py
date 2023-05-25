from ovos_plugin_manager.utils import load_plugin, find_plugins, PluginTypes, PluginConfigTypes, \
    load_configs_for_plugin_type, load_plugin_configs
from ovos_plugin_manager.templates.phal import PHALPlugin, AdminPlugin


def find_phal_plugins():
    return find_plugins(PluginTypes.PHAL)


def get_phal_configs():
    return load_configs_for_plugin_type(PluginTypes.PHAL)


def get_phal_module_configs(module_name):
    # PHAL plugins return [list of config dicts] or {module_name: [list of config dicts]}
    cfgs = load_plugin_configs(module_name, PluginConfigTypes.PHAL)
    return {module_name: cfgs} if isinstance(cfgs, list) else cfgs


def find_admin_plugins():
    return find_plugins(PluginTypes.ADMIN)


def get_admin_configs():
    return load_configs_for_plugin_type(PluginTypes.ADMIN)


def get_admin_module_configs(module_name):
    # admin plugins return [list of config dicts] or {module_name: [list of config dicts]}
    cfgs = load_plugin_configs(module_name, PluginConfigTypes.ADMIN)
    return {module_name: cfgs} if isinstance(cfgs, list) else cfgs
