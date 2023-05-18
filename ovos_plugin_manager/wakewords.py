import json
import os
from hashlib import md5
from ovos_utils.log import LOG
from ovos_utils.xdg_utils import xdg_data_home

from ovos_plugin_manager.templates.hotwords import HotWordEngine
from ovos_plugin_manager.utils import normalize_lang, load_plugin, find_plugins, PluginTypes, PluginConfigTypes


def get_ww_id(plugin_name, ww_name, ww_config):
    ww_hash = md5(json.dumps(ww_config, sort_keys=True).encode("utf-8")).hexdigest()
    return f"{plugin_name}_{ww_name}_{ww_hash}"


def scan_wws():
    ww_ids = {}
    raise NotImplementedError("plugin wake word metadata reporting is WIP")
    return ww_ids


def get_wws(scan=False):
    if scan:
        scan_wws()
    ww_ids = {}
    for lang in get_ww_supported_langs():
        WW_FOLDER = f"{xdg_data_home()}/OPM/ww_configs/{lang}"
        for voice in os.listdir(WW_FOLDER):
            with open(f"{WW_FOLDER}/{voice}") as f:
                ww_ids[voice] = json.load(f)
    return ww_ids


def find_wake_word_plugins():
    return find_plugins(PluginTypes.WAKEWORD)


def get_ww_configs():
    configs = {}
    for plug in find_wake_word_plugins():
        configs[plug] = get_ww_module_configs(plug)
    return configs


def get_ww_module_configs(module_name):
    # WW plugins return {ww_name: [list of config dicts]}
    return load_plugin(module_name + ".config", PluginConfigTypes.WAKEWORD) or {}


def get_ww_lang_configs(lang, include_dialects=False):
    lang = normalize_lang(lang)
    configs = {}
    for plug in find_wake_word_plugins():
        configs[plug] = []
        confs = get_ww_module_configs(plug)
        for ww_name, ww_conf in confs.items():
            ww_lang = ww_conf.get("lang")
            if not ww_lang:
                continue
            if include_dialects:
                lang = lang.split("-")[0]
                if ww_lang.startswith(lang):
                    configs[plug] += ww_conf
            elif lang == ww_lang or f"{lang}-{lang}" == ww_lang:
                configs[plug] += ww_conf
    return {k: v for k, v in configs.items() if v}


def get_ww_supported_langs():
    configs = {}
    for plug in find_wake_word_plugins():
        confs = get_ww_module_configs(plug)
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
        hotword_config = get_hotwords_config(config)
        if hotword not in hotword_config:
            LOG.warning(f"{hotword} not in {hotword_config}! "
                        f"Returning base HotWordEngine")
            return HotWordEngine
        ww_module = hotword_config[hotword]["module"]
        if ww_module in OVOSWakeWordFactory.MAPPINGS:
            ww_module = OVOSWakeWordFactory.MAPPINGS[ww_module]
        return load_wake_word_plugin(ww_module)

    @staticmethod
    def load_module(module, hotword, hotword_config, lang, loop):
        # config here is config['hotwords'][module]
        LOG.info(f'Loading "{hotword}" wake word via {module} with '
                 f'config: {hotword_config}')
        config = {"lang": lang, "hotwords": {hotword: hotword_config}}
        clazz = OVOSWakeWordFactory.get_class(module, config)
        if clazz is None:
            raise ImportError(f'Wake Word plugin {module} failed to load')
        LOG.info(f'Loaded the Wake Word plugin {module}')
        return clazz(hotword, hotword_config, lang=lang)

    @classmethod
    def create_hotword(cls, hotword="hey mycroft", config=None,
                       lang="en-us", loop=None):
        ww_configs = get_hotwords_config(config)
        if hotword not in ww_configs:
            LOG.warning(f"replace ` ` in {hotword} with `_`")
            hotword = hotword.replace(' ', '_')
        ww_config = ww_configs.get(hotword)
        module = ww_config.get("module", "pocketsphinx")
        try:
            return cls.load_module(module, hotword, ww_config, lang, loop)
        except Exception as e:
            LOG.error(f"Failed to load hotword: {hotword} - {module}")
            LOG.exception(e)
            fallback_ww = ww_config.get("fallback_ww")
            if fallback_ww in ww_configs and fallback_ww != hotword:
                LOG.info(f"Attempting to load fallback ww instead: {fallback_ww}")
                return cls.create_hotword(fallback_ww, config, lang, loop)
            raise


def get_hotwords_config(config=None):
    from ovos_plugin_manager.utils.config import get_plugin_config
    return get_plugin_config(config, "hotwords")
