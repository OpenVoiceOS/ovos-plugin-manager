from ovos_plugin_manager.utils import load_plugin, find_plugins, PluginTypes
from ovos_plugin_manager.templates.intents import IntentExtractor, IntentPriority,\
    IntentDeterminationStrategy, IntentMatch, IntentEngine
from ovos_utils.log import LOG


def find_intent_plugins():
    return find_plugins(PluginTypes.INTENT_ENGINE)


def load_intent_plugin(module_name):
    """Wrapper function for loading text_transformer plugin.

    Arguments:
        (str) Mycroft text_transformer module name from config
    Returns:
        class: found text_transformer plugin class
    """
    return load_plugin(module_name, PluginTypes.INTENT_ENGINE)


def load_intent_engine(module_name, config=None):
    config = config or {}
    for engine_id, engine_class in find_intent_plugins().items():
        engine_config = config.get(engine_id, {})
        if engine_id == module_name:
            try:
                return engine_class(engine_config)
            except Exception as e:
                LOG.exception(f"Failed to load intent plugin: {engine_id}")
            break
    else:
        LOG.error(f"intent plugin not found: {module_name}")

