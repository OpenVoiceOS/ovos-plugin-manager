try:
    import mycroft
except ImportError:
    from ovos_utils.system import search_mycroft_core_location
    MYCROFT_ROOT = search_mycroft_core_location()
    if MYCROFT_ROOT:
        import sys
        sys.path.append(MYCROFT_ROOT)
    import mycroft

from ovos_plugin_manager.utils import load_plugin, find_plugins, PluginTypes
from ovos_plugin_manager.plugin_entry import MycroftPlugin
