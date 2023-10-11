from ovos_plugin_manager.utils.config import get_plugin_config
from ovos_utils.log import LOG

from ovos_config import Configuration
from ovos_plugin_manager.templates.language import LanguageTranslator, \
    LanguageDetector
from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes


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


def find_tx_plugins() -> dict:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.TRANSLATE)


def load_tx_plugin(module_name: str) -> type(LanguageTranslator):
    """
    Get an uninstantiated class for the requested module_name
    @param module_name: Plugin entrypoint name to load
    @return: Uninstantiated class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.TRANSLATE)


def get_tx_configs() -> dict:
    """
    Get valid plugin configurations by plugin name
    @return: dict plugin names to list of dict configurations
    """
    from ovos_plugin_manager.utils.config import load_configs_for_plugin_type
    return load_configs_for_plugin_type(PluginTypes.TRANSLATE)


def get_tx_module_configs(module_name: str):
    """
    Get valid configurations for the specified plugin
    @param module_name: plugin to get configuration for
    @return: list of dict configurations (if provided)  TODO Validate type
    """
    from ovos_plugin_manager.utils.config import load_plugin_configs
    return load_plugin_configs(module_name, PluginConfigTypes.TRANSLATE)


def find_lang_detect_plugins():
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.LANG_DETECT)


def load_lang_detect_plugin(module_name: str) -> type(LanguageDetector):
    """
    Get an uninstantiated class for the requested module_name
    @param module_name: Plugin entrypoint name to load
    @return: Uninstantiated class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.LANG_DETECT)


def get_lang_detect_configs() -> dict:
    """
    Get valid plugin configurations by plugin name
    @return: dict plugin names to list of dict configurations
    """
    from ovos_plugin_manager.utils.config import load_configs_for_plugin_type
    return load_configs_for_plugin_type(PluginTypes.LANG_DETECT)


def get_lang_detect_module_configs(module_name: str):
    """
    Get valid configurations for the specified plugin
    @param module_name: plugin to get configuration for
    @return: list of dict configurations (if provided)  TODO Validate type
    """
    from ovos_plugin_manager.utils.config import load_plugin_configs
    return load_plugin_configs(module_name, PluginConfigTypes.LANG_DETECT)


_fallback_lang_detect_plugin = "ovos-lang-detect-ngram-lm"
_fallback_translate_plugin = "ovos-translate-plugin-server"


class OVOSLangDetectionFactory:
    """
    replicates the base neon class, but uses only OPM enabled plugins
    """
    MAPPINGS = {
        "libretranslate": "libretranslate_detection_plug",
        "google": "googletranslate_detection_plug",
        "amazon": "amazontranslate_detection_plug",
        "cld2": "cld2_plug",
        "cld3": "cld3_plug",
        "langdetect": "langdetect_plug",
        "fastlang": "fastlang_plug",
        "lingua_podre": "lingua_podre_plug"
    }

    @staticmethod
    def get_class(config=None):
        """
        Factory method to get a Language Detector class based on configuration.

        Configuration contains a `language` section with
        the name of a LangDetection module to be read by this method.

        "language": {
            "detection_module": <engine_name>
        }
        """
        config = config or Configuration()
        if "language" in config:
            config = config["language"]
        lang_module = config.get("detection_module", config.get("module"))
        if not lang_module:
            raise ValueError("`language.detection_module` not configured")
        if lang_module in OVOSLangDetectionFactory.MAPPINGS:
            lang_module = OVOSLangDetectionFactory.MAPPINGS[lang_module]
        return load_lang_detect_plugin(lang_module)

    @staticmethod
    def create(config=None) -> LanguageDetector:
        """
        Factory method to create a LangDetection engine based on configuration

        Configuration contains a `language` section with
        the name of a LangDetection module to be read by this method.

        "language": {
            "detection_module": <engine_name>
        }
        """
        config = config or Configuration()
        if "language" in config:
            config = config["language"]
        lang_module = config.get("detection_module", config.get("module"))
        try:
            clazz = OVOSLangDetectionFactory.get_class(config)
            if clazz is None:
                raise ValueError(f"Failed to load module: {lang_module}")
            LOG.info(f'Loaded the Language Detection plugin {lang_module}')
            if lang_module in OVOSLangDetectionFactory.MAPPINGS:
                lang_module = OVOSLangDetectionFactory.MAPPINGS[lang_module]
            return clazz(config=get_plugin_config(config, "language",
                                                  lang_module))
        except Exception:
            # The Language Detection backend failed to start, fall back if appropriate.
            if lang_module != _fallback_lang_detect_plugin:
                lang_module = _fallback_lang_detect_plugin
                LOG.error(f'Language Detection plugin {lang_module} not found. '
                          f'Falling back to {_fallback_lang_detect_plugin}')
                clazz = load_lang_detect_plugin(_fallback_lang_detect_plugin)
                if clazz:
                    return clazz(config=get_plugin_config(config, "language",
                                                          lang_module))
            
            raise


class OVOSLangTranslationFactory:
    """ replicates the base neon class, but uses only OPM enabled plugins"""
    MAPPINGS = {
        "libretranslate": "libretranslate_plug",
        "google": "googletranslate_plug",
        "amazon": "amazontranslate_plug",
        "apertium": "apertium_plug"
    }

    @staticmethod
    def get_class(config=None):
        """
        Factory method to get a Language Translator class based on configuration.

        Configuration contains a `language` section with
        the name of a Translation module to be read by this method.

        "language": {
            "translation_module": <engine_name>
        }
        """
        config = config or Configuration()
        if "language" in config:
            config = config["language"]
        lang_module = config.get("translation_module", config.get("module"))
        if not lang_module:
            raise ValueError("`language.translation_module` not configured")
        if lang_module in OVOSLangTranslationFactory.MAPPINGS:
            lang_module = OVOSLangTranslationFactory.MAPPINGS[lang_module]
        return load_tx_plugin(lang_module)

    @staticmethod
    def create(config=None) -> LanguageTranslator:
        """
        Factory method to create a LangTranslation engine based on configuration

        Configuration contains a `language` section with
        the name of a Translation module to be read by this method.

        "language": {
            "translation_module": <engine_name>
        }
        """
        config = config or Configuration()
        if "language" in config:
            config = config["language"]
        lang_module = config.get("translation_module", config.get("module"))
        try:
            clazz = OVOSLangTranslationFactory.get_class(config)
            if clazz is None:
                raise ValueError(f"Failed to load module: {lang_module}")
            LOG.info(f'Loaded the Language Translation plugin {lang_module}')
            if lang_module in OVOSLangTranslationFactory.MAPPINGS:
                lang_module = OVOSLangTranslationFactory.MAPPINGS[lang_module]
            return clazz(config=get_plugin_config(config, "language",
                                                  lang_module))
        except Exception:
            # The Language Translation backend failed to start, fall back if appropriate.
            if lang_module != _fallback_translate_plugin:
                lang_module = _fallback_translate_plugin
                LOG.error(f'Language Translation plugin {lang_module} '
                          f'not found. Falling back to {_fallback_translate_plugin}')
                clazz = load_tx_plugin(_fallback_translate_plugin)
                if clazz:
                    return clazz(config=get_plugin_config(config, "language",
                                                          lang_module))

            raise
