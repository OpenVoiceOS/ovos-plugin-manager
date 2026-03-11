"""Hardware-related plugins. DEPRECATED: Use ovos-hardware-helpers instead."""
from ovos_utils.log import log_deprecation

# Deprecation notice for this module
log_deprecation("ovos_plugin_manager.hardware module is deprecated, use ovos-hardware-helpers instead and will be removed in v3.0",
                func_name="hardware module",
                func_module="ovos_plugin_manager.hardware",
                deprecation_version="3.0")
