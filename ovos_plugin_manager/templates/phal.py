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
    This base class is intended to be used to build PHAL plugins, which run
    inside the ``ovos-PHAL`` service and react to lifecycle bus events
    (audio in/out, wake, sleep, speak).
    All of the handlers are optional and for convenience only.

    The legacy Mark-1 ``enclosure.*`` hardware protocol is no longer wired
    here. Hardware enclosure plugins mix in ``EnclosureProtocolListener`` from
    ``ovos-ui-enclosure-protocol`` instead.
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

        self.register_core_events()
        self.start()

    def register_core_events(self):
        # audio events
        self.bus.on('recognizer_loop:record_begin', self.on_record_begin)
        self.bus.on('recognizer_loop:record_end', self.on_record_end)
        self.bus.on("recognizer_loop:sleep", self.on_sleep)
        self.bus.on('recognizer_loop:audio_output_start', self.on_audio_output_start)
        self.bus.on('recognizer_loop:audio_output_end', self.on_audio_output_end)
        self.bus.on("mycroft.awoken", self.on_awake)
        self.bus.on("speak", self.on_speak)

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
        self.bus.remove("mycroft.awoken", self.on_awake)
        self.bus.remove("recognizer_loop:sleep", self.on_sleep)
        self.bus.remove("speak", self.on_speak)
        self.bus.remove('recognizer_loop:record_begin', self.on_record_begin)
        self.bus.remove('recognizer_loop:record_end', self.on_record_end)
        self.bus.remove('recognizer_loop:audio_output_start', self.on_audio_output_start)
        self.bus.remove('recognizer_loop:audio_output_end', self.on_audio_output_end)

        self._running = False

    def run(self):
        ''' plugin main loop, override if needed '''
        pass

    # Audio Events
    def on_record_begin(self, message=None):
        ''' listening started '''
        pass

    def on_record_end(self, message=None):
        ''' listening ended '''
        pass

    def on_audio_output_start(self, message=None):
        ''' speaking started '''
        pass

    def on_audio_output_end(self, message=None):
        ''' speaking started '''
        pass

    def on_awake(self, message=None):
        ''' on wakeup animation '''
        pass

    def on_sleep(self, message=None):
        ''' on naptime animation '''
        # TODO naptime skill animation should be ond here
        pass

    def on_speak(self, message=None):
        ''' on speak messages, intended for enclosures that disregard
        visemes '''
        pass

class AdminPlugin(PHALPlugin):
    """Running as Admin"""

class AdminValidator(PHALValidator):
    """Running as Admin"""
