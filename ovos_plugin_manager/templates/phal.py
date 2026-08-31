from threading import Thread
from typing import Optional

from ovos_bus_client.message import Message
from ovos_config import Configuration
from ovos_utils import camel_case_split
from ovos_utils import classproperty
from ovos_utils.log import LOG
from ovos_bus_client.util import get_mycroft_bus
from ovos_utils.process_utils import RuntimeRequirements


class PHALValidator:
    @staticmethod
    def validate(config: dict = None) -> bool:
        """
        This method is called before loading the plugin. If it returns False,
        the plugin is not loaded. This allows a plugin to run platform checks
        @param config: dict configuration for this plugin
        @return: True if plugin is enabled, else False
        """
        config = config or dict()
        return config.get("enabled", True) is True


class PHALPlugin(Thread):
    """
    Base class for PHAL plugins, which run inside the ``ovos-PHAL`` service.

    A PHAL plugin is a background ``Thread`` with access to the message bus
    (``self.bus``); subclasses wire their own bus handlers and override
    :meth:`run` for any main loop.

    This base does not wire any bus events. Hardware enclosure plugins mix in
    ``EnclosureProtocolListener`` from ``ovos-ui-enclosure-protocol`` for the
    ``enclosure.*`` commands and the record/speak/wake/sleep lifecycle.
    """
    validator = PHALValidator

    def __init__(self, bus=None, name="", config=None):
        super().__init__(daemon=True)
        self.config_core = Configuration()
        name = name or camel_case_split(self.__class__.__name__).replace(" ", "-").lower()
        self.config = config or self.config_core.get("PHAL", {}).get(name, {})
        self._running = False
        self.bus = bus or get_mycroft_bus()
        self.log = LOG
        self.name = name
        self.start()

    @classproperty
    def runtime_requirements(cls):
        """
        Provide the plugin's runtime connectivity requirements; subclasses should override to declare different needs.
        
        This default indicates the plugin does not require internet or network before load or at runtime and that both no-internet and no-network fallbacks are allowed. Subclasses can return a RuntimeRequirements instance with different flags to express their specific connectivity and fallback requirements.
        
        Returns:
            RuntimeRequirements: Instance describing internet/network requirements and fallback behaviour.
        """
        return RuntimeRequirements(internet_before_load=False,
                                   network_before_load=False,
                                   requires_internet=False,
                                   requires_network=False,
                                   no_internet_fallback=True,
                                   no_network_fallback=True)

    def emit(self, msg_type: str, msg_data: Optional[dict] = None) -> None:
        """
        Emit a bus message scoped to this plugin under the topic 'ovos.PHAL.<name>.<msg_type>'.
        
        Parameters:
            msg_type (str): Message type suffix (e.g., "ready").
            msg_data (Optional[dict]): Optional payload to include in the message.
        """
        skill_id = f"ovos.PHAL.{self.name}"
        LOG.info(f"{skill_id}.{msg_type}")
        self.bus.emit(Message(f"{skill_id}.{msg_type}", msg_data, {"skill_id": skill_id}))

    def shutdown(self):
        self._running = False

    def run(self):
        ''' plugin main loop, override if needed '''
        pass


class AdminPlugin(PHALPlugin):
    """Running as Admin"""

class AdminValidator(PHALValidator):
    """Running as Admin"""
