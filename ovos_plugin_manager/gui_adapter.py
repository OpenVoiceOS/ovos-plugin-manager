# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""Factory and discovery utilities for ``opm.gui_adapter`` plugins."""
from typing import Dict, List, Optional, Type

from ovos_plugin_manager.templates.gui import AbstractGUIPlugin
from ovos_plugin_manager.utils import PluginTypes, find_plugins, load_plugin
from ovos_utils.log import LOG


def find_gui_adapter_plugins() -> Dict[str, Type[AbstractGUIPlugin]]:
    """Find all installed GUI adapter plugins.

    Returns:
        dict mapping plugin entry-point names to plugin classes.
    """
    return find_plugins(PluginTypes.GUI_ADAPTER)


def load_gui_adapter_plugin(module_name: str) -> Optional[Type[AbstractGUIPlugin]]:
    """Get an uninstantiated class for the requested plugin name.

    Args:
        module_name: Plugin entry-point name (as declared in ``setup.py``).

    Returns:
        Uninstantiated plugin class, or ``None`` if not found.
    """
    return load_plugin(module_name, PluginTypes.GUI_ADAPTER)


class OVOSGUIAdapterFactory:
    """Factory for creating :class:`AbstractGUIPlugin` instances."""

    @staticmethod
    def create(
        module_name: str,
        config: Optional[dict] = None,
        bus=None,
    ) -> Optional[AbstractGUIPlugin]:
        """Create a single GUI adapter plugin instance by name.

        Args:
            module_name: Plugin entry-point name.
            config:      Optional plugin-specific configuration dict.
            bus:         Optional :class:`MessageBusClient` instance.

        Returns:
            Instantiated plugin, or ``None`` if loading or instantiation failed.
        """
        clazz = load_gui_adapter_plugin(module_name)
        if clazz is None:
            return None
        try:
            instance = clazz(config or {}, bus=bus)
            LOG.debug(f"Loaded GUI adapter plugin: {module_name}")
            return instance
        except Exception:
            LOG.exception(f"Failed to instantiate GUI adapter plugin: {module_name}")
            return None

    @staticmethod
    def create_all(
        config: Optional[Dict[str, dict]] = None,
        bus=None,
    ) -> List[AbstractGUIPlugin]:
        """Create instances of every installed GUI adapter plugin.

        Args:
            config: Optional dict mapping plugin entry-point names to their
                    individual configuration dicts.
            bus:    Optional :class:`MessageBusClient` instance.

        Returns:
            List of successfully instantiated :class:`AbstractGUIPlugin` objects.
            Plugins that fail to instantiate are skipped and logged.
        """
        plugins = find_gui_adapter_plugins()
        config = config or {}
        instances: List[AbstractGUIPlugin] = []
        for name, clazz in plugins.items():
            plugin_config = config.get(name, {})
            try:
                instance = clazz(plugin_config, bus=bus)
                LOG.info(f"Loaded GUI adapter plugin: {name}")
                instances.append(instance)
            except Exception:
                LOG.exception(f"Failed to instantiate GUI adapter plugin: {name}")
        return instances
