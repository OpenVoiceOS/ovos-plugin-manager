from ovos_plugin_manager.utils import PluginTypes


def __getattr__(name):
    # OpenVoiceOSPlugin lives in the deprecated plugin_entry module; importing
    # it lazily keeps `from ovos_plugin_manager import OpenVoiceOSPlugin`
    # working without dragging the deprecated module into every package import.
    if name == "OpenVoiceOSPlugin":
        from ovos_plugin_manager.plugin_entry import OpenVoiceOSPlugin
        return OpenVoiceOSPlugin
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
