"""Definition of the audio service backends base classes.

These classes can be used to create an Audioservice plugin extending
OpenVoiceOS's media playback options.
"""
from ovos_bus_client.message import Message

from ovos_plugin_manager.templates.media import AudioPlayerBackend as _AB
from ovos_utils import classproperty
from ovos_utils.log import log_deprecation
from ovos_utils.ocp import PlaybackType, TrackState
from ovos_utils.process_utils import RuntimeRequirements

log_deprecation("ovos_plugin_manager.templates.audio has been deprecated on ovos-audio, "
                "move to ovos_plugin_manager.templates.media", "0.1.0")


class AudioBackend(_AB):
    """Base class for all audio backend implementations.

    Arguments:
        config (dict): configuration dict for the instance
        bus (MessageBusClient): OpenVoiceOS messagebus emitter
    """

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
                                   requires_internet=False,
                                   requires_network=False,
                                   no_internet_fallback=True,
                                   no_network_fallback=True)

    # methods below deprecated and handled by OCP directly
    # playlists are no longer managed plugin side
    # this is just a compat layer forwarding commands to OCP
    def clear_list(self):
        """Clear playlist."""
        msg = Message('ovos.common_play.playlist.clear')
        self.bus.emit(msg)

    def add_list(self, tracks):
        """Add tracks to backend's playlist.

        Arguments:
            tracks (list): list of tracks.
        """
        tracks = tracks or []
        if isinstance(tracks, (str, tuple)):
            tracks = [tracks]
        elif not isinstance(tracks, list):
            raise ValueError
        tracks = [self._uri2meta(t) for t in tracks]
        msg = Message('ovos.common_play.playlist.queue',
                      {'tracks': tracks})
        self.bus.emit(msg)

    @staticmethod
    def _uri2meta(uri):
        if isinstance(uri, list):
            uri = uri[0]
        try:
            from ovos_ocp_files_plugin.plugin import OCPFilesMetadataExtractor
            return OCPFilesMetadataExtractor.extract_metadata(uri)
        except:
            meta = {"uri": uri,
                    "skill_id": "mycroft.audio_interface",
                    "playback": PlaybackType.AUDIO,  # TODO mime type check
                    "status": TrackState.QUEUED_AUDIO,
                    }
        return meta

    def next(self):
        """Skip to next track in playlist."""
        self.bus.emit(Message("ovos.common_play.next"))

    def previous(self):
        """Skip to previous track in playlist."""
        self.bus.emit(Message("ovos.common_play.previous"))


class RemoteAudioBackend(AudioBackend):
    """Base class for remote audio backends.

    RemoteAudioBackends will always be checked after the normal
    AudioBackends to make playback start locally by default.

    An example of a RemoteAudioBackend would be things like Chromecasts,
    mopidy servers, etc.
    """
