from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes
from ovos_config import Configuration
from ovos_utils.log import LOG
from ovos_plugin_manager.templates.eot import EndOfTurnEngine


def find_end_of_turn_plugins() -> dict:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.END_OF_TURN)


def load_end_of_turn_plugin(module_name: str) -> type:
    """
    Get an uninstantiated class for the requested module_name
    @param module_name: Plugin entrypoint name to load
    @return: Uninstantiated class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.END_OF_TURN)


def get_end_of_turn_configs() -> dict:
    """
    Get valid plugin configurations by plugin name
    @return: dict plugin names to list of dict configurations
    """
    from ovos_plugin_manager.utils.config import load_configs_for_plugin_type
    return load_configs_for_plugin_type(PluginTypes.END_OF_TURN)


def get_end_of_turn_module_configs(module_name: str) -> dict:
    """
    Get valid configurations for the specified plugin
    @param module_name: plugin to get configurations for
    @return: dict configurations by language (if provided)
    """
    # End-of-turn plugins return [list of config dicts] or {module_name: [configs]}
    from ovos_plugin_manager.utils.config import load_plugin_configs
    cfgs = load_plugin_configs(module_name, PluginConfigTypes.END_OF_TURN)
    return {module_name: cfgs} if isinstance(cfgs, list) else cfgs


def get_end_of_turn_config(config: dict = None) -> dict:
    """
    Get relevant configuration for factory methods
    @param config: global Configuration OR plugin class-specific configuration
    @return: plugin class-specific configuration
    """
    from ovos_plugin_manager.utils.config import get_plugin_config
    config = config or Configuration()
    if "listener" in config and "end_of_turn" not in config:
        config = get_plugin_config(config, "listener")
    if "end_of_turn" in config:
        config = get_plugin_config(config, "end_of_turn")
    return config


class OVOSEndOfTurnFactory:

    @staticmethod
    def get_class(config=None):
        """Factory method to get an end-of-turn engine class based on configuration.

        The configuration file ``mycroft.conf`` contains a ``listener`` section
        with the name of an end-of-turn module to be read by this method.

        "listener": {
            "end_of_turn": {
                "module": <engine_name>
            }
        }
        """
        config = get_end_of_turn_config(config)
        module = config.get("module")
        if not module:
            raise ValueError(f"End-of-turn plugin not configured in: {config}")
        if module in ("dummy", "none", "silence"):
            return EndOfTurnEngine
        return load_end_of_turn_plugin(module)

    @classmethod
    def create(cls, config=None):
        """Factory method to create an end-of-turn engine based on configuration.

        The configuration file ``mycroft.conf`` contains a ``listener`` section
        with the name of an end-of-turn module to be read by this method.

        "listener": {
            "end_of_turn": {
                "module": <engine_name>
            }
        }
        """
        config = config or Configuration()
        if "listener" in config:
            config = config["listener"]
        if "end_of_turn" in config:
            config = config["end_of_turn"]
        plugin = config.get("module")
        if not plugin:
            raise ValueError(f"End-of-turn plugin not configured in: {config}")

        plugin_config = config.get(plugin, {})
        fallback = plugin_config.get("fallback_module")

        try:
            clazz = cls.get_class(config)
            return clazz(plugin_config)
        except Exception:
            LOG.exception(f'End-of-turn plugin {plugin} could not be loaded!')
            if fallback in config and fallback != plugin:
                LOG.info(f"Attempting to load fallback plugin instead: {fallback}")
                config["module"] = fallback
                return cls.create(config)
            raise
