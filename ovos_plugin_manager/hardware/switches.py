"""
DEPRECATED: Use ovos_hardware_helpers.switches instead.

This module re-exports AbstractSwitches from ovos-hardware-helpers as a
backwards-compatibility shim. All new code should import directly from
ovos_hardware_helpers.switches.
"""
from ovos_utils.log import log_deprecation
from ovos_plugin_manager.version import VERSION_MAJOR

# Log deprecation on import
_deprecation_version = f"{VERSION_MAJOR + 1}.0"
log_deprecation("ovos_plugin_manager.hardware.switches is deprecated, use ovos_hardware_helpers.switches instead",
                func_name="switches module",
                func_module="ovos_plugin_manager.hardware.switches",
                deprecation_version=_deprecation_version)

__all__ = ["AbstractSwitches"]


def __getattr__(name: str):
    """Lazy import to make ovos-hardware-helpers an optional dependency."""
    if name == "AbstractSwitches":
        try:
            from ovos_hardware_helpers.switches import AbstractSwitches
            return AbstractSwitches
        except ModuleNotFoundError as e:
            raise ImportError(
                f"ovos-hardware-helpers is not installed. "
                f"Install it with: pip install ovos-hardware-helpers"
            ) from e
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
