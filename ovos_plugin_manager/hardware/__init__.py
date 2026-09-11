"""Hardware-related plugins. DEPRECATED: Use ovos-hardware-helpers instead."""
from ovos_utils.log import log_deprecation
from ovos_plugin_manager.version import VERSION_MAJOR

# Calculate next major version for deprecation
_deprecation_version = f"{VERSION_MAJOR + 1}.0"

# Deprecation notice for this module
log_deprecation(f"ovos_plugin_manager.hardware module is deprecated, use ovos-hardware-helpers instead and will be removed in v{_deprecation_version}",
                func_name="hardware module",
                func_module="ovos_plugin_manager.hardware",
                deprecation_version=_deprecation_version)

__all__ = ["AbstractFan", "AbstractSwitches", "AbstractLed", "Color"]


def __getattr__(name: str):
    """Lazy import to make ovos-hardware-helpers an optional dependency."""
    if name == "AbstractFan":
        from ovos_plugin_manager.hardware.fan import AbstractFan
        return AbstractFan
    elif name == "AbstractSwitches":
        from ovos_plugin_manager.hardware.switches import AbstractSwitches
        return AbstractSwitches
    elif name == "AbstractLed":
        from ovos_plugin_manager.hardware.led import AbstractLed
        return AbstractLed
    elif name == "Color":
        from ovos_plugin_manager.hardware.led import Color
        return Color
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
