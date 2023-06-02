from typing import Optional

from ovos_plugin_manager.utils import normalize_lang, PluginTypes, PluginConfigTypes
from ovos_plugin_manager.templates.g2p import Grapheme2PhonemePlugin, PhonemeAlphabet
from ovos_utils.log import LOG
from ovos_config import Configuration


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


def find_g2p_plugins() -> dict:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.PHONEME)


def load_g2p_plugin(module_name: str) -> Grapheme2PhonemePlugin:
    """
    Get an uninstantiated class for the requested module_name
    @param module_name: Plugin entrypoint name to load
    @return: Uninstantiated class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.PHONEME)


def get_g2p_configs() -> dict:
    """
    Get valid plugin configurations by plugin name
    @return: dict plugin names to list of dict configurations
    """
    from ovos_plugin_manager.utils.config import load_configs_for_plugin_type
    return load_configs_for_plugin_type(PluginTypes.PHONEME)


def get_g2p_module_configs(module_name: str):
    """
    Get valid configurations for the specified plugin
    @param module_name: plugin to get configuration for
    @return: dict configuration (if provided) (TODO: Validate return type)
    """
    from ovos_plugin_manager.utils.config import load_plugin_configs
    return load_plugin_configs(module_name,
                               PluginConfigTypes.PHONEME, True)


def get_g2p_lang_configs(lang: str, include_dialects: bool = False) -> dict:
    """
    Get a dict of plugin names to list valid configurations for the requested
    lang.
    @param lang: Language to get configurations for
    @param include_dialects: consider configurations in different locales
    @return: dict {`plugin_name`: [`valid_configs`]}
    """
    from ovos_plugin_manager.utils.config import get_plugin_language_configs
    return get_plugin_language_configs(PluginTypes.PHONEME, lang,
                                       include_dialects)


def get_g2p_supported_langs() -> dict:
    """
    Return a dict of plugin names to list supported languages
    @return: dict plugin names to list supported languages
    """
    from ovos_plugin_manager.utils.config import get_plugin_supported_languages
    return get_plugin_supported_languages(PluginTypes.PHONEME)


def get_g2p_config(config: Optional[dict] = None) -> dict:
    """
    Get relevant configuration for factory methods
    @param config: global Configuration OR plugin class-specific configuration
    @return: plugin class-specific configuration
    """
    from ovos_plugin_manager.utils.config import get_plugin_config
    return get_plugin_config(config, "g2p")


class OVOSG2PFactory:
    """ replicates the base mycroft class, but uses only OPM enabled plugins"""
    MAPPINGS = {
        "dummy": "ovos-g2p-plugin-dummy",
        "phoneme_guesser": "neon-g2p-plugin-phoneme-guesser",
        "gruut": "neon-g2p-plugin-gruut"
    }

    @staticmethod
    def get_class(config=None):
        """Factory method to get a G2P engine class based on configuration.

        The configuration file ``mycroft.conf`` contains a ``g2p`` section with
        the name of a G2P module to be read by this method.

        "g2p": {
            "module": <engine_name>
        }
        """
        config = get_g2p_config(config)
        g2p_module = config.get("module") or 'dummy'
        if g2p_module in OVOSG2PFactory.MAPPINGS:
            g2p_module = OVOSG2PFactory.MAPPINGS[g2p_module]
        if g2p_module == 'ovos-g2p-plugin-dummy':
            return Grapheme2PhonemePlugin

        return load_g2p_plugin(g2p_module)

    @staticmethod
    def create(config=None):
        """Factory method to create a G2P engine based on configuration.

        The configuration file ``mycroft.conf`` contains a ``g2p`` section with
        the name of a G2P module to be read by this method.

        "g2p": {
            "module": <engine_name>
        }
        """
        g2p_config = get_g2p_config(config)
        g2p_module = g2p_config.get('module', 'dummy')
        try:
            clazz = OVOSG2PFactory.get_class(g2p_config)
            g2p = clazz(g2p_config)
            LOG.debug(f'Loaded plugin {g2p_module}')
        except Exception:
            LOG.exception('The selected G2P plugin could not be loaded.')
            raise
        return g2p
