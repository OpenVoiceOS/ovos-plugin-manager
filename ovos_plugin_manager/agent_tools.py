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
"""Discovery/loading utilities and factory for ToolBox agent plugins.

Entry point group: ``opm.agents.toolbox``
Config group: ``opm.agents.toolbox.config`` (:attr:`PluginConfigTypes.AGENT_TOOLBOX`)
"""
from typing import Any, Dict, Optional, Type, Union

from ovos_bus_client import MessageBusClient
from ovos_config import Configuration
from ovos_utils.fakebus import FakeBus
from ovos_utils.log import LOG

from ovos_plugin_manager.templates.agent_tools import ToolBox
from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes


def find_toolbox_plugins() -> Dict[str, Type[ToolBox]]:
    """
    Find all installed ToolBox plugins
    @return: dict plugin names to uninstantiated ToolBox classes
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.AGENT_TOOLBOX)


def load_toolbox_plugin(module_name: str) -> Type[ToolBox]:
    """
    Get an uninstantiated class for the requested module_name
    @param module_name: Plugin entrypoint name to load
    @return: Uninstantiated ToolBox class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.AGENT_TOOLBOX)


def get_toolbox_configs() -> dict:
    """
    Get a dict of plugin names to valid ToolBox configurations
    @return: dict plugin name to list of dict configurations
    """
    from ovos_plugin_manager.utils.config import load_configs_for_plugin_type
    return load_configs_for_plugin_type(PluginTypes.AGENT_TOOLBOX)


def get_toolbox_module_configs(module_name: str) -> dict:
    """
    Get valid configurations for the specified ToolBox plugin
    @param module_name: plugin to get configuration for
    @return: dict configurations for the plugin
    """
    from ovos_plugin_manager.utils.config import load_plugin_configs
    cfgs = load_plugin_configs(module_name, PluginConfigTypes.AGENT_TOOLBOX)
    return {module_name: cfgs} if isinstance(cfgs, list) else cfgs


def get_toolbox_config(config: Optional[dict] = None) -> dict:
    """
    Get relevant configuration for factory methods
    @param config: global Configuration OR plugin class-specific configuration
    @return: plugin class-specific configuration (with `module` resolved,
             merged with the global `agent_toolbox`-level defaults)
    """
    from ovos_plugin_manager.utils.config import get_plugin_config
    config = config or Configuration()
    if "agent_toolbox" in config:
        config = get_plugin_config(config, "agent_toolbox")
    return config


class OVOSToolBoxFactory:
    """Factory for instantiating ToolBox plugins from configuration."""

    @staticmethod
    def get_class(config: Optional[dict] = None) -> Type[ToolBox]:
        """Factory method to get a ToolBox class based on configuration.

        The configuration file ``mycroft.conf`` contains an ``agent_toolbox``
        section with the name of a ToolBox module to be read by this method.

        "agent_toolbox": {
            "module": <plugin_name>
        }
        """
        config = get_toolbox_config(config)
        module = config.get("module")
        if not module:
            raise ValueError(f"ToolBox plugin not configured in: {config}")
        return load_toolbox_plugin(module)

    @classmethod
    def create(cls, config: Optional[dict] = None,
               bus: Optional[Union[MessageBusClient, FakeBus]] = None) -> ToolBox:
        """Factory method to create a ToolBox instance based on configuration.

        The configuration file ``mycroft.conf`` contains an ``agent_toolbox``
        section with the name of a ToolBox module to be read by this method.

        "agent_toolbox": {
            "module": <plugin_name>,
            "<plugin_name>": {...plugin specific config...}
        }

        @param config: global Configuration OR plugin class-specific configuration
        @param bus: optional MessageBusClient/FakeBus to bind the ToolBox to
        @return: instantiated ToolBox plugin
        """
        config = config or Configuration()
        if "agent_toolbox" in config:
            config = config["agent_toolbox"]
        module = config.get("module")
        if not module:
            raise ValueError(f"ToolBox plugin not configured in: {config}")
        plugin_config = config.get(module, {})
        try:
            clazz = load_toolbox_plugin(module)
            return clazz(config=plugin_config, bus=bus)
        except Exception:
            LOG.exception(f"ToolBox plugin {module} could not be loaded!")
            raise


def create(config: Optional[dict] = None,
           bus: Optional[Union[MessageBusClient, FakeBus]] = None) -> ToolBox:
    """
    Module-level convenience factory, equivalent to ``OVOSToolBoxFactory.create``.
    @param config: global Configuration OR plugin class-specific configuration
    @param bus: optional MessageBusClient/FakeBus to bind the ToolBox to
    @return: instantiated ToolBox plugin
    """
    return OVOSToolBoxFactory.create(config, bus)
