from ovos_plugin_manager.utils import PluginTypes
from ovos_utils.log import LOG


def find_plugins(*args, **kwargs):
    # TODO: Deprecate in 0.1.0
    LOG.warning("This reference is deprecated. "
                "Import from ovos_plugin_manager.utils directly")
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(*args, **kwargs)


def find_skill_plugins() -> dict:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.SKILL)


def load_skill_plugins(*args, **kwargs):
    """
    Load and instantiate installed skill plugins.

    Returns:
        List of initialized skill objects
    """
    # TODO: This doesn't match other plugins that return a class;
    #       should this be refactored to "init_skill_plugins"?
    plugin_skills = []
    plugins = find_skill_plugins()
    for skill_id, plug in plugins.items():
        try:
            skill = plug(*args, **kwargs)
        except:
            LOG.exception(f"Failed to load {skill_id}")
            continue
        plugin_skills.append(skill)
    return plugin_skills
