from ovos_plugin_manager.utils.config import get_plugin_config
from ovos_utils.log import LOG

from ovos_config import Configuration
from ovos_plugin_manager.templates.language import LanguageTranslator, \
    LanguageDetector
from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes


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


class OVOSLangDetectionFactory:

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
        return load_lang_detect_plugin(lang_module)

    @classmethod
    def create(cls, config=None) -> LanguageDetector:
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
        cfg = config.get(lang_module, {})
        fallback = cfg.get("fallback_module")
        try:
            config["module"] = lang_module
            clazz = OVOSLangDetectionFactory.get_class(config)
            if clazz is None:
                raise ValueError(f"Failed to load module: {lang_module}")
            LOG.info(f'Loaded the Language Detection plugin {lang_module}')
            return clazz(config=get_plugin_config(config, "language",
                                                  lang_module))
        except Exception:
            LOG.exception(f'Language Detection plugin {lang_module} could not be loaded!')
            if fallback in config and fallback != lang_module:
                LOG.info(f"Attempting to load fallback plugin instead: {fallback}")
                config["detection_module"] = fallback
                return cls.create(config)
            raise


class OVOSLangTranslationFactory:

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
        return load_tx_plugin(lang_module)

    @classmethod
    def create(cls, config=None) -> LanguageTranslator:
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
        cfg = config.get(lang_module, {})
        fallback = cfg.get("fallback_module")
        try:
            config["module"] = lang_module
            clazz = OVOSLangTranslationFactory.get_class(config)
            if clazz is None:
                raise ValueError(f"Failed to load module: {lang_module}")
            LOG.info(f'Loaded the Language Translation plugin {lang_module}')
            return clazz(config=get_plugin_config(config, "language",
                                                  lang_module))
        except Exception:
            LOG.exception(f'Language Translation plugin {lang_module} could not be loaded!')
            if fallback in config and fallback != lang_module:
                LOG.info(f"Attempting to load fallback plugin instead: {fallback}")
                config["translation_module"] = fallback
                return cls.create(config)
            raise
