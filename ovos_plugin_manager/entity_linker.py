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
"""Discovery and configuration utilities for entity-linker plugins."""
from typing import Dict, List, Optional, Type

from ovos_config import Configuration
from ovos_utils.log import LOG

from ovos_plugin_manager.templates.triples import EntityLinker
from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes


def find_entity_linker_plugins() -> Dict[str, Type[EntityLinker]]:
    """Find all installed entity-linker plugins.

    Returns:
        dict mapping plugin entry-point names to plugin classes.
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.ENTITY_LINKER)


def load_entity_linker_plugin(module_name: str) -> Optional[Type[EntityLinker]]:
    """Get an uninstantiated class for the requested plugin name.

    Args:
        module_name: Plugin entry-point name to load.

    Returns:
        Uninstantiated plugin class, or ``None`` if not found.
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.ENTITY_LINKER)


def get_entity_linker_configs() -> Dict[str, List[dict]]:
    """Get valid plugin configurations keyed by plugin name.

    Returns:
        dict mapping plugin names to their list of configuration dicts.
    """
    from ovos_plugin_manager.utils.config import load_configs_for_plugin_type
    return load_configs_for_plugin_type(PluginTypes.ENTITY_LINKER)


def get_entity_linker_module_configs(module_name: str) -> dict:
    """Get valid configurations for the specified plugin.

    Args:
        module_name: plugin to get configuration for

    Returns:
        dict configurations for the plugin (if provided)
    """
    from ovos_plugin_manager.utils.config import load_plugin_configs
    return load_plugin_configs(module_name, PluginConfigTypes.ENTITY_LINKER, True)


def get_entity_linker_config(config: Optional[dict] = None) -> dict:
    """Get relevant configuration for entity linker factory methods.

    Args:
        config: global Configuration OR plugin class-specific configuration

    Returns:
        plugin class-specific configuration
    """
    from ovos_plugin_manager.utils.config import get_plugin_config
    config = config or Configuration()
    return get_plugin_config(config, "entity_linker")


class OVOSEntityLinkerFactory:
    """Factory for creating EntityLinker engines from global configuration.

    Reads mycroft.conf and returns the globally configured plugin.

    Config section key: "entity_linker"
    Expected config shape:
        "entity_linker": {
            "module": "<plugin-entry-point>",
            "<plugin-entry-point>": { ... plugin-specific config ... }
        }
    """
    MAPPINGS = {}

    @staticmethod
    def get_class(config: Optional[dict] = None) -> Type[EntityLinker]:
        """Factory method to get an EntityLinker engine class based on configuration.

        Args:
            config: optional configuration dict

        Returns:
            Uninstantiated plugin class

        Raises:
            ValueError: if no module is configured
        """
        config = get_entity_linker_config(config)
        module = config.get("module")
        if not module:
            raise ValueError("No entity_linker module configured")
        if module in OVOSEntityLinkerFactory.MAPPINGS:
            module = OVOSEntityLinkerFactory.MAPPINGS[module]
        return load_entity_linker_plugin(module)

    @staticmethod
    def create(config: Optional[dict] = None) -> EntityLinker:
        """Factory method to create an EntityLinker engine based on configuration.

        Args:
            config: optional configuration dict

        Returns:
            Instantiated plugin instance

        Raises:
            Exception: if plugin cannot be loaded
        """
        config = config or get_entity_linker_config()
        plugin = config.get("module")
        plugin_config = config.get(plugin) or {}
        try:
            clazz = OVOSEntityLinkerFactory.get_class(config)
            return clazz(plugin_config)
        except Exception:
            LOG.exception(f"EntityLinker plugin {plugin} could not be loaded!")
            raise
