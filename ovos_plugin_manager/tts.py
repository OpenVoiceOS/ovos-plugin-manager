import json
import os
from typing import Dict, Optional, Type

from ovos_plugin_manager.templates.tts import TTS, TTSContext, TTSValidator, TextToSpeechCache, ConcatTTS
from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes
from ovos_utils.log import LOG
from ovos_utils.xdg_utils import xdg_data_home
from hashlib import md5


def find_tts_plugins() -> Dict[str, Type[TTS]]:
    """
    Discover installed TTS plugins.
    
    Returns:
        Dict[str, Type[TTS]]: Mapping of entry point name to the uninstantiated TTS plugin class.
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.TTS)


def load_tts_plugin(module_name: str) -> Type[TTS]:
    """
    Load an uninstantiated TTS plugin class by its entrypoint name.
    
    Parameters:
        module_name (str): Plugin entrypoint name to load.
    
    Returns:
        The TTS plugin class (uninstantiated).
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
    Retrieve language-specific TTS configuration lists for a plugin.
    
    Parameters:
        module_name (str): Name of the TTS plugin to load configurations for.
    
    Returns:
        dict: Mapping of language code (str) to a list of configuration dicts for that language.
              Each list is sorted by the "priority" key in ascending order (default priority is 60).
    """
    from ovos_plugin_manager.utils.config import load_plugin_configs
    configs = load_plugin_configs(module_name, PluginConfigTypes.TTS)
    # let's sort by priority key
    for k, v in configs.items():
        configs[k] = sorted(v, key=lambda c: c.get("priority", 60))
    return configs


def get_tts_lang_configs(lang: str, include_dialects: bool = False) -> dict:
    """
    Retrieve TTS configuration lists for a language across installed TTS plugins.
    
    Parameters:
    	lang (str): Language tag to query (e.g., "en", "en-US").
    	include_dialects (bool): If true, include configurations for related dialects/locales
    		(e.g., include "en-GB" when querying "en-US").
    
    Returns:
    	dict: Mapping of plugin name to a list of valid configuration dictionaries for the
    		specified language; each list is sorted by the `priority` key (higher priority first).
    """
    from ovos_plugin_manager.utils.config import get_plugin_language_configs
    return get_plugin_language_configs(PluginTypes.TTS, lang, include_dialects)


def get_tts_supported_langs() -> dict:
    """
    List languages and which TTS plugins support each language.
    
    Returns:
        dict: Mapping from language code (str) to a list of plugin names (list[str]) that provide TTS support for that language.
    """
    from ovos_plugin_manager.utils.config import get_plugin_supported_languages
    return get_plugin_supported_languages(PluginTypes.TTS)


def get_tts_config(config: dict = None, module: str = None) -> dict:
    """
    Return configuration for TTS plugins used by factory methods.
    
    Parameters:
        config (dict, optional): Global configuration or plugin-specific configuration to use.
        module (str, optional): TTS plugin module name to retrieve configuration for; if omitted, returns the general TTS configuration.
    
    Returns:
        dict: Resolved plugin-specific configuration dictionary.
    """
    from ovos_plugin_manager.utils.config import get_plugin_config
    return get_plugin_config(config, 'tts', module)


def get_voice_id(plugin_name: str, lang: str, tts_config: dict) -> str:
    """
    Produce a stable unique identifier for a TTS voice configuration.
    
    Parameters:
        plugin_name (str): TTS plugin entry point name.
        lang (str): BCP-47 language code.
        tts_config (dict): Voice-specific configuration dictionary; keys order does not affect identity.
    
    Returns:
        str: Identifier in the form "<plugin_name>_<lang>_<config_hash>" where <config_hash> is a stable hash of the configuration.
    """
    tts_hash = md5(json.dumps(tts_config,
                              sort_keys=True).encode("utf-8")).hexdigest()
    return f"{plugin_name}_{lang}_{tts_hash}"


def scan_voices() -> dict:
    """
    Enumerate installed TTS plugins and persist each discovered voice configuration to disk.
    
    For each supported language and voice variant this creates a JSON file at
    ~/.local/share/OPM/voice_configs/<lang>/<voice_id>.json containing the voice configuration.
    Existing voice metadata keys (priority, display_name, offline, gender) are moved into a `meta`
    sub-dictionary and the `module` key is set to the plugin name.
    
    Returns:
        voice_ids (dict): Mapping from `voice_id` (str) to the voice configuration dict written to disk.
    """
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


def get_voices(scan: bool = False) -> dict:
    """
    List all available TTS voice configurations, optionally re-scanning installed plugins first.
    
    Voice configuration files are read from ~/.local/share/OPM/voice_configs/<lang>/. Call scan_voices() or pass scan=True to refresh on-disk voice definitions before loading.
    
    Parameters:
        scan (bool): If True, re-scan installed TTS plugins and update on-disk voice configs before reading.
    
    Returns:
        dict: Mapping of voice_id (filename) to the loaded voice configuration dictionary.
    """
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
        tts_module = config.get("module") or "ovos-tts-plugin-dummy"
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
        tts_module = tts_config.get('module')
        if not tts_module:
            raise ValueError("tts 'module' is not set in config")
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
