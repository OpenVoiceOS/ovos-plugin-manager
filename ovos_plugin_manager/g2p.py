from ovos_plugin_manager.utils import load_plugin, find_plugins, PluginTypes
from ovos_plugin_manager.templates.g2p import Grapheme2PhonemePlugin, PhonemeAlphabet
from ovos_utils.log import LOG
from ovos_utils.configuration import read_mycroft_config


def find_g2p_plugins():
    return find_plugins(PluginTypes.PHONEME)


def load_g2p_plugin(module_name):
    return load_plugin(module_name, PluginTypes.PHONEME)


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
        config = config or get_g2p_config()
        g2p_module = config.get("module") or 'dummy'
        if g2p_module == 'dummy':
            return Grapheme2PhonemePlugin
        if g2p_module in OVOSG2PFactory.MAPPINGS:
            g2p_module = OVOSG2PFactory.MAPPINGS[g2p_module]
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
            LOG.info(f'Found plugin {g2p_module}')
            g2p = clazz(g2p_config)
            LOG.info(f'Loaded plugin {g2p_module}')
        except Exception:
            LOG.exception('The selected G2P plugin could not be loaded.')
            raise
        return g2p


def get_g2p_config(config=None):
    config = config or read_mycroft_config()
    if "g2p" in config:
        config = config["g2p"]
    g2p_module = config.get('module', 'dummy')
    g2p_config = config.get(g2p_module, {})
    g2p_config["module"] = g2p_module
    return g2p_config
