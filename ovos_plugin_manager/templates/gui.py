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
        """
        Handle removal of a GUI namespace when a skill signals its screen was closed.
        
        If the incoming message contains a "skill_id" in its data, emits a "gui.clear.namespace" message with "__from" set to that skill id.
        
        Parameters:
            message (Message): Bus message expected to include `data["skill_id"]` with the skill namespace to clear.
        """
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
        """
        Initialize the GUI plugin with its configuration and an optional message bus client.
        
        Parameters:
            config (Dict[str, Any]): Plugin-specific configuration.
            bus (Optional[MessageBusClient]): Optional message bus client used to send and receive GUI events; may be None.
        """
        self.config = config
        self.bus = bus

    # ------------------------------------------------------------------
    # Template handlers — override in subclasses; all default to no-ops
    # ------------------------------------------------------------------

    def handle_show_idle(self, skill_id: str, data: Dict[str, Any]) -> None:
        """
        Handle the "SYSTEM_idle" template for a skill's namespace.
        
        Override to react when a skill displays the idle template (e.g., clear UI or show default state).
        
        Parameters:
            skill_id (str): Identifier or namespace of the skill emitting the template.
            data (Dict[str, Any]): Template payload and metadata.
        """
        pass

    def handle_show_loading(self, skill_id: str, data: Dict[str, Any]) -> None:
        """
        Handle a request to display the GUI "loading" template for the given skill.
        
        Parameters:
            skill_id (str): Skill namespace or identifier that originated the template.
            data (Dict[str, Any]): Template payload and metadata provided by the skill.
        """
        pass

    def handle_show_status(self, skill_id: str, data: Dict[str, Any]) -> None:
        """
        Handle a "status" template event for the given skill.
        
        Parameters:
        	skill_id (str): Identifier or namespace of the skill that emitted the template.
        	data (Dict[str, Any]): Payload associated with the status template containing event details.
        """
        pass

    def handle_show_error(self, skill_id: str, data: Dict[str, Any]) -> None:
        """
        Handle an incoming "SYSTEM_error" template event for a skill (no-op by default).
        
        Parameters:
            skill_id (str): Identifier of the skill that emitted the template.
            data (Dict[str, Any]): Template payload containing error details and presentation data.
        """
        pass

    def handle_show_text(self, skill_id: str, data: Dict[str, Any]) -> None:
        """
        Handle a text-based GUI template for the given skill.
        
        Default no-op implementation; override in subclasses to render or process text templates.
        
        Parameters:
        	skill_id (str): Namespace of the skill that sent the template.
        	data (Dict[str, Any]): Template payload for the text display (e.g., keys like "text", "title", "subtitle", and other metadata).
        """
        pass

    def handle_show_image(self, skill_id: str, data: Dict[str, Any]) -> None:
        """
        Handle a request to display an image template.
        
        Default implementation is a no-op; subclasses should override to render or process image templates for the given skill.
        
        Parameters:
            skill_id (str): Identifier or namespace of the originating skill.
            data (Dict[str, Any]): Template payload for the image (e.g., URL, caption, metadata).
        """
        pass

    def handle_show_animated_image(self, skill_id: str, data: Dict[str, Any]) -> None:
        """
        Handle an animated image template event for a skill.
        
        Parameters:
            skill_id (str): Unique namespace or identifier of the skill that sent the template.
            data (Dict[str, Any]): Template payload sent by the skill (e.g., image source, animation settings, metadata).
        
        Description:
            Default no-op implementation; subclasses should override to render or process animated-image templates.
        """
        pass

    def handle_show_list(self, skill_id: str, data: Dict[str, Any]) -> None:
        """
        Handle presentation of a list template emitted by a skill.
        
        This default no-op implementation receives the originating skill's namespace and the template payload; subclasses should override to render or process the list items and related metadata.
        
        Parameters:
            skill_id (str): Namespace or identifier of the skill that emitted the template.
            data (Dict[str, Any]): Template payload containing list items and any associated metadata (e.g., title, description, actions).
        """
        pass

    def handle_show_grid(self, skill_id: str, data: Dict[str, Any]) -> None:
        """
        Handle a "grid" GUI template for a given skill.
        
        Parameters:
            skill_id (str): Identifier of the skill that originated the template.
            data (Dict[str, Any]): Template payload containing grid items and presentation metadata.
        """
        pass

    def handle_show_table(self, skill_id: str, data: Dict[str, Any]) -> None:
        """
        Handle a "SYSTEM_table" template event for a skill.
        
        Called when a table template is dispatched. The default implementation is a no-op and should be overridden by subclasses to render or process table content.
        
        Parameters:
            skill_id (str): Namespace or identifier of the originating skill.
            data (Dict[str, Any]): Template payload containing table rows, columns, and related metadata.
        """
        pass

    def handle_show_html(self, skill_id: str, data: Dict[str, Any]) -> None:
        """
        Handle an HTML template display request originating from a skill.
        
        This default implementation performs no action; subclasses should override to render or process the provided HTML template.
        
        Parameters:
            skill_id (str): Identifier of the skill that emitted the template.
            data (Dict[str, Any]): Template payload containing HTML and related metadata (e.g., `html`, `title`, `style`).
        """
        pass

    def handle_show_url(self, skill_id: str, data: Dict[str, Any]) -> None:
        """
        Handle a request to display a URL template for a skill.
        
        Parameters:
            skill_id (str): Identifier of the skill emitting the template.
            data (Dict[str, Any]): Template payload; typically includes a 'url' key and may contain display metadata (title, thumbnail, headers, etc.).
        
        Notes:
            Default implementation is a no-op; subclasses should override to render or process the URL template.
        """
        pass

    def handle_show_audio_player(self, skill_id: str, data: Dict[str, Any]) -> None:
        """
        Handle display or update events for the "SYSTEM_audio_player" template.
        
        Override to respond to audio player template events (playback state, track metadata, controls). 
        
        Parameters:
        	skill_id (str): Namespace or skill identifier that emitted the template.
        	data (Dict[str, Any]): Template payload containing audio player state and associated metadata.
        """
        pass

    def handle_show_video_player(self, skill_id: str, data: Dict[str, Any]) -> None:
        """
        Handle a request to display a video player template.
        
        Default no-op implementation; subclasses should override to present or control a video player when a video player template is dispatched.
        
        Parameters:
            skill_id (str): Skill namespace originating the template.
            data (Dict[str, Any]): Template payload containing video metadata and playback instructions (e.g., source URL, title, autoplay, controls).
        """
        pass

    def handle_show_clock(self, skill_id: str, data: Dict[str, Any]) -> None:
        """
        Handle a request to display a clock template.
        
        Called when the system requests showing a clock UI. Implementations should use `skill_id` to scope or namespace the display and use `data` for the template payload (e.g., time, timezone, style).
        
        Parameters:
            skill_id (str): Identifier of the skill that owns the template namespace.
            data (Dict[str, Any]): Template payload containing clock-specific fields.
        """
        pass

    def handle_show_timer(self, skill_id: str, data: Dict[str, Any]) -> None:
        """
        Handle a "timer" template event emitted by a skill.
        
        Parameters:
            skill_id (str): Unique identifier of the skill that sent the template.
            data (Dict[str, Any]): Template payload containing timer details (e.g., remaining time, state, labels).
        """
        pass

    def handle_show_weather(self, skill_id: str, data: Dict[str, Any]) -> None:
        """
        Handle a weather template update for the given skill namespace.
        
        Parameters:
            skill_id (str): Skill namespace sending the weather template.
            data (Dict[str, Any]): Template payload containing weather information (e.g., forecast, current conditions, units).
        """
        pass

    def handle_show_map(self, skill_id: str, data: Dict[str, Any]) -> None:
        """
        Handle a request to display a map template for a skill.
        
        Called when a map template is dispatched to this plugin. Subclasses should override to render or otherwise process map data coming from the skill.
        
        Parameters:
            skill_id (str): Skill namespace or identifier that issued the template.
            data (Dict[str, Any]): Template payload containing map parameters (for example: center coordinates, zoom level, markers, and provider-specific options).
        """
        pass

    def handle_show_confirm(self, skill_id: str, data: Dict[str, Any]) -> None:
        """
        Handle a "confirm" template event emitted by a skill.
        
        Parameters:
            skill_id (str): The originating skill's namespace or identifier.
            data (Dict[str, Any]): Payload for the confirmation template (dialog text, buttons, metadata) used to present the confirmation UI.
        """
        pass

    def handle_show_select(self, skill_id: str, data: Dict[str, Any]) -> None:
        """
        Handle a "select" template event, intended to present a choice list to the user.
        
        Parameters:
            skill_id (str): Identifier of the skill that emitted the template; can be used to scope session or namespace.
            data (Dict[str, Any]): Template payload containing selection details (e.g., items, title, metadata) to be rendered by the GUI adapter.
        """
        pass

    def handle_show_face(self, skill_id: str, data: Dict[str, Any]) -> None:
        """
        Handle a "face" template event for a GUI adapter.
        
        Parameters:
            skill_id (str): Namespace or skill identifier that emitted the template.
            data (Dict[str, Any]): Payload of the template containing display details (e.g., face id, expressions, timing).
        """
        pass

    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------

    def on_namespace_activated(self, skill_id: str) -> None:
        """
        Hook invoked when a skill's namespace becomes the active (top) namespace.
        
        Plugins should override this method to perform any setup required when the given
        skill's namespace is activated.
        
        Parameters:
            skill_id (str): Identifier of the skill whose namespace was activated.
        """
        pass

    def on_namespace_deactivated(self, skill_id: str) -> None:
        """Called when a skill's namespace is cleared or removed."""
        pass

    def on_idle(self) -> None:
        """
        Hook invoked when the GUI enters the idle (resting) state.
        """
        pass

    # ------------------------------------------------------------------
    # Status event hook
    # ------------------------------------------------------------------

    def on_status_event(self, event_name: str, data: Dict[str, Any]) -> None:
        """
        Handle well-known system status events forwarded by ovos-gui.
        
        Examples of event_name values: "recognizer_loop:wakeword", "speak", "recognizer_loop:record_begin".
        
        Parameters:
            event_name (str): The original bus message type.
            data (Dict[str, Any]): The message payload.
        """
        pass

    # ------------------------------------------------------------------
    # Session data hook
    # ------------------------------------------------------------------

    def on_session_update(self, skill_id: str, data: Dict[str, Any]) -> None:
        """
        Hook invoked when a skill updates its GUI session data.
        
        Parameters:
            skill_id (str): Namespace/skill that owns the session data.
            data (Dict[str, Any]): Full key/value session data dictionary set by the skill (excludes reserved keys).
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
        """
        Route a template event to the corresponding handler method.
        
        Parameters:
            template (str): Template identifier (e.g. "SYSTEM_weather") that selects the handler.
            skill_id (str): ID of the skill requesting the display; passed to the handler.
            data (Dict[str, Any]): Session data for the namespace at the time of dispatch; passed to the handler.
        
        Notes:
            If no handler is registered for `template`, the call is ignored. Exceptions raised by a handler are caught and logged.
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
