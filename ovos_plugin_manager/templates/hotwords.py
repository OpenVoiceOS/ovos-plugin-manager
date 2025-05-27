import abc
from typing import Optional, Dict, Any

from ovos_utils import classproperty
from ovos_utils.process_utils import RuntimeRequirements

from ovos_config import Configuration


def msec_to_sec(msecs):
    """
    Converts a time value from milliseconds to seconds.
    
    Args:
        msecs: Time duration in milliseconds.
    
    Returns:
        The equivalent time in seconds.
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
        """
        Initializes the hotword detection engine with a key phrase and optional configuration.
        
        Args:
            key_phrase: The wake word or phrase to detect, case-insensitive.
            config: Optional dictionary of configuration parameters for the engine. If not provided, configuration is loaded from the global "hotwords" section using the key phrase.
        """
        self.key_phrase = str(key_phrase).lower()
        self.config = config or Configuration().get("hotwords", {}).get(self.key_phrase, {})

    @classproperty
    def runtime_requirements(cls):
        """
        Describes the runtime connectivity requirements for the hotword engine.
        
        By default, indicates that no internet or network connectivity is required before loading or during operation, and that the engine supports fallback modes without connectivity. Subclasses should override this property to specify their own requirements.
        """
        return RuntimeRequirements(internet_before_load=False,
                                   network_before_load=False,
                                   requires_internet=False,
                                   requires_network=False,
                                   no_internet_fallback=True,
                                   no_network_fallback=True)

    @abc.abstractmethod
    def found_wake_word(self) -> bool:
        """
        Determines whether the wake word has been detected.
        
        Should also reset any internal detection state after checking.
        
        Returns:
            True if the wake word was detected; otherwise, False.
        """
        raise NotImplementedError()

    def reset(self):
        """
        Resets the hotword engine state in preparation for new wake word detection.
        
        Intended to be overridden by subclasses if stateful reset is required.
        """
        pass

    @abc.abstractmethod
    def update(self, chunk):
        """
        Processes a chunk of audio data and updates the internal detection state.
        
        Subclasses must implement this method to handle incoming audio data for wake word detection.
        """
        raise NotImplementedError()

    def stop(self):
        """
        Performs shutdown actions for the wake word engine.
        
        This method can be overridden by subclasses to unload resources or stop external processes as needed.
        """

    def shutdown(self):
        """
        Compatibility wrapper for `self.stop`
        """
        self.stop()
