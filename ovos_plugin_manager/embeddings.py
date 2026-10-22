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
"""Discovery utilities for embeddings plugins (text, voice, image, face, general)."""
from typing import Dict, Optional, Type

from ovos_plugin_manager.templates.embeddings import EmbeddingsDB, ImageEmbedder, TextEmbedder, VoiceEmbedder, FaceEmbedder
from ovos_plugin_manager.utils import PluginTypes


def find_embeddings_db_plugins() -> Dict[str, Type[EmbeddingsDB]]:
    """Find all installed general embeddings database plugins.

    Returns:
        dict mapping plugin entry-point names to plugin classes.
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.EMBEDDINGS)


def load_embeddings_db_plugin(module_name: str) -> Optional[Type[EmbeddingsDB]]:
    """Get an uninstantiated class for the requested embeddings DB plugin.

    Args:
        module_name: Plugin entry-point name to load.

    Returns:
        Uninstantiated plugin class, or ``None`` if not found.
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.EMBEDDINGS)


def find_voice_embeddings_plugins() -> Dict[str, Type[VoiceEmbedder]]:
    """Find all installed voice embeddings plugins.

    Returns:
        dict mapping plugin entry-point names to plugin classes.
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.VOICE_EMBEDDINGS)


def load_voice_embeddings_plugin(module_name: str) -> Optional[Type[VoiceEmbedder]]:
    """Get an uninstantiated class for the requested voice embeddings plugin.

    Args:
        module_name: Plugin entry-point name to load.

    Returns:
        Uninstantiated plugin class, or ``None`` if not found.
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.VOICE_EMBEDDINGS)


def find_image_embeddings_plugins() -> Dict[str, Type[ImageEmbedder]]:
    """Find all installed image embeddings plugins.

    Returns:
        dict mapping plugin entry-point names to plugin classes.
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.IMAGE_EMBEDDINGS)


def load_image_embeddings_plugin(module_name: str) -> Optional[Type[ImageEmbedder]]:
    """Get an uninstantiated class for the requested image embeddings plugin.

    Args:
        module_name: Plugin entry-point name to load.

    Returns:
        Uninstantiated plugin class, or ``None`` if not found.
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.IMAGE_EMBEDDINGS)


def find_face_embeddings_plugins() -> Dict[str, Type[FaceEmbedder]]:
    """Find all installed face embeddings plugins.

    Returns:
        dict mapping plugin entry-point names to plugin classes.
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.FACE_EMBEDDINGS)


def load_face_embeddings_plugin(module_name: str) -> Optional[Type[FaceEmbedder]]:
    """Get an uninstantiated class for the requested face embeddings plugin.

    Args:
        module_name: Plugin entry-point name to load.

    Returns:
        Uninstantiated plugin class, or ``None`` if not found.
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.FACE_EMBEDDINGS)


def find_text_embeddings_plugins() -> Dict[str, Type[TextEmbedder]]:
    """Find all installed text embeddings plugins.

    Returns:
        dict mapping plugin entry-point names to plugin classes.
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.TEXT_EMBEDDINGS)


def load_text_embeddings_plugin(module_name: str) -> Optional[Type[TextEmbedder]]:
    """Get an uninstantiated class for the requested text embeddings plugin.

    Args:
        module_name: Plugin entry-point name to load.

    Returns:
        Uninstantiated plugin class, or ``None`` if not found.
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.TEXT_EMBEDDINGS)
