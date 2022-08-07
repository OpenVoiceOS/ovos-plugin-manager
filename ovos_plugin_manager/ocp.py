from ovos_plugin_manager.utils import load_plugin, find_plugins, PluginTypes, PluginConfigTypes
from ovos_plugin_manager.templates.ocp import OCPStreamExtractor


def find_ocp_plugins():
    return find_plugins(PluginTypes.STREAM_EXTRACTOR)


