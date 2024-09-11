from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes
from ovos_config import Configuration
from ovos_utils.log import LOG
from ovos_plugin_manager.templates.vad import VADEngine


def find_vad_plugins() -> dict:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.VAD)


def load_vad_plugin(module_name: str) -> type(VADEngine):
    """
    Get an uninstantiated class for the requested module_name
    @param module_name: Plugin entrypoint name to load
    @return: Uninstantiated class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.VAD)


def get_vad_configs() -> dict:
    """
    Get valid plugin configurations by plugin name
    @return: dict plugin names to list of dict configurations
    """
    from ovos_plugin_manager.utils.config import load_configs_for_plugin_type
    return load_configs_for_plugin_type(PluginTypes.VAD)


def get_vad_module_configs(module_name: str) -> dict:
    """
    Get valid configurations for the specified plugin
    @param module_name: plugin to get configuration for
    @return: dict configurations by language (if provided)
    """
    # VAD plugins return [list of config dicts] or {module_name: [list of config dicts]}
    from ovos_plugin_manager.utils.config import load_plugin_configs
    cfgs = load_plugin_configs(module_name,
                               PluginConfigTypes.VAD)
    return {module_name: cfgs} if isinstance(cfgs, list) else cfgs


def get_vad_config(config: dict = None) -> dict:
    """
    Get relevant configuration for factory methods
    @param config: global Configuration OR plugin class-specific configuration
    @return: plugin class-specific configuration
    """
    from ovos_plugin_manager.utils.config import get_plugin_config
    config = config or Configuration()
    if "listener" in config and "VAD" not in config:
        config = get_plugin_config(config, "listener")
    if "VAD" in config:
        config = get_plugin_config(config, "VAD")
    return config


class OVOSVADFactory:

    @staticmethod
    def get_class(config=None):
        """Factory method to get a VAD engine class based on configuration.

        The configuration file ``mycroft.conf`` contains a ``vad`` section with
        the name of a VAD module to be read by this method.

        "VAD": {
            "module": <engine_name>
        }
        """
        config = get_vad_config(config)
        vad_module = config.get("module")
        if not vad_module:
            raise ValueError(f"VAD Plugin not configured in: {config}")
        if vad_module == "dummy":
            return VADEngine
        return load_vad_plugin(vad_module)

    @classmethod
    def create(cls, config=None):
        """Factory method to create a VAD engine based on configuration.

        The configuration file ``mycroft.conf`` contains a ``VAD`` section with
        the name of a VAD module to be read by this method.

        "VAD": {
            "module": <engine_name>
        }
        """
        config = config or Configuration()
        if "listener" in config:
            config = config["listener"]
        if "VAD" in config:
            config = config["VAD"]
        plugin = config.get("module")
        if not plugin:
            raise ValueError(f"VAD Plugin not configured in: {config}")

        plugin_config = config.get(plugin, {})
        fallback = plugin_config.get("fallback_module")

        try:
            clazz = OVOSVADFactory.get_class(config)
            return clazz(plugin_config)
        except Exception:
            LOG.exception(f'VAD plugin {plugin} could not be loaded!')
            if fallback in config and fallback != plugin:
                LOG.info(f"Attempting to load fallback plugin instead: {fallback}")
                config["module"] = fallback
                return cls.create(config)
            raise
