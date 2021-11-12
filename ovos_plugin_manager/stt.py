from ovos_plugin_manager.utils import load_plugin, find_plugins, PluginTypes
from ovos_utils.configuration import read_mycroft_config
from ovos_utils.log import LOG
from ovos_plugin_manager.templates.stt import STT, StreamingSTT, StreamThread


def find_stt_plugins():
    return find_plugins(PluginTypes.STT)


def load_stt_plugin(module_name):
    """Wrapper function for loading stt plugin.

    Arguments:
        module_name (str): Mycroft stt module name from config
    Returns:
        class: STT plugin class
    """
    return load_plugin(module_name, PluginTypes.STT)


class OVOSSTTFactory:
    """ replicates the base mycroft class, but uses only OPM enabled plugins"""
    MAPPINGS = {
        #    "mycroft": MycroftSTT,
        "google": "ovos-stt-plugin-chromium",
        #    "google_cloud": GoogleCloudSTT,
        #    "google_cloud_streaming": GoogleCloudStreamingSTT,
        #    "wit": WITSTT,
        #    "ibm": IBMSTT,
        #    "kaldi": KaldiSTT,
        #    "bing": BingSTT,
        #    "govivace": GoVivaceSTT,
        #    "houndify": HoundifySTT,
        #    "deepspeech_server": DeepSpeechServerSTT,
        #    "deepspeech_stream_server": DeepSpeechStreamServerSTT,
        #    "mycroft_deepspeech": MycroftDeepSpeechSTT,
        #    "yandex": YandexSTT
        "vosk": "ovos-stt-plugin-vosk",
        "vosk_streaming": "ovos-stt-plugin-vosk-streaming"
    }

    @staticmethod
    def get_class(config=None):
        """Factory method to get a STT engine class based on configuration.

        The configuration file ``mycroft.conf`` contains a ``stt`` section with
        the name of a STT module to be read by this method.

        "stt": {
            "module": <engine_name>
        }
        """
        config = config or get_stt_config()
        stt_module = config["module"]
        if stt_module == "dummy":
            return STT
        if stt_module in OVOSSTTFactory.MAPPINGS:
            stt_module = OVOSSTTFactory.MAPPINGS[stt_module]
        return load_stt_plugin(stt_module)

    @staticmethod
    def create(config=None):
        """Factory method to create a STT engine based on configuration.

        The configuration file ``mycroft.conf`` contains a ``stt`` section with
        the name of a STT module to be read by this method.

        "stt": {
            "module": <engine_name>
        }
        """
        try:
            clazz = OVOSSTTFactory.get_class(config)
            return clazz()
        except Exception:
            LOG.exception('The selected STT plugin could not be loaded!')
            raise


def get_stt_config(config=None):
    config = config or read_mycroft_config()
    lang = config.get("lang", "en-us")
    if "stt" in config:
        config = config["stt"]
    stt_module = config.get('module', 'google')
    stt_config = config.get(stt_module, {})
    stt_config["lang"] = stt_config.get('lang') or lang
    return stt_config
