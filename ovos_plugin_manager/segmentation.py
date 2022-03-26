from ovos_plugin_manager.utils import load_plugin, find_plugins, PluginTypes
from ovos_utils.configuration import read_mycroft_config
from ovos_utils.log import LOG
from ovos_plugin_manager.templates.segmentation import Segmenter


def find_segmentation_plugins():
    return find_plugins(PluginTypes.UTTERANCE_SEGMENTATION)


def load_segmentation_plugin(module_name):
    """Wrapper function for loading segmentation plugin.

    Arguments:
        module_name (str): segmentation module name from config
    Returns:
        class: Segmenter plugin class
    """
    return load_plugin(module_name, PluginTypes.UTTERANCE_SEGMENTATION)


class OVOSUtteranceSegmenterFactory:
    """ reads mycroft.conf and returns the globally configured plugin """
    MAPPINGS = {
        # default split at sentence boundaries
        # usually helpful in other plugins and included in base class
        # there is no dedicated plugin anymore
        "ovos-segmentation-plugin-quebrafrases": "dummy"
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
        config = config or get_segmentation_config()
        segmentation_module = config.get("module", "dummy")
        if segmentation_module in OVOSUtteranceSegmenterFactory.MAPPINGS:
            segmentation_module = OVOSUtteranceSegmenterFactory.MAPPINGS[segmentation_module]
        if segmentation_module == "dummy":
            return Segmenter
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
        plugin = config.get("module") or "dummy"
        plugin_config = config.get(plugin) or {}
        try:
            clazz = OVOSUtteranceSegmenterFactory.get_class(config)
            return clazz(plugin_config)
        except Exception:
            LOG.error(f'Utterance Segmentation plugin {plugin} could not be loaded!')
            raise


def get_segmentation_config(config=None):
    config = config or read_mycroft_config()
    lang = config.get("lang")
    if "intentBox" in config and "segmentation" not in config:
        config = config["intentBox"] or {}
        lang = config.get("lang") or lang
    if "segmentation" in config:
        config = config["segmentation"]
        lang = config.get("lang") or lang
    config["lang"] = lang or "en-us"
    segmentation_module = config.get('module') or 'dummy'
    segmentation_config = config.get(segmentation_module, {})
    segmentation_config["module"] = segmentation_module
    return segmentation_config


