from typing import Optional, Dict, Any, List

from ovos_bus_client import Message
from ovos_bus_client import MessageBusClient
from ovos_bus_client.apis.gui import GUIInterface
from ovos_config import Configuration
from ovos_utils.log import LOG

try:
    from ovos_gui.homescreen import HomescreenManager
except ImportError as _exc:

    class HomescreenManager:
        """Fallback class when ovos-gui is not installed.

        Raises the original ImportError when instantiated to
        provide clear error messaging while still allowing type hints to work.
        """

        def __init__(self, *args, **kwargs):
            LOG.error("you seem to be running GUIExtensions without ovos-gui installed...")
            # raise the original ImportError
            raise _exc


class GUIExtension:
    """ GUI Extension base class

    These plugins are responsible for managing the GUI behaviours
    for specific platforms such as homescreen handling

    only 1 GUIExtension is loaded at any time by ovos-gui service

    Args:
        bus: MessageBus instance
        gui: GUI instance
        preload_gui (bool): load GUI skills even if gui client not connected
        permanent (bool): disable unloading of GUI skills on gui client disconnections
    """

    def __init__(self, config: Dict[str, Any],
                 bus: Optional[MessageBusClient] = None,
                 gui: Optional[GUIInterface] = None,
                 preload_gui: bool = False,
                 permanent: bool = False):

        if not bus:
            bus = MessageBusClient()
            bus.run_in_thread()
            bus.connected_event.wait()
        self.bus: MessageBusClient = bus
        self.gui: GUIInterface = gui or GUIInterface("ovos.shell", bus=self.bus,
                                                     config=Configuration().get("gui", {}))
        self.preload_gui = preload_gui
        self.permanent = permanent
        self.config = config
        self.homescreen_manager: Optional[HomescreenManager] = None
        self.register_bus_events()

    def register_bus_events(self):
        self.bus.on("mycroft.gui.screen.close", self.handle_remove_namespace)

    def bind_homescreen(self, homescreen: Optional[HomescreenManager] = None):
        if self.config.get("homescreen_supported", False):
            if not homescreen:
                LOG.debug("Loading HomescreenManager")
                homescreen = HomescreenManager(self.bus)
                homescreen.daemon = True
                homescreen.start()
            self.homescreen_manager = homescreen
        else:
            LOG.info("Homescreen support not configured")

    def handle_remove_namespace(self, message: Message):
        get_skill_namespace = message.data.get("skill_id", "")
        if get_skill_namespace:
            self.bus.emit(Message("gui.clear.namespace",
                                  {"__from": get_skill_namespace}))


