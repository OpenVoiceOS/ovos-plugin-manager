import abc

from ovos_utils import classproperty
from ovos_utils.process_utils import RuntimeRequirements


class Audio2IPA:

    def __init__(self, config=None):
        """
        Initializes the Audio2IPA instance with an optional configuration.
        
        Args:
            config: Optional dictionary of configuration parameters. If not provided, an empty dictionary is used.
        """
        self.config = config or {}

    @classproperty
    def runtime_requirements(cls):
        """
        Specifies the runtime connectivity requirements for the plugin.
        
        Returns:
            A RuntimeRequirements object indicating that no internet or network connectivity
            is required before or during runtime, and that fallback behavior is allowed
            when offline or without network.
        
        Subclasses should override this property to declare their specific connectivity
        needs, such as requiring network access for device control or internet access
        for online services.
        """
        return RuntimeRequirements(internet_before_load=False,
                                   network_before_load=False,
                                   requires_internet=False,
                                   requires_network=False,
                                   no_internet_fallback=True,
                                   no_network_fallback=True)

    @abc.abstractmethod
    def get_ipa(self, audio_data):
        raise NotImplementedError
