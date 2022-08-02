from ovos_plugin_manager.utils import normalize_lang, load_plugin, find_plugins, PluginTypes, PluginConfigTypes
from ovos_config import Configuration
from ovos_utils.log import LOG
from ovos_plugin_manager.templates.hotwords import HotWordEngine


def find_wake_word_plugins():
    return find_plugins(PluginTypes.WAKEWORD)


def get_wake_word_config_examples(module_name):
    cfgs = load_plugin(module_name + ".config", PluginConfigTypes.WAKEWORD) or {}
    return {normalize_lang(lang): v for lang, v in cfgs.items()}


def get_wake_word_lang_config_examples(lang, include_dialects=False):
    lang = normalize_lang(lang)
    configs = {}
    for plug in find_wake_word_plugins():
        configs[plug] = []
        confs = get_wake_word_config_examples(plug)
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


def get_wake_word_supported_langs():
    configs = {}
    for plug in find_wake_word_plugins():
        confs = get_wake_word_config_examples(plug)
        for lang, cfgs in confs.items():
            if confs:
                if lang not in configs:
                    configs[lang] = []
                configs[lang].append(plug)
    return configs


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
        try:
            return cls.load_module(module, hotword, config, lang, loop)
        except:
            LOG.error(f"failed to created hotword: {config}")
            raise


def get_hotwords_config(config=None):
    config = config or Configuration()
    lang = config.get("lang", "en-us")
    if "hotwords" in config:
        config = config["hotwords"]
        for ww in config:
            if not config[ww].get("lang"):
                config[ww]["lang"] = lang
    return config
