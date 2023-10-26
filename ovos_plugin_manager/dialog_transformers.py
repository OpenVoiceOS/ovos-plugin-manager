from ovos_plugin_manager.templates.transformers import DialogTransformer, TTSTransformer
from ovos_plugin_manager.utils import PluginTypes
from ovos_plugin_manager.utils import load_plugin, find_plugins


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


def find_tts_transformer_plugins() -> dict:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    return find_plugins(PluginTypes.TTS_TRANSFORMER)


def load_tts_transformer_plugin(module_name: str) -> type(TTSTransformer):
    """Wrapper function for loading dialog_transformer plugin.

    Arguments:
        (str) OpenVoiceOS dialog_transformer module name from config
    Returns:
        class: found dialog_transformer plugin class
    """
    return load_plugin(module_name, PluginTypes.TTS_TRANSFORMER)
