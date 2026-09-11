from ovos_plugin_manager.templates.transformers import DialogTransformer
from ovos_plugin_manager.utils import PluginTypes
from ovos_plugin_manager.utils import load_plugin, find_plugins
# TTS transformer helpers live in ovos_plugin_manager.tts_transformers,
# re-exported here for backwards compatibility
from ovos_plugin_manager.tts_transformers import (
    find_tts_transformer_plugins as find_tts_transformer_plugins,
    load_tts_transformer_plugin as load_tts_transformer_plugin)


def find_dialog_transformer_plugins() -> dict:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    return find_plugins(PluginTypes.DIALOG_TRANSFORMER)


def load_dialog_transformer_plugin(module_name: str) -> type(DialogTransformer):
    """Wrapper function for loading dialog_transformer plugin.

    Arguments:
        (str) OpenVoiceOS dialog_transformer module name from config
    Returns:
        class: found dialog_transformer plugin class
    """
    return load_plugin(module_name, PluginTypes.DIALOG_TRANSFORMER)
