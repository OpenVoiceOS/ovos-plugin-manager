import abc
from typing import Optional, List
from ovos_utils import classproperty
from ovos_utils.process_utils import RuntimeRequirements


class OCPStreamExtractor:

    def __init__(self, ocp_settings=None):
        """
        Initializes the OCPStreamExtractor with optional settings.
        
        Args:
            ocp_settings: Optional dictionary of settings for the extractor. Defaults to an empty dictionary if not provided.
        """
        self.ocp_settings = ocp_settings or {}

    @classproperty
    def runtime_requirements(cls):
        """
        Specifies the runtime connectivity requirements for the extractor.
        
        Override this method in subclasses to define whether internet or network connectivity
        is required before loading or during operation. The returned `RuntimeRequirements`
        object controls how the extractor behaves in environments with limited connectivity.
        
        Returns:
            RuntimeRequirements: An object describing the extractor's connectivity needs.
        """
        return RuntimeRequirements(internet_before_load=False,
                                   network_before_load=False,
                                   requires_internet=True,
                                   requires_network=True,
                                   no_internet_fallback=False,
                                   no_network_fallback=False)

    @classproperty
    def supported_seis(cls) -> List[str]:
        """
        Returns a list of Stream Extractor Identifiers (SEIs) supported by this extractor.
        
        SEIs indicate which stream formats the plugin can handle. Streams with a URI
        starting with "{sei}//" will be processed by this extractor if the SEI is listed here.
        
        Returns:
            A list of supported SEI strings. The default implementation returns an empty list.
        """
        return []

    def validate_uri(self, uri) -> bool:
        """
        Checks if the given URI matches any supported Stream Extractor Identifier (SEI).
        
        Returns:
            True if the URI starts with a supported SEI followed by "//"; otherwise, False.
        """
        return any([uri.startswith(f"{sei}//") for sei in self.supported_seis])

    @abc.abstractmethod
    def extract_stream(self, uri, video=True) -> Optional[str]:
        """
        Returns a playable URI for the given input URI.
        
        Subclasses must implement this method to extract and return the actual streamable URI corresponding to the provided input. If the extractor cannot handle the URI, it should return None.
        
        Args:
            uri: The input URI to extract a stream from.
            video: If True, extract a video stream; otherwise, extract an audio stream.
        
        Returns:
            The extracted playable URI, or None if extraction is not possible.
        """
        raise NotImplementedError()
