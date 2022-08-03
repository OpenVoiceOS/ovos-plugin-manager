from ovos_plugin_manager.utils import load_plugin, normalize_lang, find_plugins, PluginTypes, PluginConfigTypes
from ovos_config import Configuration
from ovos_utils.log import LOG
from ovos_plugin_manager.templates.stt import STT, StreamingSTT, StreamThread


def find_stt_plugins():
    return find_plugins(PluginTypes.STT)


def get_stt_configs():
    return {plug: get_stt_module_configs(plug)
            for plug in find_stt_plugins()}


def get_stt_module_configs(module_name):
    # STT plugins return {lang: [list of config dicts]}
    cfgs = load_plugin(module_name + ".config", PluginConfigTypes.STT) or {}
    return {normalize_lang(lang): v for lang, v in cfgs.items()}


def get_stt_lang_configs(lang, include_dialects=False):
    lang = normalize_lang(lang)
    configs = {}
    for plug in find_stt_plugins():
        configs[plug] = []
        confs = get_stt_module_configs(plug)
        if include_dialects:
            lang = lang.split("-")[0]
            for l in confs:
                if l.startswith(lang):
                    configs[plug] += confs[l]
        elif lang in confs:
            configs[plug] += confs[lang]
        elif f"{lang}-{lang}" in confs:
            configs[plug] += confs[f"{lang}-{lang}"]
    return {k: v for k, v in configs.items() if v}


def get_stt_supported_langs():
    configs = {}
    for plug in find_stt_plugins():
        confs = get_stt_module_configs(plug)
        for lang, cfgs in confs.items():
            if confs:
                if lang not in configs:
                    configs[lang] = []
                configs[lang].append(plug)
    return configs


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
        "dummy": "ovos-stt-plugin-dummy",
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
        config = config or get_stt_config()
        plugin = config["module"]
        plugin_config = config.get(plugin) or {}
        try:
            clazz = OVOSSTTFactory.get_class(config)
            return clazz(plugin_config)
        except Exception:
            LOG.exception('The selected STT plugin could not be loaded!')
            raise


def get_stt_config(config=None):
    config = config or Configuration()
    lang = config.get("lang", "en-us")
    if "stt" in config:
        config = config["stt"]
    stt_module = config.get('module', 'dummy')
    stt_config = config.get(stt_module, {})
    stt_config["lang"] = stt_config.get('lang') or lang
    stt_config["module"] = stt_module
    return stt_config
