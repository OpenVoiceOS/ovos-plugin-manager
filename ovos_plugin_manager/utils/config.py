from typing import Optional
from ovos_config.config import Configuration


def get_plugin_config(config: Optional[dict] = None, section: str = None,
                      module: Optional[str] = None) -> dict:
    """
    Get a configuration dict for the specified plugin
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
        module_config = config.get(module) or dict()
        module_config.setdefault('lang', lang)
        module_config.setdefault('module', module)
        return module_config
    config.setdefault('lang', lang)
    return config
