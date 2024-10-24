from ovos_config import Configuration
from ovos_utils.log import LOG, deprecated

from ovos_plugin_manager.templates.microphone import Microphone
from ovos_plugin_manager.utils import PluginTypes


def find_microphone_plugins() -> dict:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.MIC)


def load_microphone_plugin(module_name: str) -> type(Microphone):
    """
    Get an uninstantiated class for the requested module_name
    @param module_name: Plugin entrypoint name to load
    @return: Uninstantiated class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.MIC)


@deprecated("get_microphone_config is deprecated, use Configuration() directly", "1.0.0")
def get_microphone_config(config=None):
    """
    Get relevant configuration for factory methods
    @param config: global Configuration OR plugin class-specific configuration
    @return: plugin class-specific configuration
    """
    from ovos_plugin_manager.utils.config import get_plugin_config
    return get_plugin_config(config, "microphone")


class OVOSMicrophoneFactory:

    @staticmethod
    def get_class(config=None):
        """Factory method to get a microphone engine class based on configuration.

        The configuration file ``mycroft.conf`` contains a ``microphone`` section with
        the name of a microphone module to be read by this method.

        "microphone": {
            "module": <engine_name>
        }
        """
        config = config or Configuration().get("listener", {}).get("microphone", {})
        microphone_module = config.get("module")
        return load_microphone_plugin(microphone_module)

    @classmethod
    def create(cls, config=None):
        """Factory method to create a microphone engine based on configuration.

        The configuration file ``mycroft.conf`` contains a ``microphone`` section with
        the name of a microphone module to be read by this method.

        "microphone": {
            "module": <engine_name>
        }
        """
        config = config or Configuration().get("listener", {}).get("microphone", {})
        microphone_module = config.get('module')
        microphone_config = config.get(microphone_module, {})
        fallback = microphone_config.get("fallback_module")
        try:
            clazz = OVOSMicrophoneFactory.get_class(config)
            if fallback:
                microphone_config.pop('fallback_module')
            microphone = clazz(**microphone_config)
            LOG.debug(f'Loaded microphone plugin {microphone_module}')
        except Exception:
            LOG.exception('The selected microphone plugin could not be loaded.')
            if fallback in config and fallback != microphone_module:
                LOG.info(f"Attempting to load fallback plugin instead: {fallback}")
                config["module"] = fallback
                return cls.create(config)
            raise
        return microphone
