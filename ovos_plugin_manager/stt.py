from ovos_plugin_manager.utils import normalize_lang, \
    PluginTypes, PluginConfigTypes
from ovos_config import Configuration
from ovos_plugin_manager.utils.config import get_valid_plugin_configs, \
    sort_plugin_configs, get_plugin_config
from ovos_utils.log import LOG, log_deprecation
from ovos_plugin_manager.templates.stt import STT, StreamingSTT, StreamThread


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


def find_stt_plugins() -> dict:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.STT)


def load_stt_plugin(module_name: str) -> type(STT):
    """
    Get an uninstantiated class for the requested module_name
    @param module_name: Plugin entrypoint name to load
    @return: Uninstantiated class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.STT)


def get_stt_configs() -> dict:
    """
    Get a dict of plugin names to valid STT configuration
    @return: dict plugin name to dict of str lang to list of dict valid configs
    """
    from ovos_plugin_manager.utils.config import load_configs_for_plugin_type
    return load_configs_for_plugin_type(PluginTypes.STT)


def get_stt_module_configs(module_name: str) -> dict:
    """
    Get a dict of lang to list of valid config dicts for a specific plugin
    @param module_name: name of plugin to get configurations for
    @return: {lang: [list of config dicts]}
    """
    from ovos_plugin_manager.utils.config import load_plugin_configs
    configs = load_plugin_configs(module_name, PluginConfigTypes.STT, True)
    # let's sort by priority key
    for k, v in configs.items():
        configs[k] = sorted(v, key=lambda c: c.get("priority", 60))
    return configs


def get_stt_lang_configs(lang: str, include_dialects: bool = False) -> dict:
    """
    Get a dict of plugins names to sorted list of valid configurations
    @param lang: language to get configurations for (i.e. en, en-US)
    @param include_dialects: If true, include configs for other locales
        (i.e. include en-GB configs for lang=en-US)
    @return: dict plugin name to list of valid configs sorted by priority
    """
    from ovos_plugin_manager.utils.config import get_plugin_language_configs
    matched_configs = get_plugin_language_configs(PluginTypes.STT, lang,
                                                  include_dialects)
    return sort_plugin_configs(matched_configs)


def get_stt_supported_langs() -> dict:
    """
    Get a dict of languages to valid configuration options
    @return: dict lang to list of plugins that support that lang
    """
    from ovos_plugin_manager.utils.config import get_plugin_supported_languages
    return get_plugin_supported_languages(PluginTypes.STT)


def get_stt_config(config: dict = None, module: str = None) -> dict:
    """
    Get relevant configuration for factory methods
    @param config: global Configuration OR plugin class-specific configuration
    @param module: STT module to get configuration for
    @return: plugin class-specific configuration
    """
    from ovos_plugin_manager.utils.config import get_plugin_config
    stt_config = get_plugin_config(config, "stt", module)
    assert stt_config.get('lang') is not None, "expected lang but got None"
    return stt_config


class OVOSSTTFactory:
    """ replicates the base mycroft class, but uses only OPM enabled plugins"""
    MAPPINGS = {
        "mycroft": "ovos-stt-plugin-selene",
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
        config = get_stt_config(config)
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
        stt_config = get_stt_config(config)
        plugin = stt_config.get("module", "dummy")
        if plugin in OVOSSTTFactory.MAPPINGS:
            log_deprecation("Module mappings will be deprecated", "0.1.0")
            plugin = OVOSSTTFactory.MAPPINGS[plugin]
            stt_config = get_stt_config(config, plugin)
        try:
            clazz = OVOSSTTFactory.get_class(stt_config)
            return clazz(stt_config)
        except Exception:
            LOG.exception('The selected STT plugin could not be loaded!')
            raise
