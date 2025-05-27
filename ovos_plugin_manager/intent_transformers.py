from ovos_plugin_manager.templates.transformers import IntentTransformer
from ovos_plugin_manager.utils import PluginTypes


def find_intent_transformer_plugins() -> dict:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.INTENT_TRANSFORMER)


def load_intent_transformer_plugin(module_name: str) -> \
        type(IntentTransformer):
    """
    Get an uninstantiated class for the requested module_name
    @param module_name: Plugin entrypoint name to load
    @return: Uninstantiated class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.INTENT_TRANSFORMER)
