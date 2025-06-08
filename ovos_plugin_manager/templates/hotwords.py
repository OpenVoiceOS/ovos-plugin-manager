import abc
from typing import Optional, Dict, Any

from ovos_utils import classproperty
from ovos_utils.process_utils import RuntimeRequirements

from ovos_config import Configuration


def msec_to_sec(msecs):
    """Convert milliseconds to seconds.

    Arguments:
        msecs: milliseconds

    Returns:
        int: input converted from milliseconds to seconds
    """
    return msecs / 1000


class HotWordEngine:
    """Hotword/Wakeword base class to be implemented by all wake word plugins.

    Arguments:
        key_phrase (str): string representation of the wake word
        config (dict): Configuration block for the specific wake word
        lang (str): language code (BCP-47)
    """

    def __init__(self, key_phrase: str, config: Optional[Dict[str, Any]] = None):
        self.key_phrase = str(key_phrase).lower()
        self.config = config or Configuration().get("hotwords", {}).get(self.key_phrase, {})

    @classproperty
    def runtime_requirements(cls):
        """ skill developers should override this if they do not require connectivity
         some examples:
         IOT plugin that controls devices via LAN could return:
            scans_on_init = True
            RuntimeRequirements(internet_before_load=False,
                                 network_before_load=scans_on_init,
                                 requires_internet=False,
                                 requires_network=True,
                                 no_internet_fallback=True,
                                 no_network_fallback=False)
         online search plugin with a local cache:
            has_cache = False
            RuntimeRequirements(internet_before_load=not has_cache,
                                 network_before_load=not has_cache,
                                 requires_internet=True,
                                 requires_network=True,
                                 no_internet_fallback=True,
                                 no_network_fallback=True)
         a fully offline plugin:
            RuntimeRequirements(internet_before_load=False,
                                 network_before_load=False,
                                 requires_internet=False,
                                 requires_network=False,
                                 no_internet_fallback=True,
                                 no_network_fallback=True)
        """
        return RuntimeRequirements(internet_before_load=False,
                                   network_before_load=False,
                                   requires_internet=False,
                                   requires_network=False,
                                   no_internet_fallback=True,
                                   no_network_fallback=True)

    @abc.abstractmethod
    def found_wake_word(self) -> bool:
        """Check if wake word has been found.

        Checks if the wake word has been found. Should reset any internal
        tracking of the wake word state.

        Returns:
            bool: True if a wake word was detected, else False
        """
        raise NotImplementedError()

    def reset(self):
        """
        Reset the WW engine to prepare for a new detection
        """
        pass

    @abc.abstractmethod
    def update(self, chunk):
        """Updates the hotword engine with new audio data.

        The engine should process the data and update internal trigger state.

        Arguments:
            chunk (bytes): Chunk of audio data to process
        """
        raise NotImplementedError()

    def stop(self):
        """
        Perform any actions needed to shut down the wake word engine.
        This may include things such as unloading data or shutdown
        external processes.
        """

    def shutdown(self):
        """
        Compatibility wrapper for `self.stop`
        """
        self.stop()
