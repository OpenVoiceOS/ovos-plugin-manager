from ovos_plugin_manager.templates.embeddings import EmbeddingsDB, ImageEmbedder, TextEmbedder, VoiceEmbedder, FaceEmbedder
from ovos_plugin_manager.utils import PluginTypes


def find_embeddings_db_plugins() -> dict:
    """
    Discover all installed general embeddings database plugins.
    
    Returns:
        dict: A mapping of plugin names to their entrypoints for general embeddings database plugins.
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.EMBEDDINGS)


def load_embeddings_db_plugin(module_name: str) -> type(EmbeddingsDB):
    """
    Load and return the uninstantiated class of a general embeddings database plugin by its module name.
    
    Parameters:
        module_name (str): The entrypoint name of the embeddings database plugin to load.
    
    Returns:
        type(EmbeddingsDB): The plugin class corresponding to the specified module name.
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.EMBEDDINGS)


def find_voice_embeddings_plugins() -> dict:
    """
    Discover all installed voice embeddings plugins.
    
    Returns:
        dict: A mapping of plugin names to their entrypoints for available voice embeddings plugins.
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.VOICE_EMBEDDINGS)


def load_voice_embeddings_plugin(module_name: str) -> type(VoiceEmbedder):
    """
    Load and return the uninstantiated class of a voice embeddings plugin by its module name.
    
    Parameters:
        module_name (str): The entrypoint name of the voice embeddings plugin to load.
    
    Returns:
        type(VoiceEmbedder): The uninstantiated class of the specified voice embeddings plugin.
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.VOICE_EMBEDDINGS)


def find_image_embeddings_plugins() -> dict:
    """
    Discover all installed image embeddings plugins.
    
    Returns:
        dict: A mapping of plugin names to their entrypoints for image embeddings plugins.
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.IMAGE_EMBEDDINGS)


def load_image_embeddings_plugin(module_name: str) -> type(ImageEmbedder):
    """
    Load and return the uninstantiated class of an image embeddings plugin specified by its module name.
    
    Parameters:
        module_name (str): The entrypoint name of the image embeddings plugin to load.
    
    Returns:
        type(ImageEmbedder): The uninstantiated class of the requested image embeddings plugin.
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.IMAGE_EMBEDDINGS)

def find_face_embeddings_plugins() -> dict:
    """
    Find all installed face embeddings plugins.
    
    Returns:
        dict: A mapping of plugin names to their entrypoints for face embeddings plugins.
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.FACE_EMBEDDINGS)


def load_face_embeddings_plugin(module_name: str) -> type(FaceEmbedder):
    """
    Load and return the uninstantiated class of a face embeddings plugin by its module name.
    
    Parameters:
        module_name (str): The entrypoint name of the face embeddings plugin to load.
    
    Returns:
        type(FaceEmbedder): The uninstantiated class of the specified face embeddings plugin.
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.FACE_EMBEDDINGS)


def find_text_embeddings_plugins() -> dict:
    """
    Discover all installed text embeddings plugins.
    
    Returns:
        dict: A mapping of plugin names to their entrypoints for text embeddings plugins.
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.TEXT_EMBEDDINGS)


def load_text_embeddings_plugin(module_name: str) -> type(TextEmbedder):
    """
    Load and return the uninstantiated class of a text embeddings plugin specified by its module name.
    
    Parameters:
        module_name (str): The entrypoint name of the text embeddings plugin to load.
    
    Returns:
        type(TextEmbedder): The uninstantiated class of the specified text embeddings plugin.
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.TEXT_EMBEDDINGS)
