from ovos_plugin_manager.utils import load_plugin, find_plugins, PluginTypes
from ovos_utils.log import LOG


def find_microphone_plugins():
    return find_plugins(PluginTypes.MIC)


def load_microphone_plugin(module_name):
    return load_plugin(module_name, PluginTypes.MIC)


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
        config = get_microphone_config(config)
        microphone_module = config.get("module")
        return load_microphone_plugin(microphone_module)

    @staticmethod
    def create(config=None):
        """Factory method to create a microphone engine based on configuration.

        The configuration file ``mycroft.conf`` contains a ``microphone`` section with
        the name of a microphone module to be read by this method.

        "microphone": {
            "module": <engine_name>
        }
        """
        microphone_config = get_microphone_config(config)
        microphone_module = microphone_config.get('module')
        try:
            clazz = OVOSMicrophoneFactory.get_class(microphone_config)
            # Note that configuration is expanded for this class of plugins
            # since they are dataclasses and don't have the same init signature
            # as other plugin types
            microphone_config.pop('lang')
            microphone_config.pop('module')
            microphone = clazz(**microphone_config)
            LOG.debug(f'Loaded microphone plugin {microphone_module}')
        except Exception:
            LOG.exception('The selected microphone plugin could not be loaded.')
            raise
        return microphone


def get_microphone_config(config=None):
    from ovos_plugin_manager.utils.config import get_plugin_config
    return get_plugin_config(config, "microphone")
