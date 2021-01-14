from ovos_plugin_manager.utils import find_plugins, PluginTypes
from ovos_utils.messagebus import get_mycroft_bus
from ovos_utils.log import LOG


def setup_audio_service(service_module, config=None, bus=None):
    """Run the appropriate setup function and return created service objects.

    Arguments:
        service_module: Python module to run
        config (dict): Mycroft configuration dict
        bus (MessageBusClient): Messagebus interface
    Returns:
        (list) List of created services.
    """
    config = config or {}
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


def find_audio_service_plugins():
    return find_plugins(PluginTypes.AUDIO)


def load_audio_service_plugins(config=None, bus=None):
    """Load installed audioservice plugins.

    Arguments:
        config: configuration dict for the audio backends.
        bus: Mycroft messagebus

    Returns:
        List of started services
    """
    bus = bus or get_mycroft_bus()
    plugin_services = []
    plugins = find_audio_service_plugins()
    for plug in plugins:
        service = setup_audio_service(plug, config, bus)
        if service:
            plugin_services += service
    return plugin_services
