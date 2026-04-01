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
"""Discovery and configuration utilities for triples-related plugins."""
from typing import Dict, List, Optional, Type, Union

from ovos_config import Configuration
from ovos_utils.log import LOG

from ovos_plugin_manager.templates.triples import (
    TriplesExtractor, TriplesDB, TriplesReasoner
)
from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes


# --- TriplesExtractor helpers ---

def find_triples_plugins() -> Dict[str, Type[TriplesExtractor]]:
    """Find all installed triples-extraction plugins.

    Returns:
        dict mapping plugin entry-point names to plugin classes.
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.TRIPLES)


def load_triples_plugin(module_name: str) -> Optional[Type[TriplesExtractor]]:
    """Get an uninstantiated class for the requested plugin name.

    Args:
        module_name: Plugin entry-point name to load.

    Returns:
        Uninstantiated plugin class, or ``None`` if not found.
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.TRIPLES)


def get_triples_configs() -> Dict[str, List[dict]]:
    """Get valid plugin configurations keyed by plugin name.

    Returns:
        dict mapping plugin names to their list of configuration dicts.
    """
    from ovos_plugin_manager.utils.config import load_configs_for_plugin_type
    return load_configs_for_plugin_type(PluginTypes.TRIPLES)


def get_triples_module_configs(module_name: str) -> Union[Dict[str, list], dict]:
    """Get valid configuration for the specified plugin.

    Args:
        module_name: Plugin entry-point name to get configuration for.

    Returns:
        dict configuration for the plugin (if provided).
    """
    from ovos_plugin_manager.utils.config import load_plugin_configs
    return load_plugin_configs(module_name, PluginConfigTypes.TRIPLES, True)


def get_triples_config(config: Optional[dict] = None) -> dict:
    """Get relevant configuration for triples extractor factory methods.

    Args:
        config: global Configuration OR plugin class-specific configuration

    Returns:
        plugin class-specific configuration
    """
    from ovos_plugin_manager.utils.config import get_plugin_config
    config = config or Configuration()
    return get_plugin_config(config, "triples_extractor")


# --- TriplesStore helpers ---

def find_triples_store_plugins() -> Dict[str, Type[TriplesDB]]:
    """Find all installed triples storage plugins.

    Returns:
        dict mapping plugin entry-point names to plugin classes.
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.TRIPLES_STORE)


def load_triples_store_plugin(module_name: str) -> Optional[Type[TriplesDB]]:
    """Get an uninstantiated class for the requested storage plugin.

    Args:
        module_name: Plugin entry-point name to load.

    Returns:
        Uninstantiated plugin class, or ``None`` if not found.
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.TRIPLES_STORE)


def get_triples_store_configs() -> Dict[str, List[dict]]:
    """Get valid plugin configurations keyed by plugin name.

    Returns:
        dict mapping plugin names to their list of configuration dicts.
    """
    from ovos_plugin_manager.utils.config import load_configs_for_plugin_type
    return load_configs_for_plugin_type(PluginTypes.TRIPLES_STORE)


def get_triples_store_config(config: Optional[dict] = None) -> dict:
    """Get relevant configuration for triples store factory methods.

    Args:
        config: global Configuration OR plugin class-specific configuration

    Returns:
        plugin class-specific configuration
    """
    from ovos_plugin_manager.utils.config import get_plugin_config
    config = config or Configuration()
    return get_plugin_config(config, "triples_store")


# --- TriplesReasoner helpers ---

def find_triples_reasoner_plugins() -> Dict[str, Type[TriplesReasoner]]:
    """Find all installed triples reasoner plugins.

    Returns:
        dict mapping plugin entry-point names to plugin classes.
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.TRIPLES_REASONER)


def load_triples_reasoner_plugin(module_name: str) -> Optional[Type[TriplesReasoner]]:
    """Get an uninstantiated class for the requested reasoner plugin.

    Args:
        module_name: Plugin entry-point name to load.

    Returns:
        Uninstantiated plugin class, or ``None`` if not found.
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.TRIPLES_REASONER)


def get_triples_reasoner_configs() -> Dict[str, List[dict]]:
    """Get valid plugin configurations keyed by plugin name.

    Returns:
        dict mapping plugin names to their list of configuration dicts.
    """
    from ovos_plugin_manager.utils.config import load_configs_for_plugin_type
    return load_configs_for_plugin_type(PluginTypes.TRIPLES_REASONER)


def get_triples_reasoner_config(config: Optional[dict] = None) -> dict:
    """Get relevant configuration for triples reasoner factory methods.

    Args:
        config: global Configuration OR plugin class-specific configuration

    Returns:
        plugin class-specific configuration
    """
    from ovos_plugin_manager.utils.config import get_plugin_config
    config = config or Configuration()
    return get_plugin_config(config, "triples_reasoner")


# --- Factory classes ---

