import json
import os
from hashlib import md5
from typing import Optional

from ovos_utils.lang import standardize_lang_tag
from ovos_utils.log import LOG
from ovos_utils.xdg_utils import xdg_data_home

from ovos_plugin_manager.templates.hotwords import HotWordEngine
from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes


def find_wake_word_plugins() -> dict:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.WAKEWORD)


def load_wake_word_plugin(module_name: str) -> type(HotWordEngine):
    """
    Get an uninstantiated class for the requested module_name
    @param module_name: Plugin entrypoint name to load
    @return: Uninstantiated class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.WAKEWORD)


def get_ww_configs() -> dict:
    """
    Get valid plugin configurations by plugin name
    @return: dict plugin names to list of dict configurations
    """
    from ovos_plugin_manager.utils.config import load_configs_for_plugin_type
    return load_configs_for_plugin_type(PluginTypes.WAKEWORD)


def get_ww_module_configs(module_name: str) -> dict:
    """
    Get valid configurations for the specified plugin
    @param module_name: plugin to get configuration for
    @return: dict configurations by ww name (if provided)
    """
    # WW plugins return {ww_name: [list of config dicts]}
    from ovos_plugin_manager.utils.config import load_plugin_configs
    return load_plugin_configs(module_name, PluginConfigTypes.WAKEWORD)


def get_ww_lang_configs(lang: str, include_dialects: bool = False) -> dict:
    """
    Get a dict of plugin names to list valid configurations for the requested
    lang.
    @param lang: Language to get configurations for
    @param include_dialects: consider configurations in different locales
    @return: dict {`plugin_name`: `valid_configs`]}
    """
    from ovos_plugin_manager.utils.config import get_plugin_language_configs
    return get_plugin_language_configs(PluginTypes.WAKEWORD, lang,
                                       include_dialects)


def get_ww_supported_langs() -> dict:
    """
    Return a dict of plugin names to list supported languages
    @return: dict plugin names to list supported languages
    """
    from ovos_plugin_manager.utils.config import get_plugin_supported_languages
    return get_plugin_supported_languages(PluginTypes.WAKEWORD)


def get_hotwords_config(config: dict = None) -> dict:
    """
    Get relevant configuration for factory methods
    @param config: global Configuration OR plugin class-specific configuration
    @return: plugin class-specific configuration
    """
    from ovos_plugin_manager.utils.config import get_plugin_config
    return get_plugin_config(config, "hotwords")


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


class OVOSWakeWordFactory:

    @staticmethod
    def get_class(hotword: str, config: Optional[dict] = None) -> type:
        """
        Get the plugin class for the specified hotword
        @param hotword: string hotword to load
        @param config: optional global configuration
        @return: Uninitialized hotword class
        """
        hotword_config = get_hotwords_config(config)
        if hotword not in hotword_config:
            LOG.warning(f"{hotword} not in {hotword_config}! "
                        f"Returning base HotWordEngine")
            return HotWordEngine
        ww_module = hotword_config[hotword]["module"]
        return load_wake_word_plugin(ww_module)

    @staticmethod
    def load_module(module: str, hotword: str, hotword_config: dict,
                    lang: str, loop=None) -> HotWordEngine:
        """
        Get an initialized HotWordEngine using the specified module and hotword
        @param module: hotword plugin to load (not parsed)
        @param hotword: string hotword to load
        @param hotword_config: configuration for the specified `hotword`.
            Equivalent to Configuration()['hotwords'][hotword]
        @param lang: BCP-47 language code of hotword
        @param loop: Unused
        @return: Initialized HotWordEngine
        """
        lang = standardize_lang_tag(lang)
        # config here is config['hotwords'][module]
        LOG.info(f'Loading "{hotword}" wake word via {module} with '
                 f'config: {hotword_config}')
        config = {"lang": lang, "hotwords": {hotword: hotword_config}}
        clazz = OVOSWakeWordFactory.get_class(hotword, config)
        if clazz is None:
            raise ImportError(f'Wake Word {hotword} with module {module} '
                              f'failed to load')
        LOG.info(f'Loaded the Wake Word {hotword} with module {module}')
        return clazz(hotword, hotword_config, lang=lang)

    @classmethod
    def create_hotword(cls, hotword: str = "hey mycroft",
                       config: Optional[dict] = None,
                       lang: str = "en-US", loop=None) -> HotWordEngine:
        """
        Get an initialized HotWordEngine by configured name
        @param hotword: string hotword to load
        @param config: optional global configuration
        @param lang: BCP-47 language code of hotword
        @param loop: Unused
        @return: Initialized HotWordEngine
        """
        lang = standardize_lang_tag(lang)
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
