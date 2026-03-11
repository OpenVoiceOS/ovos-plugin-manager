from typing import Optional, Dict, Any

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
