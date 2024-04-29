import json
import os
from ovos_plugin_manager.templates.tts import TTS, TTSContext, TTSValidator, \
    TextToSpeechCache, ConcatTTS, RemoteTTS
from ovos_plugin_manager.utils import PluginTypes, normalize_lang, \
    PluginConfigTypes
from ovos_plugin_manager.utils.config import get_valid_plugin_configs, \
    sort_plugin_configs, get_plugin_config
from ovos_utils.log import LOG, log_deprecation
from ovos_utils.xdg_utils import xdg_data_home
from hashlib import md5


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


def find_tts_plugins() -> dict:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.TTS)


def load_tts_plugin(module_name: str) -> type(TTS):
    """
    Get an uninstantiated class for the requested module_name
    @param module_name: Plugin entrypoint name to load
    @return: Uninstantiated class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.TTS)


def get_tts_configs() -> dict:
    """
    Get a dict of plugin names to valid TTS configuration
    @return: dict plugin name to dict of str lang to list of dict valid configs
    """
    from ovos_plugin_manager.utils.config import load_configs_for_plugin_type
    return load_configs_for_plugin_type(PluginTypes.TTS)


def get_tts_module_configs(module_name: str) -> dict:
    """
    Get a dict of lang to list of valid config dicts for a specific plugin
    @param module_name: name of plugin to get configurations for
    @return: {lang: [list of config dicts]}
    """
    from ovos_plugin_manager.utils.config import load_plugin_configs
    configs = load_plugin_configs(module_name, PluginConfigTypes.TTS)
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
    from ovos_plugin_manager.utils.config import get_plugin_language_configs
    return get_plugin_language_configs(PluginTypes.TTS, lang, include_dialects)


def get_tts_supported_langs():
    """
    Get a dict of languages to valid configuration options
    @return: dict lang to list of plugins that support that lang
    """
    from ovos_plugin_manager.utils.config import get_plugin_supported_languages
    return get_plugin_supported_languages(PluginTypes.TTS)


def get_tts_config(config: dict = None, module: str = None) -> dict:
    """
    Get relevant configuration for factory methods
    @param config: global Configuration OR plugin class-specific configuration
    @param module: TTS module to get configuration for
    @return: plugin class-specific configuration
    """
    from ovos_plugin_manager.utils.config import get_plugin_config
    return get_plugin_config(config, 'tts', module)


def get_voice_id(plugin_name, lang, tts_config):
    tts_hash = md5(json.dumps(tts_config,
                              sort_keys=True).encode("utf-8")).hexdigest()
    return f"{plugin_name}_{lang}_{tts_hash}"


def scan_voices():
    voice_ids = {}
    for lang in get_tts_supported_langs():
        VOICES_FOLDER = f"{xdg_data_home()}/OPM/voice_configs/{lang}"
        os.makedirs(VOICES_FOLDER, exist_ok=True)
        for plug, voices in get_tts_lang_configs(lang,
                                                 include_dialects=True).items():
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
        tts_module = tts_config.get('module', 'dummy')
        if tts_module in OVOSTTSFactory.MAPPINGS:
            # The configured module maps to a valid plugin; get configuration
            # again to make sure any module-specific config/overrides are loaded
            log_deprecation("Module mappings will be deprecated", "0.1.0")
            tts_module = OVOSTTSFactory.MAPPINGS[tts_module]
            tts_config = get_tts_config(config, tts_module)
        try:
            clazz = OVOSTTSFactory.get_class(tts_config)
            if clazz:
                LOG.info(f'Found plugin {tts_module}')
                tts = clazz(config=tts_config)
                tts._plugin_id = tts_module
                tts.validator.validate()
                LOG.info(f'Loaded plugin {tts_module}')
            else:
                raise RuntimeError(f"unknown plugin: {tts_module}")
        except Exception:
            plugins = find_tts_plugins()
            modules = ",".join(plugins.keys())
            LOG.exception(f'The TTS plugin "{tts_module}" could not be loaded.'
                          f'\nAvailable modules: {modules}')
            raise
        return tts
