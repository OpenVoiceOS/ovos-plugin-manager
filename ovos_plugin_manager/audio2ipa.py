from typing import Optional
from ovos_plugin_manager.utils import normalize_lang, PluginTypes, PluginConfigTypes
from ovos_plugin_manager.templates.audio2ipa import Audio2IPA
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


def find_audio2ipa_plugins() -> dict:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.AUDIO2IPA)


def load_audio2ipa_plugin(module_name: str) -> type(Audio2IPA):
    """
    Get an uninstantiated class for the requested module_name
    @param module_name: Plugin entrypoint name to load
    @return: Uninstantiated class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.AUDIO2IPA)


def get_audio2ipa_config(config: Optional[dict] = None) -> dict:
    """
    Get relevant configuration for factory methods
    @param config: global Configuration OR plugin class-specific configuration
    @return: plugin class-specific configuration
    """
    from ovos_plugin_manager.utils.config import get_plugin_config
    return get_plugin_config(config, "audio2ipa")


class OVOSAudio2IPAFactory:
    @staticmethod
    def get_class(config=None):
        """Factory method to get a Audio2IPA engine class based on configuration.

        The configuration file ``mycroft.conf`` contains a ``audio2ipa`` section with
        the name of a Audio2IPA module to be read by this method.

        "audio2ipa": {
            "module": <engine_name>
        }
        """
        config = get_audio2ipa_config(config)
        audio2ipa_module = config.get("module")
        return load_audio2ipa_plugin(audio2ipa_module)

    @staticmethod
    def create(config=None):
        """Factory method to create a Audio2IPA engine based on configuration.

        The configuration file ``mycroft.conf`` contains a ``audio2ipa`` section with
        the name of a Audio2IPA module to be read by this method.

        "audio2ipa": {
            "module": <engine_name>
        }
        """
        audio2ipa_config = get_audio2ipa_config(config)
        audio2ipa_module = audio2ipa_config.get('module', 'dummy')
        try:
            clazz = OVOSAudio2IPAFactory.get_class(audio2ipa_config)
            audio2ipa = clazz(audio2ipa_config)
            LOG.debug(f'Loaded plugin {audio2ipa_module}')
        except Exception:
            LOG.debug('The selected Audio2IPA plugin could not be loaded.')
            raise
        return audio2ipa
