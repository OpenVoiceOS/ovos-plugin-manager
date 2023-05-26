from ovos_plugin_manager.utils import normalize_lang, \
    PluginTypes, PluginConfigTypes
from ovos_config import Configuration
from ovos_utils.log import LOG
from ovos_plugin_manager.templates.segmentation import Segmenter


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


def find_segmentation_plugins() -> dict:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.UTTERANCE_SEGMENTATION)


def load_segmentation_plugin(module_name: str) -> type(Segmenter):
    """
    Get an uninstantiated class for the requested module_name
    @param module_name: Plugin entrypoint name to load
    @return: Uninstantiated class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.UTTERANCE_SEGMENTATION)


def get_segmentation_configs() -> dict:
    """
    Get valid plugin configurations by plugin name
    @return: dict plugin names to list of dict configurations
    """
    from ovos_plugin_manager.utils.config import load_configs_for_plugin_type
    return load_configs_for_plugin_type(PluginTypes.UTTERANCE_SEGMENTATION)


def get_segmentation_module_configs(module_name: str) -> dict:
    """
    Get valid configurations for the specified plugin
    @param module_name: plugin to get configuration for
    @return: dict configurations by language (if provided)
    """
    from ovos_plugin_manager.utils.config import load_plugin_configs
    return load_plugin_configs(module_name,
                               PluginConfigTypes.UTTERANCE_SEGMENTATION, True)


def get_segmentation_lang_configs(lang: str,
                                     include_dialects: bool = False) -> dict:
    """
    Get a dict of plugin names to list valid configurations for the requested
    lang.
    @param lang: Language to get configurations for
    @param include_dialects: consider configurations in different locales
    @return: dict {`plugin_name`: `valid_configs`]}
    """
    from ovos_plugin_manager.utils.config import get_plugin_language_configs
    return get_plugin_language_configs(PluginTypes.UTTERANCE_SEGMENTATION, lang,
                                       include_dialects)


def get_segmentation_supported_langs():
    """
    Return a dict of plugin names to list supported languages
    @return: dict plugin names to list supported languages
    """
    from ovos_plugin_manager.utils.config import get_plugin_supported_languages
    return get_plugin_supported_languages(PluginTypes.UTTERANCE_SEGMENTATION)


def get_segmentation_config(config: dict = None) -> dict:
    """
    Get relevant configuration for factory methods
    @param config: global Configuration OR plugin class-specific configuration
    @return: plugin class-specific configuration
    """
    from ovos_plugin_manager.utils.config import get_plugin_config
    config = config or Configuration()
    return get_plugin_config(config, "segmentation")


class OVOSUtteranceSegmenterFactory:
    """ reads mycroft.conf and returns the globally configured plugin """
    MAPPINGS = {
        # default split at sentence boundaries
        # usually helpful in other plugins and included in base class
        "dummy": "ovos-segmentation-plugin-quebrafrases"
    }

    @staticmethod
    def get_class(config=None):
        """Factory method to get a Segmenter engine class based on configuration.

        The configuration file ``mycroft.conf`` contains a ``segmentation`` section with
        the name of a Segmenter module to be read by this method.

        "segmentation": {
            "module": <engine_name>
        }
        """
        config = get_segmentation_config(config)
        segmentation_module = config.get("module", "ovos-segmentation-plugin-quebrafrases")
        if segmentation_module in OVOSUtteranceSegmenterFactory.MAPPINGS:
            segmentation_module = OVOSUtteranceSegmenterFactory.MAPPINGS[segmentation_module]
        return load_segmentation_plugin(segmentation_module)

    @staticmethod
    def create(config=None):
        """Factory method to create a Segmenter engine based on configuration.

        The configuration file ``mycroft.conf`` contains a ``segmentation`` section with
        the name of a Segmenter module to be read by this method.

        "segmentation": {
            "module": <engine_name>
        }
        """
        config = config or get_segmentation_config()
        plugin = config.get("module") or "ovos-segmentation-plugin-quebrafrases"
        plugin_config = config.get(plugin) or {}
        try:
            clazz = OVOSUtteranceSegmenterFactory.get_class(config)
            return clazz(plugin_config)
        except Exception:
            LOG.exception(f'Utterance Segmentation plugin {plugin} '
                          f'could not be loaded!')
            return Segmenter()
