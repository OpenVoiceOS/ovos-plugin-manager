from typing import List, Optional

from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes
from ovos_plugin_manager.templates.gui import GUIExtension
from ovos_utils.log import LOG


def find_plugins(*args, **kwargs):
    # TODO: Deprecate in 0.1.0
    LOG.warning("This reference is deprecated. "
                "Import from ovos_plugin_manager.utils directly")
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(*args, **kwargs)


def load_plugin(*args, **kwargs):
    # TODO: Deprecate in 0.1.0
    LOG.warning("This reference is deprecated. "
                "Import from ovos_plugin_manager.utils directly")
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(*args, **kwargs)


def find_gui_plugins() -> dict:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.GUI)


def load_gui_plugin(module_name: str) -> type(GUIExtension):
    """
    Get an uninstantiated class for the requested module_name
    @param module_name: Plugin entrypoint name to load
    @return: Uninstantiated class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.GUI)


def get_gui_configs() -> dict:
    """
    Get valid plugin configurations by plugin name
    @return: dict plugin names to list of dict configurations
    """
    from ovos_plugin_manager.utils.config import load_configs_for_plugin_type
    return load_configs_for_plugin_type(PluginTypes.GUI)


def get_gui_module_configs(module_name: str) -> List[dict]:
    """
    Get valid configurations for the specified plugin
    @param module_name: plugin to get configuration for
    @return: list of dict configurations (if provided)
    """
    from ovos_plugin_manager.utils.config import load_plugin_configs
    cfgs = load_plugin_configs(module_name, PluginConfigTypes.GUI)
    return {module_name: cfgs} if isinstance(cfgs, list) else cfgs


def get_gui_config(config: Optional[dict] = None) -> dict:
    """
    Get relevant configuration for factory methods
    @param config: global Configuration OR plugin class-specific configuration
    @return: plugin class-specific configuration
    """
    from ovos_plugin_manager.utils.config import get_plugin_config
    return get_plugin_config(config, "gui")


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
        gui_module = gui_config.get('module', 'generic')
        try:
            clazz = OVOSGuiFactory.get_class(gui_config)
            gui = clazz(gui_config, bus=bus, gui=gui)
            LOG.debug(f'Loaded plugin {gui_module}')
        except Exception:
            LOG.exception('The selected gui plugin could not be loaded.')
            raise
        return gui
