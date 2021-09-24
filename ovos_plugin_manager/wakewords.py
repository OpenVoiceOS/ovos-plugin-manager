from ovos_plugin_manager.utils import load_plugin, find_plugins, PluginTypes
from ovos_utils.configuration import read_mycroft_config
from ovos_utils.log import LOG


def find_wake_word_plugins():
    return find_plugins(PluginTypes.WAKEWORD)


def load_wake_word_plugin(module_name):
    """Wrapper function for loading wake word plugin.

    Arguments:
        (str) Mycroft wake word module name from config
    """
    return load_plugin(module_name, PluginTypes.WAKEWORD)


class OVOSWakeWordFactory:
    """ replicates the base mycroft class, but uses only OPM enabled plugins"""
    MAPPINGS = {
        "pocketsphinx": "ovos-ww-plugin-pocketsphinx",
        "precise": "ovos-ww-plugin-precise",
        "snowboy": "ovos-ww-plugin-snowboy",
        "porcupine": "porcupine_wakeword_plug"
    }

    @staticmethod
    def load_module(module, hotword, config, lang, loop):
        LOG.info('Loading "{}" wake word via {}'.format(hotword, module))
        if module in OVOSWakeWordFactory.MAPPINGS:
            module = OVOSWakeWordFactory.MAPPINGS[module]

        clazz = load_wake_word_plugin(module)
        if clazz is None:
            raise ValueError(f'Wake Word plugin {module} not found')
        LOG.info(
            'Loaded the Wake Word plugin {}'.format(module))

        return clazz(hotword, config, lang=lang)

    @classmethod
    def create_hotword(cls, hotword="hey mycroft", config=None,
                       lang="en-us", loop=None):
        config = config or read_mycroft_config() or {}
        if "hotwords" in config:
            config = config["hotwords"]

        config = config.get(hotword) or config["hey mycroft"]

        module = config.get("module", "pocketsphinx")
        return cls.load_module(module, hotword, config, lang, loop)
