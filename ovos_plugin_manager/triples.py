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
from typing import Dict, Optional, Type

from ovos_plugin_manager.templates.triples import TriplesExtractor, TriplesDB, TriplesReasoner, EntityLinker
from ovos_plugin_manager.utils import PluginTypes


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


# --- EntityLinker helpers ---


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
