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
"""Discovery, loading, and factory helpers for voice-clone plugins (``opm.vc``)."""
from typing import Dict, Optional, Type

from ovos_plugin_manager.templates.vc import VoiceClonePlugin
from ovos_plugin_manager.utils import PluginTypes
from ovos_utils.log import LOG


def find_voice_clone_plugins() -> Dict[str, Type[VoiceClonePlugin]]:
    """Find all installed voice-clone plugins.

    Returns:
        dict mapping plugin entry-point names to plugin classes.
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.VOICE_CLONE)


def load_voice_clone_plugin(module_name: str) -> Optional[Type[VoiceClonePlugin]]:
    """Get an uninstantiated class for the requested voice-clone plugin.

    Args:
        module_name: Plugin entry-point name to load.

    Returns:
        Uninstantiated plugin class, or ``None`` if not found.
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.VOICE_CLONE)


def get_voice_clone_config(config: Optional[dict] = None,
                           module: Optional[str] = None) -> dict:
    """Get relevant configuration for factory methods.

    Args:
        config: Global ``mycroft.conf`` config dict, or a plugin-specific
            config dict already scoped to the ``voice_clone`` section.
        module: Voice-clone module name to retrieve config for.

    Returns:
        Plugin-specific configuration dict with at least a ``module`` key.
    """
    from ovos_plugin_manager.utils.config import get_plugin_config
    return get_plugin_config(config, "voice_clone", module)


class OVOSVoiceClonerFactory:
    """Factory for instantiating voice-clone plugins from configuration.

    Configuration is read from the ``voice_clone`` section of
    ``mycroft.conf``::

        "voice_clone": {
            "module": "my-vc-plugin",
            "my-vc-plugin": {
                ...plugin-specific keys...
            }
        }
    """

    @staticmethod
    def get_class(config: Optional[dict] = None) -> Optional[Type[VoiceClonePlugin]]:
        """Return the plugin class specified by *config*.

        Args:
            config: Global or section-scoped configuration.  The
                ``module`` key must be present (or resolvable via
                :func:`get_voice_clone_config`).

        Returns:
            Uninstantiated :class:`~ovos_plugin_manager.templates.vc.VoiceClonePlugin`
            subclass, or ``None`` if not found.
        """
        vc_config = get_voice_clone_config(config)
        module = vc_config.get("module")
        if not module:
            return None
        return load_voice_clone_plugin(module)

    @staticmethod
    def create(config: Optional[dict] = None) -> VoiceClonePlugin:
        """Instantiate and return the configured voice-clone plugin.

        Args:
            config: Global or section-scoped configuration.

        Returns:
            An initialised :class:`~ovos_plugin_manager.templates.vc.VoiceClonePlugin`.

        Raises:
            RuntimeError: If the plugin class cannot be loaded.
        """
        vc_config = get_voice_clone_config(config)
        module = vc_config.get("module")
        plugin_config = vc_config.get(module) or {}
        try:
            clazz = OVOSVoiceClonerFactory.get_class(vc_config)
            if clazz is None:
                raise RuntimeError(f"Voice-clone plugin '{module}' could not be found.")
            return clazz(plugin_config)
        except Exception:
            LOG.exception(f"The selected voice-clone plugin '{module}' could not be loaded!")
            raise
