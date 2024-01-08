from ovos_plugin_manager.utils import PluginConfigTypes, PluginTypes
from ovos_utils.log import LOG
from ovos_bus_client.util import get_mycroft_bus
from ovos_config import Configuration
from ovos_utils.log import log_deprecation

log_deprecation("ovos_plugin_manager.audio has been deprecated on ovos-audio, "
                "move to ovos_plugin_manager.media", "0.1.0")


def find_plugins(*args, **kwargs):
    # TODO: Deprecate in 0.1.0
    LOG.warning("This reference is deprecated. "
                "Import from ovos_plugin_manager.utils directly")
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(*args, **kwargs)


def find_audio_service_plugins() -> dict:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.AUDIO)


def get_audio_service_configs() -> dict:
    """
    Get valid plugin configurations by plugin name
    @return: dict plugin names to list of dict configurations
    """
    from ovos_plugin_manager.utils.config import load_configs_for_plugin_type
    return load_configs_for_plugin_type(PluginTypes.AUDIO)


def get_audio_service_module_configs(module_name: str) -> dict:
    """
    Get valid configuration for the specified plugin
    @param module_name: plugin to get configuration for
    @return: dict configuration (if provided)
    """
    from ovos_plugin_manager.utils.config import load_plugin_configs
    return load_plugin_configs(module_name, PluginConfigTypes.AUDIO)


def setup_audio_service(service_module, config=None, bus=None):
    """Run the appropriate setup function and return created service objects.

    Arguments:
        service_module: Python module to run
        config (dict): OpenVoiceOS configuration dict
        bus (MessageBusClient): Messagebus interface
    Returns:
        (list) List of created services.
    """
    config = config or Configuration().get("Audio", {})
    bus = bus or get_mycroft_bus()

    if (hasattr(service_module, 'autodetect') and
            callable(service_module.autodetect)):
        try:
            return service_module.autodetect(config, bus)
        except Exception as e:
            LOG.error('Failed to autodetect audio service. ' + repr(e))
    elif hasattr(service_module, 'load_service'):
        try:
            return service_module.load_service(config, bus)
        except Exception as e:
            LOG.error('Failed to load audio service. ' + repr(e))
    else:
        return None


def load_audio_service_plugins(config=None, bus=None):
    """Load installed audioservice plugins.

    Arguments:
        config: OpenVoiceOS core configuration
        bus: OpenVoiceOS messagebus

    Returns:
        List of started services
    """
    bus = bus or get_mycroft_bus()
    plugin_services = []
    found_plugins = find_audio_service_plugins()
    for plugin_name, plugin_module in found_plugins.items():
        LOG.info(f'Loading audio service plugin: {plugin_name}')
        service = setup_audio_service(plugin_module, config, bus)
        if service:
            plugin_services += service
    return plugin_services
