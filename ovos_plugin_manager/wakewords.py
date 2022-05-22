from ovos_plugin_manager.utils import load_plugin, find_plugins, PluginTypes
from ovos_utils.configuration import read_mycroft_config
from ovos_utils.log import LOG
from ovos_plugin_manager.templates.hotwords import HotWordEngine


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
        "dummy": "ovos-ww-plugin-dummy",
        "pocketsphinx": "ovos-ww-plugin-pocketsphinx",
        "precise": "ovos-ww-plugin-precise",
        "snowboy": "ovos-ww-plugin-snowboy",
        "porcupine": "porcupine_wakeword_plug"
    }

    @staticmethod
    def get_class(hotword, config=None):
        """Factory method to get a TTS engine class based on configuration.

        The configuration file ``mycroft.conf`` contains a ``tts`` section with
        the name of a TTS module to be read by this method.

        "tts": {
            "module": <engine_name>
        }
        """
        config = get_hotwords_config(config)
        if hotword not in config:
            return HotWordEngine
        ww_module = config["module"]
        if ww_module in OVOSWakeWordFactory.MAPPINGS:
            ww_module = OVOSWakeWordFactory.MAPPINGS[ww_module]
        return load_wake_word_plugin(ww_module)

    @staticmethod
    def load_module(module, hotword, config, lang, loop):
        LOG.info(f'Loading "{hotword}" wake word via {module}')
        if module in OVOSWakeWordFactory.MAPPINGS:
            module = OVOSWakeWordFactory.MAPPINGS[module]

        clazz = load_wake_word_plugin(module)
        if clazz is None:
            raise ValueError(f'Wake Word plugin {module} not found')
        LOG.info(f'Loaded the Wake Word plugin {module}')

        return clazz(hotword, config, lang=lang)

    @classmethod
    def create_hotword(cls, hotword="hey mycroft", config=None,
                       lang="en-us", loop=None):
        config = get_hotwords_config(config)
        config = config.get(hotword) or config["hey mycroft"]
        module = config.get("module", "pocketsphinx")
        return cls.load_module(module, hotword, config, lang, loop)


def get_hotwords_config(config=None):
    config = config or read_mycroft_config()
    lang = config.get("lang", "en-us")
    if "hotwords" in config:
        config = config["hotwords"]
        for ww in config:
            if not config[ww].get("lang"):
                config[ww]["lang"] = lang
    return config
