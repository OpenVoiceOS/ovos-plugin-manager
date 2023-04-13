from ovos_config import Configuration
from ovos_utils.log import LOG
from ovos_utils.messagebus import FakeBus

from ovos_plugin_manager.utils import load_plugin, normalize_lang, find_plugins, PluginTypes, PluginConfigTypes


def find_question_solver_plugins():
    return find_plugins(PluginTypes.QUESTION_SOLVER)


def get_question_solver_configs():
    return {plug: get_question_solver_module_configs(plug)
            for plug in find_question_solver_plugins()}


def get_question_solver_module_configs(module_name):
    # solver plugins return {lang: [list of config dicts]}
    cfgs = load_plugin(module_name + ".config", PluginConfigTypes.QUESTION_SOLVER) or {}
    return {normalize_lang(lang): v for lang, v in cfgs.items()}


def get_question_solver_lang_configs(lang, include_dialects=False):
    lang = normalize_lang(lang)
    configs = {}
    for plug in find_question_solver_plugins():
        configs[plug] = []
        confs = get_question_solver_module_configs(plug)
        if include_dialects:
            lang = lang.split("-")[0]
            for l in confs:
                if l.startswith(lang):
                    configs[plug] += confs[l]
        elif lang in confs:
            configs[plug] += confs[lang]
        elif f"{lang}-{lang}" in confs:
            configs[plug] += confs[f"{lang}-{lang}"]
    return {k: v for k, v in configs.items() if v}


def get_question_solver_supported_langs():
    configs = {}
    for plug in find_question_solver_plugins():
        confs = get_question_solver_module_configs(plug)
        for lang, cfgs in confs.items():
            if confs:
                if lang not in configs:
                    configs[lang] = []
                configs[lang].append(plug)
    return configs


def load_question_solver_plugin(module_name):
    """Wrapper function for loading text_transformer plugin.

    Arguments:
        (str) Mycroft text_transformer module name from config
    Returns:
        class: found text_transformer plugin class
    """
    return load_plugin(module_name, PluginTypes.QUESTION_SOLVER)


class QuestionSolversService:
    def __init__(self, bus=None, config=None):
        self.config_core = config or Configuration()
        self.loaded_modules = {}
        self.bus = bus or FakeBus()
        self.config = self.config_core.get("solvers") or {}
        self.load_plugins()

    def load_plugins(self):
        for plug_name, plug in find_question_solver_plugins().items():
            config = self.config.get(plug_name) or {}
            if not config.get("enabled", True):
                LOG.debug(f"{plug_name} not enabled in config, it won't be loaded")
                continue
            try:
                self.loaded_modules[plug_name] = plug(config=config)
                LOG.info(f"loaded question solver plugin: {plug_name}")
            except Exception as e:
                LOG.exception(f"Failed to load question solver plugin: {plug_name}")

    @property
    def modules(self):
        return sorted(self.loaded_modules.values(),
                      key=lambda k: k.priority)

    def shutdown(self):
        for module in self.modules:
            try:
                module.shutdown()
            except:
                pass

    def spoken_answer(self, utterance, context=None):
        for module in self.modules:
            try:
                ans = module.spoken_answer(utterance, context)
                if ans:
                    return ans
            except Exception as e:
                LOG.error(e)
                pass
