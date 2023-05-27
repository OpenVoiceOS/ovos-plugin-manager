from ovos_plugin_manager.utils import PluginTypes


def find_persona_plugins() -> dict:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints (persona entrypoint are just dicts)
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.PERSONA)


