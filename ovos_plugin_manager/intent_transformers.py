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
"""Discovery utilities for ``opm.intent_transformer`` plugins."""
from typing import Dict, Optional, Type

from ovos_plugin_manager.templates.transformers import IntentTransformer
from ovos_plugin_manager.utils import PluginTypes


def find_intent_transformer_plugins() -> Dict[str, Type[IntentTransformer]]:
    """Find all installed intent-transformer plugins.

    Returns:
        dict mapping plugin entry-point names to plugin classes.
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.INTENT_TRANSFORMER)


def load_intent_transformer_plugin(module_name: str) -> Optional[Type[IntentTransformer]]:
    """Get an uninstantiated class for the requested plugin name.

    Args:
        module_name: Plugin entry-point name to load.

    Returns:
        Uninstantiated plugin class, or ``None`` if not found.
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.INTENT_TRANSFORMER)