class OVOSTriplesExtractorFactory:
    """Factory for creating TriplesExtractor engines from global configuration.

    Reads mycroft.conf and returns the globally configured plugin.

    Config section key: "triples_extractor"
    Expected config shape:
        "triples_extractor": {
            "module": "<plugin-entry-point>",
            "<plugin-entry-point>": { ... plugin-specific config ... }
        }
    """
    MAPPINGS = {"dummy": "ovos-triples-plugin-dummy"}

    @staticmethod
    def get_class(config: Optional[dict] = None) -> Type[TriplesExtractor]:
        """Factory method to get a TriplesExtractor engine class based on configuration.

        Args:
            config: optional configuration dict

        Returns:
            Uninstantiated plugin class
        """
        config = get_triples_config(config)
        module = config.get("module", "dummy")
        if module in OVOSTriplesExtractorFactory.MAPPINGS:
            module = OVOSTriplesExtractorFactory.MAPPINGS[module]
        return load_triples_plugin(module)

    @staticmethod
    def create(config: Optional[dict] = None) -> TriplesExtractor:
        """Factory method to create a TriplesExtractor engine based on configuration.

        Args:
            config: optional configuration dict

        Returns:
            Instantiated plugin instance
        """
        config = config or get_triples_config()
        plugin = config.get("module") or "dummy"
        plugin_config = config.get(plugin) or {}
        try:
            clazz = OVOSTriplesExtractorFactory.get_class(config)
            return clazz(plugin_config)
        except Exception:
            LOG.exception(f"TriplesExtractor plugin {plugin} could not be loaded!")
            raise


class OVOSTriplesStoreFactory:
    """Factory for creating TriplesDB storage engines from global configuration.

    Reads mycroft.conf and returns the globally configured plugin.

    Config section key: "triples_store"
    Expected config shape:
        "triples_store": {
            "module": "<plugin-entry-point>",
            "<plugin-entry-point>": { ... plugin-specific config ... }
        }
    """
    MAPPINGS = {}

    @staticmethod
    def get_class(config: Optional[dict] = None) -> Type[TriplesDB]:
        """Factory method to get a TriplesDB engine class based on configuration.

        Args:
            config: optional configuration dict

        Returns:
            Uninstantiated plugin class

        Raises:
            ValueError: if no module is configured
        """
        config = get_triples_store_config(config)
        module = config.get("module")
        if not module:
            raise ValueError("No triples_store module configured")
        if module in OVOSTriplesStoreFactory.MAPPINGS:
            module = OVOSTriplesStoreFactory.MAPPINGS[module]
        return load_triples_store_plugin(module)

    @staticmethod
    def create(config: Optional[dict] = None) -> TriplesDB:
        """Factory method to create a TriplesDB engine based on configuration.

        Args:
            config: optional configuration dict

        Returns:
            Instantiated plugin instance

        Raises:
            Exception: if plugin cannot be loaded
        """
        config = config or get_triples_store_config()
        plugin = config.get("module")
        plugin_config = config.get(plugin) or {}
        try:
            clazz = OVOSTriplesStoreFactory.get_class(config)
            return clazz(plugin_config)
        except Exception:
            LOG.exception(f"TriplesStore plugin {plugin} could not be loaded!")
            raise


class OVOSTriplesReasonerFactory:
    """Factory for creating TriplesReasoner engines from global configuration.

    Reads mycroft.conf and returns the globally configured plugin.

    Config section key: "triples_reasoner"
    Expected config shape:
        "triples_reasoner": {
            "module": "<plugin-entry-point>",
            "<plugin-entry-point>": { ... plugin-specific config ... }
        }
    """
    MAPPINGS = {}

    @staticmethod
    def get_class(config: Optional[dict] = None) -> Type[TriplesReasoner]:
        """Factory method to get a TriplesReasoner engine class based on configuration.

        Args:
            config: optional configuration dict

        Returns:
            Uninstantiated plugin class

        Raises:
            ValueError: if no module is configured
        """
        config = get_triples_reasoner_config(config)
        module = config.get("module")
        if not module:
            raise ValueError("No triples_reasoner module configured")
        if module in OVOSTriplesReasonerFactory.MAPPINGS:
            module = OVOSTriplesReasonerFactory.MAPPINGS[module]
        return load_triples_reasoner_plugin(module)

    @staticmethod
    def create(config: Optional[dict] = None) -> TriplesReasoner:
        """Factory method to create a TriplesReasoner engine based on configuration.

        Args:
            config: optional configuration dict

        Returns:
            Instantiated plugin instance

        Raises:
            Exception: if plugin cannot be loaded
        """
        config = config or get_triples_reasoner_config()
        plugin = config.get("module")
        plugin_config = config.get(plugin) or {}
        try:
            clazz = OVOSTriplesReasonerFactory.get_class(config)
            return clazz(plugin_config)
        except Exception:
            LOG.exception(f"TriplesReasoner plugin {plugin} could not be loaded!")
            raise
