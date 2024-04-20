from ovos_utils.log import LOG

from ovos_plugin_manager.templates.transformers import AudioTransformer, AudioLanguageDetector
from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes


def find_plugins(*args, **kwargs):
    # TODO: Deprecate in 0.1.0
    LOG.warning("This reference is deprecated. "
                "Import from ovos_plugin_manager.utils directly")
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(*args, **kwargs)


def load_plugin(*args, **kwargs):
    # TODO: Deprecate in 0.1.0
    LOG.warning("This reference is deprecated. "
                "Import from ovos_plugin_manager.utils directly")
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(*args, **kwargs)


def find_audio_transformer_plugins() -> dict:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.AUDIO_TRANSFORMER)


def load_audio_transformer_plugin(module_name: str) -> type(AudioTransformer):
    """Wrapper function for loading audio_transformer plugin.

    Arguments:
        (str) OpenVoiceOS audio_transformer module name from config
    Returns:
        class: found audio_transformer plugin class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.AUDIO_TRANSFORMER)


def get_audio_transformer_configs() -> dict:
    """
    Get valid plugin configurations by plugin name
    @return: dict plugin names to list of dict configurations
    """
    from ovos_plugin_manager.utils.config import load_configs_for_plugin_type
    return load_configs_for_plugin_type(PluginTypes.AUDIO_TRANSFORMER)


def get_audio_transformer_module_configs(module_name: str):
    """
    Get valid configuration for the specified plugin
    @param module_name: plugin to get configuration for
    @return: dict configuration (if provided) (TODO: Validate return type)
    """
    from ovos_plugin_manager.utils.config import load_plugin_configs
    return load_plugin_configs(module_name, PluginConfigTypes.AUDIO_TRANSFORMER)


def find_audio_lang_detector_plugins() -> dict:
    """
    Find all installed audio language detector plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return {k: p for k, p in find_plugins(PluginTypes.AUDIO_TRANSFORMER).items()
            if issubclass(p, AudioLanguageDetector)}
