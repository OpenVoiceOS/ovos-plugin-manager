from ovos_plugin_manager.utils import load_plugin, find_plugins, PluginTypes
from ovos_utils.configuration import read_mycroft_config
from ovos_utils.log import LOG


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
        #    "google": GoogleSTT,
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
        "vosk": "vosk_stt_plug",
        "vosk_streaming": "vosk_streaming_stt_plug"
    }

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
            config = config or read_mycroft_config().get("stt", {})
            stt_module = config.get("module", "mycroft")
            if stt_module in OVOSSTTFactory.MAPPINGS:
                stt_module = OVOSSTTFactory.MAPPINGS[stt_module]

            clazz = load_stt_plugin(stt_module)
            if clazz is None:
                raise ValueError(f'STT plugin {stt_module} not found')
            LOG.info(f'Loaded the STT plugin {stt_module}')
            return clazz()
        except Exception:
            # The STT backend failed to start. Report it and fall back to
            # default.
            LOG.exception('The selected STT plugin could not be loaded!')
            raise
