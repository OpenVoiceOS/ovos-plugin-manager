from ovos_plugin_manager.utils import load_plugin, find_plugins, PluginTypes
from ovos_plugin_manager.templates.tts import TTS
from ovos_utils.configuration import read_mycroft_config
from ovos_utils.log import LOG


def find_tts_plugins():
    return find_plugins(PluginTypes.TTS)


def load_tts_plugin(module_name):
    """Wrapper function for loading tts plugin.

    Arguments:
        (str) Mycroft tts module name from config
    Returns:
        class: found tts plugin class
    """
    return load_plugin(module_name, PluginTypes.TTS)


class OVOSTTSFactory:
    """ replicates the base mycroft class, but uses only OPM enabled plugins"""
    MAPPINGS = {
        "mimic": "ovos-tts-plugin-mimic",
        "mimic2": "ovos-tts-plugin-mimic2",
        "google": "ovos-tts-plugin-google-tx",
        # "marytts": MaryTTS,
        # "fatts": FATTS,
        # "festival": Festival,
        "espeak": "ovos_tts_plugin_espeakng",
        # "spdsay": SpdSay,
        # "watson": WatsonTTS,
        # "bing": BingTTS,
        "responsive_voice": "ovos-tts-plugin-responsivevoice",
        # "yandex": YandexTTS,
        "polly": "chatterbox_polly_tts",
        # "mozilla": MozillaTTS,
        # "dummy": DummyTTS
        "pico": "ovos-tts-plugin-pico"
    }

    @staticmethod
    def create(config=None):
        """Factory method to create a TTS engine based on configuration.

        The configuration file ``mycroft.conf`` contains a ``tts`` section with
        the name of a TTS module to be read by this method.

        "tts": {
            "module": <engine_name>
        }
        """
        config = config or read_mycroft_config()
        lang = config.get("lang", "en-us")
        if "tts" in config:
            config = config["tts"]
        tts_module = config.get('module', 'mimic')
        if tts_module == "dummy":
            return TTS()
        tts_config = config.get(tts_module, {})
        tts_lang = tts_config.get('lang', lang)
        try:
            if tts_module in OVOSTTSFactory.MAPPINGS:
                tts_module = OVOSTTSFactory.MAPPINGS[tts_module]
            clazz = load_tts_plugin(tts_module)
            if clazz is None:
                raise ValueError(f'TTS plugin {tts_module} not found')
            LOG.info(f'Loaded plugin {tts_module}')
            tts = clazz(tts_lang, tts_config)
            tts.validator.validate()
        except Exception:
            LOG.exception('The selected TTS plugin could not be loaded.')
            raise
        return tts
