from ovos_plugin_manager.utils import load_plugin, find_plugins, PluginTypes, PluginConfigTypes
from ovos_config import Configuration
from ovos_utils.log import LOG
from ovos_plugin_manager.templates.vad import VADEngine


def find_vad_plugins():
    return find_plugins(PluginTypes.VAD)


def get_vad_configs():
    return {plug: get_vad_module_configs(plug)
            for plug in find_vad_plugins()}


def get_vad_module_configs(module_name):
    # VAD plugins return [list of config dicts] or {module_name: [list of config dicts]}
    cfgs = load_plugin(module_name + ".config", PluginConfigTypes.VAD)
    return {module_name: cfgs} if isinstance(cfgs, list) else cfgs


def load_vad_plugin(module_name):
    """Wrapper function for loading vad plugin.

    Arguments:
        module_name (str): vad module name from config
    Returns:
        class: VAD plugin class
    """
    return load_plugin(module_name, PluginTypes.VAD)


class OVOSVADFactory:
    """ replicates the base mycroft class, but uses only OPM enabled plugins"""
    MAPPINGS = {
        "silero": "ovos-vad-plugin-silero",
        "webrtcvad": "ovos-vad-plugin-webrtcvad"
    }

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
        if vad_module in OVOSVADFactory.MAPPINGS:
            vad_module = OVOSVADFactory.MAPPINGS[vad_module]
        return load_vad_plugin(vad_module)

    @staticmethod
    def create(config=None):
        """Factory method to create a VAD engine based on configuration.

        The configuration file ``mycroft.conf`` contains a ``VAD`` section with
        the name of a VAD module to be read by this method.

        "VAD": {
            "module": <engine_name>
        }
        """
        vad_config = get_vad_config(config)
        plugin = vad_config.get("module")
        if not plugin:
            raise ValueError(f"VAD Plugin not configured in: {vad_config}")
        try:
            clazz = OVOSVADFactory.get_class(vad_config)
            return clazz(vad_config)
        except Exception:
            LOG.exception(f'VAD plugin {plugin} could not be loaded!')
            raise


def get_vad_config(config=None):
    """
    Get the VAD configuration, including `module` and module-specific config
    @param config: Configuration dict to parse (default Configuration())
    @return: dict containing `module` and module-specific configuration
    """
    from ovos_plugin_manager.utils.config import get_plugin_config
    config = config or Configuration()
    if "listener" in config and "VAD" not in config:
        config = get_plugin_config(config, "listener")
    if "VAD" in config:
        config = get_plugin_config(config, "VAD")
    return config

