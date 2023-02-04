
class OCPStreamExtractor:

    def __init__(self, ocp_settings=None):
        self.ocp_settings = ocp_settings or {}

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

