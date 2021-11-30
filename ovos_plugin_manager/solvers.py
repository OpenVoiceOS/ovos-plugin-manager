from ovos_plugin_manager.utils import load_plugin, find_plugins, PluginTypes


def find_question_solver_plugins():
    return find_plugins(PluginTypes.QUESTION_SOLVER)


def load_question_solver_plugin(module_name):
    """Wrapper function for loading text_transformer plugin.

    Arguments:
        (str) Mycroft text_transformer module name from config
    Returns:
        class: found text_transformer plugin class
    """
    return load_plugin(module_name, PluginTypes.QUESTION_SOLVER)

