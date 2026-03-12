"""
DEPRECATED: Use ovos_hardware_helpers.fan instead.

This module re-exports AbstractFan from ovos-hardware-helpers as a
backwards-compatibility shim. All new code should import directly from
ovos_hardware_helpers.fan.
"""
from ovos_utils.log import log_deprecation
from ovos_plugin_manager.version import VERSION_MAJOR

# Log deprecation on import
_deprecation_version = f"{VERSION_MAJOR + 1}.0"
log_deprecation("ovos_plugin_manager.hardware.fan is deprecated, use ovos_hardware_helpers.fan instead",
                func_name="fan module",
                func_module="ovos_plugin_manager.hardware.fan",
                deprecation_version=_deprecation_version)

# Re-export from ovos-hardware-helpers
from ovos_hardware_helpers.fan import AbstractFan

__all__ = ["AbstractFan"]
