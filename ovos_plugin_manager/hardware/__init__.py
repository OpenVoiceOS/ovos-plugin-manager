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
