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


class IntentBox(IntentExtractor):
    """ loads all intent plugins, core interfaces with this class only """

    def __init__(self, config=None,
                 strategy=IntentDeterminationStrategy.SEGMENT_REMAINDER,
                 priority=IntentPriority.LOW,
                 segmenter=None):
        super().__init__(config, strategy, priority, segmenter)
        self.services = []
        self._load_intent_plugins()

    def _load_intent_plugins(self):
        engines = []

        for engine_id, engine_class in find_intent_plugins().items():
            engine_config = self.config.get(engine_id, {})
            if engine_config.get("disabled"):
                continue
            try:
                plugin = engine_class(engine_config)
                plugin.engine_id = engine_id
                engines.append(plugin)
            except Exception as e:
                LOG.exception(f"Failed to load intent plugin: {engine_id}")

        engines.sort(key=lambda k: k.priority)
        self.services = engines
        for e in engines:
            LOG.info(f"Loaded intent engine: {e} with priority: {e.priority}")

    def calc_intent(self, utterance, min_conf=0.0, lang=None, session=None):
        lang = lang or self.lang
        matches = []
        for engine in self.services:  # sorted by engine priority
            conf_modifier = max(100 - engine.priority, 1)  # engine weight from 0 - 100
            LOG.info(f"Matching {utterance} with {engine}")
            try:
                for match in engine.calc(utterance, lang=lang, session=session):
                    match.confidence = match.confidence * (conf_modifier / 100)
                    matches.append(match)
                    LOG.debug(f"intent candidate: {match}")
            except:
                LOG.exception(f"{engine} error!")

        if not matches:
            return None
        matches = sorted(matches, key=lambda k: k.priority, reverse=True)
        LOG.debug(f"best match: {matches[0]}")
        return matches[0]
