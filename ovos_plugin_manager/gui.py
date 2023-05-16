from ovos_plugin_manager.utils import load_plugin, find_plugins, PluginTypes, PluginConfigTypes
from ovos_plugin_manager.templates.gui import GUIExtension
from ovos_utils.log import LOG


def find_gui_plugins():
    return find_plugins(PluginTypes.GUI)


def get_gui_configs():
    return {plug: get_gui_module_configs(plug)
            for plug in find_gui_plugins()}


def get_gui_module_configs(module_name):
    # GUI plugins return [list of config dicts] or {module_name: [list of config dicts]}
    cfgs = load_plugin(module_name + ".config",  PluginConfigTypes.GUI)
    return {module_name: cfgs} if isinstance(cfgs, list) else cfgs


def load_gui_plugin(module_name):
    return load_plugin(module_name, PluginTypes.GUI)


class OVOSGuiFactory:
    @staticmethod
    def get_class(config=None):
        """Factory method to get a gui engine class based on configuration.

        The configuration file ``mycroft.conf`` contains a ``gui`` section with
        the name of a gui module to be read by this method.

        "gui": {
            "extension": <engine_name>
        }
        """
        config = get_gui_config(config)
        gui_module = config.get("module") or 'generic'
        if gui_module == 'generic':
            return GUIExtension
        return load_gui_plugin(gui_module)

    @staticmethod
    def create(config=None, bus=None, gui=None):
        """Factory method to create a gui engine based on configuration.

        The configuration file ``mycroft.conf`` contains a ``gui`` section with
        the name of a gui module to be read by this method.

        "gui": {
            "extension": <engine_name>
        }
        """
        gui_config = get_gui_config(config)
        gui_module = gui_config.get('extension', 'generic')
        try:
            clazz = OVOSGuiFactory.get_class(gui_config)
            gui = clazz(gui_config, bus=bus, gui=gui)
            LOG.debug(f'Loaded plugin {gui_module}')
        except Exception:
            LOG.exception('The selected gui plugin could not be loaded.')
            raise
        return gui


def get_gui_config(config=None):
    from ovos_plugin_manager.utils.config import get_plugin_config
    return get_plugin_config(config, "gui")
