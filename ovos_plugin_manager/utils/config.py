from typing import Optional, Union
from ovos_config.config import Configuration
from ovos_utils.log import LOG
from ovos_plugin_manager.utils import load_plugin, find_plugins, \
    normalize_lang, PluginTypes, PluginConfigTypes


def get_plugin_config(config: Optional[dict] = None, section: str = None,
                      module: Optional[str] = None) -> dict:
    """
    Get a configuration dict for the specified plugin. Configuration is applied
    such that:
    - module-specific configurations take priority
    - section-specific configuration is appended (new keys only)
    - global `lang` configuration is appended (if not already set)
    @param config: Base configuration to parse, defaults to `Configuration()`
    @param section: Config section for the plugin (i.e. TTS, STT, language)
    @param module: Module/plugin to get config for, default reads from config
    @return: Configuration for the requested module, including `lang` and `module` keys
    """
    config = config or Configuration()
    lang = config.get('lang') or Configuration().get('lang')
    config = (config.get('intentBox', {}).get(section) or config.get(section)
              or config) if section else config
    module = module or config.get('module')
    if module:
        module_config = dict(config.get(module) or dict())
        module_config.setdefault('module', module)
        for key, val in config.items():
            # Configured module name is not part of that module's config
            if key in ("module", "translation_module", "detection_module"):
                continue
            elif isinstance(val, dict):
                continue
            # Use section-scoped config as defaults (i.e. TTS.lang)
            module_config.setdefault(key, val)
        config = module_config
    if section not in ["hotwords", "VAD", "listener", "gui"]:
        config.setdefault('lang', lang)
    LOG.debug(f"Loaded configuration: {config}")
    return config


def get_valid_plugin_configs(configs: dict, lang: str,
                             include_dialects: bool) -> list:
    """
    Get a sorted dict of configurations for a particular plugin
    @param configs: dict of normalized language to sorted list of valid dict
                    configurations for a particular plugin
    @param lang: normalized language to return valid configurations for
    @param include_dialects: if True, include configs for alternate dialects
    @return: list of valid configurations matching the requested lang
    """
    valid_configs = list()
    if include_dialects:
        # Check other dialects of the requested language
        base_lang = lang.split("-")[0]
        for language, confs in configs.items():
            if language.startswith(base_lang):
                for config in confs:
                    try:
                        if language != lang:
                            # Dialect match, boost priority
                            config["priority"] = config.get("priority",
                                                            60) + 15
                        valid_configs.append(config)
                    except Exception as e:
                        LOG.error(f'config={config}')
                        LOG.exception(e)
    elif lang in configs:
        # Exact language/dialog match
        valid_configs.append(configs[lang])
    elif f"{lang}-{lang}" in configs:
        # match (some) default locales
        valid_configs.append(configs[f"{lang}-{lang}"])
    LOG.debug(f'Found {len(valid_configs)} valid configurations for {lang}')
    return valid_configs


def sort_plugin_configs(configs: dict) -> dict:
    """
    Sort a dict of plugin name to valid configurations by priority
    @param configs: dict config name to valid configurations
    @return: dict of sorted lists with highest priority at the end of the list
    """
    bad_plugs = []
    for plug_name, plug_configs in configs.items():
        LOG.debug(plug_configs)
        try:
            configs[plug_name] = sorted(plug_configs,
                                        key=lambda c: c.get("priority", 60))
        except:
            LOG.exception(f"Invalid plugin data: {plug_name}")
            bad_plugs.append(plug_name)

    for plug_name in [p for p in bad_plugs if p in configs]:
        configs.pop(plug_name)

    LOG.debug(configs)
    return {k: v for k, v in configs.items() if v}


def load_plugin_configs(plug_name: str,
                        plug_type: Optional[PluginConfigTypes] = None,
                        normalize_language_keys: bool = False) -> \
        Union[dict, list]:
    """
    Load a specific plugin's valid configurations.

    Arguments:
        plug_type: (str) plugin type name. Ex. "mycroft.plugin.tts".
        plug_name: (str) specific plugin name
        normalize_language_keys: (bool) If true, normalize dict keys as langs
    Returns:
        Loaded configuration dict, list of dicts, or None
        if no matching object was found.
    """
    config = load_plugin(plug_name + ".config", plug_type)
    if normalize_language_keys:
        return {normalize_lang(lang): v for lang, v in config.items()}
    return config


def load_configs_for_plugin_type(plug_type: PluginTypes) -> dict:
    """
    Load all valid configuration options for the specified plug_type
    @param plug_type: Plugin type to get configs for
    @return: dict plugin name to list or dict configurations
    """
    return {plug: load_plugin_configs(
            plug, PluginConfigTypes(f"{plug_type.value}.config"))
            for plug in find_plugins(plug_type)} or dict()


def get_plugin_supported_languages(plug_type: PluginTypes) -> dict:
    """
    Return a dict of plugin names to list supported languages
    @param plug_type: plugin type to get plugins/configuration for
    @return: dict plugin names to list supported languages
    """
    lang_configs = dict()
    for plug in find_plugins(plug_type):
        configs = \
            load_plugin_configs(plug,
                                PluginConfigTypes(f"{plug_type.value}.config"))
        for lang, config in configs:
            lang = normalize_lang(lang)
            lang_configs.setdefault(lang, list())
            lang_configs[lang].append(plug)
    return lang_configs


def get_plugin_language_configs(plug_type: PluginTypes, lang: str,
                                include_dialects: bool = False) -> dict:
    """
    Return a dict of plugin names to list of valid (dict) configurations
    @param plug_type: plugin type to get configurations for
    @param lang: BCP-47 language code to get configurations for
    @param include_dialects: consider configurations in different locales
    @return: dict {`plugin_name`: [`valid_configs`]}
    """
    lang = normalize_lang(lang)
    plugin_configs = dict()
    valid_configs = dict()
    for plug in find_plugins(plug_type):
        plugin_configs[plug] = list()
        valid_configs = \
            load_plugin_configs(plug,
                                PluginConfigTypes(f"{plug_type.value}.config"))
        valid_configs = {normalize_lang(lang): conf
                         for lang, conf in valid_configs.items()}
        if include_dialects:
            lang = lang.split('-')[0]
            for language in valid_configs:
                if language.startswith(lang):
                    plugin_configs[plug] += valid_configs[language]
        elif lang in valid_configs:
            plugin_configs[plug] += valid_configs[lang]
        elif f"{lang}-{lang}" in valid_configs:
            plugin_configs += valid_configs[f"{lang}-{lang}"]
    return {plug: configs for plug, configs in
            valid_configs.items() if configs} or dict()
