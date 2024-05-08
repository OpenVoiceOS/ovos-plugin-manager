"""Definition of the audio service backends base classes.

These classes can be used to create an Audioservice plugin extending
OpenVoiceOS's media playback options.
"""
from ovos_bus_client.message import Message

from ovos_plugin_manager.templates.media import AudioPlayerBackend as _AB
from ovos_utils import classproperty
from ovos_utils.log import LOG, log_deprecation
from ovos_utils.process_utils import RuntimeRequirements

try:
    from ovos_utils.ocp import PlaybackType, TrackState
except ImportError:
    LOG.warning("Please update to ovos-utils~=0.1.")
    from enum import IntEnum

    class PlaybackType(IntEnum):
        SKILL = 0  # skills handle playback whatever way they see fit,
        # eg spotify / mycroft common play
        VIDEO = 1  # Video results
        AUDIO = 2  # Results should be played audio only
        AUDIO_SERVICE = 3  ## DEPRECATED - used in ovos 0.0.7
        MPRIS = 4  # External MPRIS compliant player
        WEBVIEW = 5  # webview, render a url instead of media player
        UNDEFINED = 100  # data not available, hopefully status will be updated soon..


    class TrackState(IntEnum):
        DISAMBIGUATION = 1  # media result, not queued for playback
        PLAYING_SKILL = 20  # Skill is handling playback internally
        PLAYING_AUDIOSERVICE = 21  ## DEPRECATED - used in ovos 0.0.7
        PLAYING_VIDEO = 22  # Skill forwarded playback to video service
        PLAYING_AUDIO = 23  # Skill forwarded playback to audio service
        PLAYING_MPRIS = 24  # External media player is handling playback
        PLAYING_WEBVIEW = 25  # Media playback handled in browser (eg. javascript)

        QUEUED_SKILL = 30  # Waiting playback to be handled inside skill
        QUEUED_AUDIOSERVICE = 31  ## DEPRECATED - used in ovos 0.0.7
        QUEUED_VIDEO = 32  # Waiting playback in video service
        QUEUED_AUDIO = 33  # Waiting playback in audio service
        QUEUED_WEBVIEW = 34  # Waiting playback in browser service


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
