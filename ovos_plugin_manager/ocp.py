from ovos_plugin_manager.utils import load_plugin, find_plugins, PluginTypes, PluginConfigTypes
from ovos_plugin_manager.templates.ocp import OCPStreamExtractor
from ovos_utils.log import LOG


def find_ocp_plugins():
    return find_plugins(PluginTypes.STREAM_EXTRACTOR)


class StreamHandler:
    def __init__(self):
        self.extractors = {}
        self.load()

    @property
    def supported_seis(self):
        """
        skills may return results requesting a specific extractor to be used

        plugins should report a StreamExtractorIds (sei) that identifies it can handle certain kinds of requests

        any streams of the format "{sei}//{uri}" can be handled by this plugin
        """
        seis = []
        for extractor in self.extractors.values():
            seis += extractor.supported_seis
        return seis

    def load(self):
        for plugin, clazz in find_ocp_plugins().items():
            try:
                self.extractors[plugin] = clazz()
                LOG.info(f"Loaded OCP plugin: {plugin}")
            except:
                LOG.error(f"Failed to load {plugin}")
                continue

    def _get_sei_plugs(self, uri):
        return [plug for plug in self.extractors.values()
                if any((uri.startswith(f"{sei}//") for sei in plug.supported_seis))]

    def _extract_from_sei(self, uri, video=True):
        # attempt to use a dedicated stream extractor if requested
        for plug in self._get_sei_plugs(uri):
            try:
                return plug.extract_stream(uri, video)
            except Exception as e:
                LOG.exception(f"error extracting stream with {plug}")

    def _extract_from_url(self, uri, video=True):
        for plug in self.extractors.values():
            try:
                if plug.validate_uri(uri):
                    return plug.extract_stream(uri, video)
            except Exception as e:
                LOG.exception(f"error extracting stream with {plug}")

    def extract_stream(self, uri, video=True):
        meta = {}

        # attempt to use a dedicated stream extractor if requested
        while len(self._get_sei_plugs(uri)):  # support chained extractions, where one plugin calls another
            meta = self._extract_from_sei(uri, video) or {}
            if meta.get("uri"):
                uri = meta["uri"]
            else:
                break

        # let plugins parse the raw url and see if they want to handle it
        meta = self._extract_from_url(uri, video) or meta

        # no extractor available, return raw url
        return meta or {"uri": uri}


# if __name__ == "__main__":
#     s = StreamHandler()
#     print(s.supported_seis)
#     # ['rss', 'bandcamp', 'youtube', 'ydl', 'youtube.channel.live',
#     # 'pytube', 'invidious', 'm3u', 'pls']