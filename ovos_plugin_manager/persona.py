import inspect
from typing import Type, Dict, Any, Optional, List, Union

from ovos_plugin_manager.templates.agent_tools import ToolBox
from ovos_plugin_manager.utils import PluginTypes
from ovos_utils.log import LOG


def find_persona_plugins() -> Dict[str, Dict[str, Any]]:
    """
    Find all installed persona definitions
    @return: dict plugin names to entrypoints (persona entrypoint are just dicts)
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.PERSONA)


def find_toolbox_plugins() -> Dict[str, Type[ToolBox]]:
    """
    Find all installed ToolBox plugins.

    @return: dict of toolbox_id to ToolBox subclass
    """
    from ovos_plugin_manager.utils import find_plugins
    return find_plugins(PluginTypes.AGENT_TOOLBOX)


def load_toolbox_plugin(toolbox_id: str,
                        config: Optional[Dict[str, Any]] = None,
                        bus=None) -> Optional[ToolBox]:
    """
    Instantiate one installed ToolBox plugin by its entry-point name.

    The base class takes ``(toolbox_id, config=None, bus=None)``, but plugins
    conventionally hide the id and expose only ``(config=None)``, passing
    their own id up. Callers that guess wrong get a TypeError, so this
    inspects the subclass and passes only what it accepts, then fills in
    ``toolbox_id`` and binds the bus afterwards.

    @param toolbox_id: entry-point name of the toolbox
    @param config: plugin-specific config, passed through if accepted
    @param bus: messagebus client to bind, if the plugin did not bind one
    @return: the ToolBox instance, or None if it is not installed or failed
    """
    plugins = find_toolbox_plugins()
    clazz = plugins.get(toolbox_id)
    if clazz is None:
        LOG.warning(f"ToolBox plugin not installed: {toolbox_id}")
        return None
    try:
        return init_toolbox(clazz, toolbox_id, config=config, bus=bus)
    except Exception:
        LOG.exception(f"Failed to load ToolBox plugin: {toolbox_id}")
        return None


def load_toolbox_plugins(toolbox_ids: Optional[List[str]] = None,
                         config: Optional[Dict[str, Any]] = None,
                         bus=None) -> List[ToolBox]:
    """
    Instantiate several ToolBox plugins, skipping any that fail.

    @param toolbox_ids: entry-point names to load, or None for all installed
    @param config: mapping of toolbox_id to that plugin's config
    @param bus: messagebus client to bind to each toolbox
    @return: list of successfully loaded ToolBox instances
    """
    config = config or {}
    if toolbox_ids is None:
        toolbox_ids = list(find_toolbox_plugins())
    toolboxes = []
    for tid in toolbox_ids:
        tb = load_toolbox_plugin(tid, config=config.get(tid, {}), bus=bus)
        if tb is not None:
            toolboxes.append(tb)
    return toolboxes


def init_toolbox(clazz: Type[ToolBox], toolbox_id: str,
                 config: Optional[Dict[str, Any]] = None,
                 bus=None) -> ToolBox:
    """
    Construct a ToolBox subclass without assuming its __init__ signature.

    Every loader in the ecosystem called this differently — one passed
    ``toolbox_id`` alone, others passed ``config`` and ``bus`` — and every
    shipped plugin rejected at least one of those shapes. Rather than force a
    signature on plugins that already exist, pass each keyword only if the
    subclass declares it (or accepts ``**kwargs``), then set what was skipped.

    @param clazz: the ToolBox subclass
    @param toolbox_id: entry-point name, used if the plugin does not set one
    @param config: plugin-specific config
    @param bus: messagebus client to bind, if the plugin did not bind one
    @return: the constructed ToolBox
    """
    try:
        params = inspect.signature(clazz.__init__).parameters
    except (TypeError, ValueError):  # builtins / C extensions
        params = {}
    takes_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD
                       for p in params.values())

    kwargs = {}
    for name, value in (("toolbox_id", toolbox_id), ("config", config),
                        ("bus", bus)):
        if value is None and name != "toolbox_id":
            continue
        if name in params or takes_kwargs:
            kwargs[name] = value

    toolbox = clazz(**kwargs)

    # a plugin that hides toolbox_id sets its own, usually as a class
    # attribute; only fill in the entry-point name when it did not
    if not getattr(toolbox, "toolbox_id", None):
        toolbox.toolbox_id = toolbox_id
    if bus is not None and getattr(toolbox, "bus", None) is None:
        toolbox.bind(bus)
    return toolbox
