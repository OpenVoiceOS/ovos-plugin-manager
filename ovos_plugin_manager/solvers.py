from ovos_plugin_manager.utils import load_plugin, find_plugins, PluginTypes


def find_question_solver_plugins():
    return find_plugins(PluginTypes.QUESTION_SOLVER)


def get_question_solver_config_examples(module_name):
    return load_plugin(module_name + ".config",
                       PluginTypes.QUESTION_SOLVER_CONFIG)


def load_question_solver_plugin(module_name):
    """Wrapper function for loading text_transformer plugin.

    Arguments:
        (str) Mycroft text_transformer module name from config
    Returns:
        class: found text_transformer plugin class
    """
    return load_plugin(module_name, PluginTypes.QUESTION_SOLVER)

