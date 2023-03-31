import json
import os
from ovos_plugin_manager.templates.tts import TTS, TTSContext, TTSValidator, TextToSpeechCache, ConcatTTS, RemoteTTS
from ovos_plugin_manager.utils import load_plugin, find_plugins, PluginTypes, normalize_lang, PluginConfigTypes
from ovos_plugin_manager.utils.config import get_valid_plugin_configs, sort_plugin_configs
from ovos_utils.log import LOG
from ovos_utils.xdg_utils import xdg_data_home
from hashlib import md5
import json


def get_voice_id(plugin_name, lang, tts_config):
    tts_hash = md5(json.dumps(tts_config, sort_keys=True).encode("utf-8")).hexdigest()
    return f"{plugin_name}_{lang}_{tts_hash}"


def scan_voices():
    voice_ids = {}
    for lang in get_tts_supported_langs():
        VOICES_FOLDER = f"{xdg_data_home()}/OPM/voice_configs/{lang}"
        os.makedirs(VOICES_FOLDER, exist_ok=True)
        for plug, voices in get_tts_lang_configs(lang, include_dialects=True).items():
            for voice in voices:
                voiceid = get_voice_id(plug, lang, voice)
                if "meta" not in voice:
                    voice["meta"] = {}
                noise = ["priority", "display_name", "offline", "gender"]
                for k in noise:
                    if k in voice:
                        voice["meta"][k] = voice.pop(k)
                voice["module"] = plug
                with open(f"{VOICES_FOLDER}/{voiceid}.json", "w") as f:
                    json.dump(voice, f, indent=4, ensure_ascii=False)
                voice_ids[voiceid] = voice
    return voice_ids


def get_voices(scan=False):
    if scan:
        scan_voices()
    voice_ids = {}
    for lang in get_tts_supported_langs():
        VOICES_FOLDER = f"{xdg_data_home()}/OPM/voice_configs/{lang}"
        for voice in os.listdir(VOICES_FOLDER):
            with open(f"{VOICES_FOLDER}/{voice}") as f:
                voice_ids[voice] = json.load(f)
    return voice_ids


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


def get_tts_configs() -> dict:
    """
    Get a dict of plugin names to valid TTS configuration
    @return: dict plugin name to dict of str lang to list of dict valid configs
    """
    return {plug: get_tts_module_configs(plug)
            for plug in find_tts_plugins()}


def get_tts_module_configs(module_name: str) -> dict:
    """
    Get a dict of lang to list of valid config dicts for a specific plugin
    @param module_name: name of plugin to get configurations for
    @return: {lang: [list of config dicts]}
    """
    cfgs = load_plugin(module_name + ".config", PluginConfigTypes.TTS) or {}
    configs = {normalize_lang(lang): v for lang, v in cfgs.items()}
    # let's sort by priority key
    for k, v in configs.items():
        configs[k] = sorted(v, key=lambda c: c.get("priority", 60))
    return configs


def get_tts_lang_configs(lang, include_dialects=False):
    """
    Get a dict of plugins names to sorted list of valid configurations
    @param lang: language to get configurations for (i.e. en, en-US)
    @param include_dialects: If true, include configs for other locales
        (i.e. include en-GB configs for lang=en-US)
    @return: dict plugin name to list of valid configs sorted by priority
    """
    lang = normalize_lang(lang)
    matched_configs = {}
    for plug in find_tts_plugins():
        matched_configs[plug] = []
        confs = get_tts_module_configs(plug)
        matched_configs[plug] = get_valid_plugin_configs(confs, lang,
                                                         include_dialects)
    return sort_plugin_configs(matched_configs)


def get_tts_supported_langs():
    """
    Get a dict of languages to valid configuration options
    @return: dict lang to list of plugins that support that lang
    """
    configs = {}
    for plug in find_tts_plugins():
        confs = get_tts_module_configs(plug)
        for lang, cfgs in confs.items():
            if confs:
                if lang not in configs:
                    configs[lang] = []
                configs[lang].append(plug)
    return configs


class OVOSTTSFactory:
    """ replicates the base mycroft class, but uses only OPM enabled plugins"""
    MAPPINGS = {
        "dummy": "ovos-tts-plugin-dummy",
        "mimic": "ovos-tts-plugin-mimic",
        "mimic2": "ovos-tts-plugin-mimic2",
        "mimic3": "ovos-tts-plugin-mimic3",
        "google": "ovos-tts-plugin-google-tx",
        "marytts": "ovos-tts-plugin-marytts",
        # "fatts": FATTS,
        # "festival": Festival,
        "espeak": "ovos_tts_plugin_espeakng",
        # "spdsay": SpdSay,
        # "watson": WatsonTTS,
        # "bing": BingTTS,
        "responsive_voice": "ovos-tts-plugin-responsivevoice",
        # "yandex": YandexTTS,
        "polly": "ovos-tts-plugin-polly",
        # "mozilla": MozillaTTS,
        "pico": "ovos-tts-plugin-pico"
    }

    @staticmethod
    def get_class(config=None):
        """Factory method to get a TTS engine class based on configuration.

        The configuration file ``mycroft.conf`` contains a ``tts`` section with
        the name of a TTS module to be read by this method.

        "tts": {
            "module": <engine_name>
        }
        """
        config = config or get_tts_config()
        tts_module = config.get("module") or "dummy"
        if tts_module in OVOSTTSFactory.MAPPINGS:
            tts_module = OVOSTTSFactory.MAPPINGS[tts_module]
        return load_tts_plugin(tts_module)

    @staticmethod
    def create(config=None):
        """Factory method to create a TTS engine based on configuration.

        The configuration file ``mycroft.conf`` contains a ``tts`` section with
        the name of a TTS module to be read by this method.

        "tts": {
            "module": <engine_name>
        }
        """
        tts_config = get_tts_config(config)
        tts_lang = tts_config["lang"]
        tts_module = tts_config.get('module', 'dummy')
        try:
            clazz = OVOSTTSFactory.get_class(tts_config)
            if clazz:
                LOG.info(f'Found plugin {tts_module}')
                tts = clazz(tts_lang, tts_config)
                tts.validator.validate()
                LOG.info(f'Loaded plugin {tts_module}')
            else:
                raise FileNotFoundError("unknown plugin")
        except Exception:
            plugins = find_tts_plugins()
            modules = ",".join(plugins.keys())
            LOG.exception(f'The TTS plugin "{tts_module}" could not be loaded.\nAvailable modules: {modules}')
            raise
        return tts


def get_tts_config(config=None):
    from ovos_plugin_manager.utils.config import get_plugin_config
    return get_plugin_config(config, 'tts')


if __name__ == "__main__":
    print(get_voices())

