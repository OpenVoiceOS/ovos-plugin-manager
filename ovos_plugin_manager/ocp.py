from ovos_plugin_manager.utils import PluginTypes
from ovos_plugin_manager.templates.ocp import OCPStreamExtractor
from ovos_utils.log import LOG
from functools import lru_cache

from ovos_plugin_manager.utils import find_plugins

try:
    from ovos_plugin_manager.templates.media import AudioPlayerBackend, VideoPlayerBackend, WebPlayerBackend
except ImportError:
    LOG.warning("Please install ovos-utils~=0.1 for `AudioPlayerBackend`, "
                "`VideoPlayerBackend`, and `WebPlayerBackend` imports.")


def find_ocp_plugins() -> dict:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    return find_plugins(PluginTypes.STREAM_EXTRACTOR)


def find_ocp_audio_plugins() -> dict:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    return find_plugins(PluginTypes.AUDIO_PLAYER)


def find_ocp_video_plugins() -> dict:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    return find_plugins(PluginTypes.VIDEO_PLAYER)


def find_ocp_web_plugins() -> dict:
    """
    Find all installed plugins
    @return: dict plugin names to entrypoints
    """
    return find_plugins(PluginTypes.WEB_PLAYER)


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


@lru_cache()  # to avoid loading StreamHandler more than once
def load_stream_extractors():
    return StreamHandler()


def available_extractors():
    xtract = load_stream_extractors()
    return ["/", "http:", "https:", "file:"] + \
        [f"{sei}//" for sei in xtract.supported_seis]
