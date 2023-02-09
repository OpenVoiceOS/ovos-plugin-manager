from ovos_utils import classproperty
from ovos_utils.process_utils import RuntimeRequirements


class OCPStreamExtractor:

    def __init__(self, ocp_settings=None):
        self.ocp_settings = ocp_settings or {}

    @classproperty
    def runtime_requirements(self):
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
                                   requires_internet=True,
                                   requires_network=True,
                                   no_internet_fallback=False,
                                   no_network_fallback=False)

    @property
    def supported_seis(self):
        """
        skills may return results requesting a specific extractor to be used

        plugins should report a StreamExtractorIds (sei) that identifies it can handle certain kinds of requests

        any streams of the format "{sei}//{uri}" can be handled by this plugin
        """
        return []

    def validate_uri(self, uri):
        """ return True if uri can be handled by this extractor, False otherwise"""
        return any([uri.startswith(f"{sei}//")
                    for sei in self.supported_seis])

    def extract_stream(self, uri, video=True):
        """ return the real uri that can be played by OCP """
        return None
