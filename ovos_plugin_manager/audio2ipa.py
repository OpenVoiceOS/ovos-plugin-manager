from ovos_plugin_manager.utils import normalize_lang, load_plugin, find_plugins, PluginTypes, PluginConfigTypes
from ovos_plugin_manager.templates.audio2ipa import Audio2IPA
from ovos_utils.log import LOG


def find_audio2ipa_plugins():
    return find_plugins(PluginTypes.AUDIO2IPA)


def load_audio2ipa_plugin(module_name):
    return load_plugin(module_name, PluginTypes.AUDIO2IPA)


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


def get_audio2ipa_config(config=None):
    from ovos_plugin_manager.utils.config import get_plugin_config
    return get_plugin_config(config, "audio2ipa")