class AbstractGUIPlugin:
    """Base class for GUI adapter plugins.

    Each installed adapter receives every template event simultaneously,
    allowing multiple display backends (Qt, browser, TUI, etc.) to operate
    concurrently.

    Subclass this and implement only the handlers you need; all handlers
    default to no-ops so partial implementations are valid.

    Entry point group: ``opm.gui_adapter``

    Args:
        config: Plugin-specific configuration dict.
        bus:    Optional :class:`MessageBusClient` instance.
    """

    def __init__(self, config: Dict[str, Any], bus: Optional[MessageBusClient] = None):
        self.config = config
        self.bus = bus

    # ------------------------------------------------------------------
    # Template handlers — override in subclasses; all default to no-ops
    # ------------------------------------------------------------------

    def handle_show_idle(self, skill_id: str, data: Dict[str, Any]) -> None:
        pass

    def handle_show_loading(self, skill_id: str, data: Dict[str, Any]) -> None:
        pass

    def handle_show_status(self, skill_id: str, data: Dict[str, Any]) -> None:
        pass

    def handle_show_error(self, skill_id: str, data: Dict[str, Any]) -> None:
        pass

    def handle_show_text(self, skill_id: str, data: Dict[str, Any]) -> None:
        pass

    def handle_show_image(self, skill_id: str, data: Dict[str, Any]) -> None:
        pass

    def handle_show_animated_image(self, skill_id: str, data: Dict[str, Any]) -> None:
        pass

    def handle_show_list(self, skill_id: str, data: Dict[str, Any]) -> None:
        pass

    def handle_show_grid(self, skill_id: str, data: Dict[str, Any]) -> None:
        pass

    def handle_show_table(self, skill_id: str, data: Dict[str, Any]) -> None:
        pass

    def handle_show_html(self, skill_id: str, data: Dict[str, Any]) -> None:
        pass

    def handle_show_url(self, skill_id: str, data: Dict[str, Any]) -> None:
        pass

    def handle_show_audio_player(self, skill_id: str, data: Dict[str, Any]) -> None:
        pass

    def handle_show_video_player(self, skill_id: str, data: Dict[str, Any]) -> None:
        pass

    def handle_show_clock(self, skill_id: str, data: Dict[str, Any]) -> None:
        pass

    def handle_show_timer(self, skill_id: str, data: Dict[str, Any]) -> None:
        pass

    def handle_show_weather(self, skill_id: str, data: Dict[str, Any]) -> None:
        pass

    def handle_show_map(self, skill_id: str, data: Dict[str, Any]) -> None:
        pass

    def handle_show_confirm(self, skill_id: str, data: Dict[str, Any]) -> None:
        pass

    def handle_show_select(self, skill_id: str, data: Dict[str, Any]) -> None:
        pass

    def handle_show_face(self, skill_id: str, data: Dict[str, Any]) -> None:
        pass

    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------

    def on_namespace_activated(self, skill_id: str) -> None:
        """Called when a skill's namespace becomes the active (top) namespace."""
        pass

    def on_namespace_deactivated(self, skill_id: str) -> None:
        """Called when a skill's namespace is cleared or removed."""
        pass

    def on_idle(self) -> None:
        """Called when the GUI returns to the idle/resting state."""
        pass

    # ------------------------------------------------------------------
    # Status event hook
    # ------------------------------------------------------------------

    def on_status_event(self, event_name: str, data: Dict[str, Any]) -> None:
        """Called for well-known system status events forwarded by ovos-gui.

        Examples of *event_name* values: ``"recognizer_loop:wakeword"``,
        ``"speak"``, ``"recognizer_loop:record_begin"``.

        Args:
            event_name: The original bus message type.
            data:       The message payload.
        """
        pass

    # ------------------------------------------------------------------
    # Session data hook
    # ------------------------------------------------------------------

    def on_session_update(self, skill_id: str, data: Dict[str, Any]) -> None:
        """Called whenever a skill sets GUI session data via ``gui.value.set``.

        Args:
            skill_id: Namespace / skill that owns the data.
            data:     Full key/value session data dict (excluding reserved keys).
        """
        pass

    # ------------------------------------------------------------------
    # Template dispatch helper
    # ------------------------------------------------------------------

    _TEMPLATE_HANDLERS: Dict[str, str] = {
        "SYSTEM_idle":           "handle_show_idle",
        "SYSTEM_loading":        "handle_show_loading",
        "SYSTEM_status":         "handle_show_status",
        "SYSTEM_error":          "handle_show_error",
        "SYSTEM_text":           "handle_show_text",
        "SYSTEM_image":          "handle_show_image",
        "SYSTEM_animated_image": "handle_show_animated_image",
        "SYSTEM_list":           "handle_show_list",
        "SYSTEM_grid":           "handle_show_grid",
        "SYSTEM_table":          "handle_show_table",
        "SYSTEM_html":           "handle_show_html",
        "SYSTEM_url":            "handle_show_url",
        "SYSTEM_audio_player":   "handle_show_audio_player",
        "SYSTEM_video_player":   "handle_show_video_player",
        "SYSTEM_clock":          "handle_show_clock",
        "SYSTEM_timer":          "handle_show_timer",
        "SYSTEM_weather":        "handle_show_weather",
        "SYSTEM_map":            "handle_show_map",
        "SYSTEM_confirm":        "handle_show_confirm",
        "SYSTEM_select":         "handle_show_select",
        "SYSTEM_face":           "handle_show_face",
    }

    def dispatch_template(self, template: str, skill_id: str, data: Dict[str, Any]) -> None:
        """Dispatch a template show event to the appropriate handler method.

        Args:
            template: ``PageTemplates`` value (e.g. ``"SYSTEM_weather"``).
            skill_id: ID of the skill requesting display.
            data:     Session data from the namespace at the time of the call.
        """
        handler_name = self._TEMPLATE_HANDLERS.get(template)
        if handler_name:
            handler = getattr(self, handler_name, None)
            if handler:
                try:
                    handler(skill_id, data)
                except Exception:
                    LOG.exception(
                        f"{self.__class__.__name__}.{handler_name} raised an exception"
                    )
        else:
            LOG.warning(f"{self.__class__.__name__}: unknown template '{template}'")
