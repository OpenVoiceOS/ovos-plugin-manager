"""Discovery + loading for ``opm.media.provider`` plugins.

MediaProvider plugins are the catalog/search layer the OCP pipeline queries
in-process, replacing OCP search skills. See
:mod:`ovos_plugin_manager.templates.media_provider`.
"""
from typing import Dict, List, Optional

from ovos_utils.log import LOG

from ovos_plugin_manager.templates.media_provider import MediaProvider
from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes


def find_media_provider_plugins() -> dict:
    """
    Find all installed media provider plugins
    @return: dict plugin names to entrypoints
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.MEDIA_PROVIDER)


def load_media_provider_plugin(module_name: str) -> type(MediaProvider):
    """
    Get an uninstantiated class for the requested module_name
    @param module_name: Plugin entrypoint name to load
    @return: Uninstantiated class
    """
    from ovos_plugin_manager.utils import load_plugin
    return load_plugin(module_name, PluginTypes.MEDIA_PROVIDER)


def get_media_provider_configs() -> dict:
    """
    Get valid plugin configurations by plugin name
    @return: dict plugin names to list of dict configurations
    """
    from ovos_plugin_manager.utils.config import load_configs_for_plugin_type
    return load_configs_for_plugin_type(PluginTypes.MEDIA_PROVIDER)


def get_media_provider_module_configs(module_name: str) -> List[dict]:
    """
    Get valid configurations for the specified plugin
    @param module_name: plugin to get configuration for
    @return: list of dict configurations
    """
    from ovos_plugin_manager.utils.config import load_plugin_configs
    return load_plugin_configs(module_name, PluginConfigTypes.MEDIA_PROVIDER)


def load_media_providers(config: Optional[dict] = None) -> Dict[str, MediaProvider]:
    """
    Instantiate every installed and enabled media provider plugin.

    A provider is loaded unless it is explicitly disabled in config. Per-provider
    config lives under ``mycroft.conf`` -> ``media_providers`` -> ``<name>``; a
    provider is skipped when its config sets ``"enabled": false``. Runtime
    availability (missing API key, no network, …) is the provider's own concern —
    it simply returns ``[]`` from :meth:`MediaProvider.search`.

    @param config: optional ``media_providers`` config mapping; read from
        ``Configuration()`` when not provided.
    @return: dict of provider name to instantiated provider.
    """
    if config is None:
        try:
            from ovos_config import Configuration
            config = Configuration().get("media_providers", {})
        except Exception:
            config = {}

    providers: Dict[str, MediaProvider] = {}
    for name, clazz in find_media_provider_plugins().items():
        plugin_config = config.get(name, {})
        if plugin_config.get("enabled") is False:
            LOG.debug(f"MediaProvider '{name}' disabled in config")
            continue
        try:
            instance = clazz(config=plugin_config)
            instance.name = instance.name or name
            providers[name] = instance
            LOG.info(f"Loaded MediaProvider plugin: {name}")
        except Exception:
            LOG.exception(f"Failed to load MediaProvider plugin: {name}")
    return providers
