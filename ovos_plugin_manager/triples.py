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
"""Discovery and configuration utilities for triples-extraction plugins."""
from typing import Dict, List, Optional, Type, Union

from ovos_plugin_manager.templates.triples import TriplesExtractor
from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes


def find_triples_plugins() -> Dict[str, Type[TriplesExtractor]]:
    """Find all installed triples-extraction plugins.

    Returns:
        dict mapping plugin entry-point names to plugin classes.
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.COREFERENCE_SOLVER)


def load_triples_plugin(module_name: str) -> Optional[Type[TriplesExtractor]]:
    """Get an uninstantiated class for the requested plugin name.

    Args:
        module_name: Plugin entry-point name to load.

    Returns:
        Uninstantiated plugin class, or ``None`` if not found.
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.COREFERENCE_SOLVER)


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
