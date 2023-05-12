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


def find_tldr_solver_plugins():
    return find_plugins(PluginTypes.TLDR_SOLVER)


def get_tldr_solver_configs():
    return {plug: get_tldr_solver_module_configs(plug)
            for plug in find_tldr_solver_plugins()}


def get_tldr_solver_module_configs(module_name):
    # solver plugins return {lang: [list of config dicts]}
    cfgs = load_plugin(module_name + ".config", PluginConfigTypes.TLDR_SOLVER) or {}
    return {normalize_lang(lang): v for lang, v in cfgs.items()}


def get_tldr_solver_lang_configs(lang, include_dialects=False):
    lang = normalize_lang(lang)
    configs = {}
    for plug in find_tldr_solver_plugins():
        configs[plug] = []
        confs = get_tldr_solver_module_configs(plug)
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


def get_tldr_solver_supported_langs():
    configs = {}
    for plug in find_tldr_solver_plugins():
        confs = get_tldr_solver_module_configs(plug)
        for lang, cfgs in confs.items():
            if confs:
                if lang not in configs:
                    configs[lang] = []
                configs[lang].append(plug)
    return configs


def load_tldr_solver_plugin(module_name):
    """Wrapper function for loading text_transformer plugin.

    Arguments:
        (str) Mycroft text_transformer module name from config
    Returns:
        class: found text_transformer plugin class
    """
    return load_plugin(module_name, PluginTypes.TLDR_SOLVER)


def find_entailment_solver_plugins():
    return find_plugins(PluginTypes.ENTAILMENT_SOLVER)


def get_entailment_solver_configs():
    return {plug: get_entailment_solver_module_configs(plug)
            for plug in find_entailment_solver_plugins()}


def get_entailment_solver_module_configs(module_name):
    # solver plugins return {lang: [list of config dicts]}
    cfgs = load_plugin(module_name + ".config", PluginConfigTypes.ENTAILMENT_SOLVER) or {}
    return {normalize_lang(lang): v for lang, v in cfgs.items()}


def get_entailment_solver_lang_configs(lang, include_dialects=False):
    lang = normalize_lang(lang)
    configs = {}
    for plug in find_entailment_solver_plugins():
        configs[plug] = []
        confs = get_entailment_solver_module_configs(plug)
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


def get_entailment_solver_supported_langs():
    configs = {}
    for plug in find_entailment_solver_plugins():
        confs = get_entailment_solver_module_configs(plug)
        for lang, cfgs in confs.items():
            if confs:
                if lang not in configs:
                    configs[lang] = []
                configs[lang].append(plug)
    return configs


def load_entailment_solver_plugin(module_name):
    """Wrapper function for loading text_transformer plugin.

    Arguments:
        (str) Mycroft text_transformer module name from config
    Returns:
        class: found text_transformer plugin class
    """
    return load_plugin(module_name, PluginTypes.ENTAILMENT_SOLVER)


def find_multiple_choice_solver_plugins():
    return find_plugins(PluginTypes.MULTIPLE_CHOICE_SOLVER)


def get_multiple_choice_solver_configs():
    return {plug: get_multiple_choice_solver_module_configs(plug)
            for plug in find_multiple_choice_solver_plugins()}


def get_multiple_choice_solver_module_configs(module_name):
    # solver plugins return {lang: [list of config dicts]}
    cfgs = load_plugin(module_name + ".config", PluginConfigTypes.MULTIPLE_CHOICE_SOLVER) or {}
    return {normalize_lang(lang): v for lang, v in cfgs.items()}


def get_multiple_choice_solver_lang_configs(lang, include_dialects=False):
    lang = normalize_lang(lang)
    configs = {}
    for plug in find_multiple_choice_solver_plugins():
        configs[plug] = []
        confs = get_multiple_choice_solver_module_configs(plug)
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


def get_multiple_choice_solver_supported_langs():
    configs = {}
    for plug in find_multiple_choice_solver_plugins():
        confs = get_multiple_choice_solver_module_configs(plug)
        for lang, cfgs in confs.items():
            if confs:
                if lang not in configs:
                    configs[lang] = []
                configs[lang].append(plug)
    return configs


def load_multiple_choice_solver_plugin(module_name):
    """Wrapper function for loading text_transformer plugin.

    Arguments:
        (str) Mycroft text_transformer module name from config
    Returns:
        class: found text_transformer plugin class
    """
    return load_plugin(module_name, PluginTypes.MULTIPLE_CHOICE_SOLVER)


def find_reading_comprehension_solver_plugins():
    return find_plugins(PluginTypes.READING_COMPREHENSION_SOLVER)


def get_reading_comprehension_solver_configs():
    return {plug: get_reading_comprehension_solver_module_configs(plug)
            for plug in find_reading_comprehension_solver_plugins()}


def get_reading_comprehension_solver_module_configs(module_name):
    # solver plugins return {lang: [list of config dicts]}
    cfgs = load_plugin(module_name + ".config", PluginConfigTypes.READING_COMPREHENSION_SOLVER) or {}
    return {normalize_lang(lang): v for lang, v in cfgs.items()}


def get_reading_comprehension_solver_lang_configs(lang, include_dialects=False):
    lang = normalize_lang(lang)
    configs = {}
    for plug in find_reading_comprehension_solver_plugins():
        configs[plug] = []
        confs = get_reading_comprehension_solver_module_configs(plug)
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


def get_reading_comprehension_solver_supported_langs():
    configs = {}
    for plug in find_reading_comprehension_solver_plugins():
        confs = get_reading_comprehension_solver_module_configs(plug)
        for lang, cfgs in confs.items():
            if confs:
                if lang not in configs:
                    configs[lang] = []
                configs[lang].append(plug)
    return configs


def load_reading_comprehension_solver_plugin(module_name):
    """Wrapper function for loading text_transformer plugin.

    Arguments:
        (str) Mycroft text_transformer module name from config
    Returns:
        class: found text_transformer plugin class
    """
    return load_plugin(module_name, PluginTypes.READING_COMPREHENSION_SOLVER)
