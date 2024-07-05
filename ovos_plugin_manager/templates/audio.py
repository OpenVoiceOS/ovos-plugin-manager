"""Definition of the audio service backends base classes.

These classes can be used to create an Audioservice plugin extending
OpenVoiceOS's media playback options.
"""
from abc import ABCMeta, abstractmethod
from typing import List

from ovos_bus_client import Message
from ovos_bus_client.message import dig_for_message
from ovos_utils import classproperty
from ovos_utils.fakebus import FakeBus
from ovos_utils.log import LOG
from ovos_utils.process_utils import RuntimeRequirements

try:
    from ovos_utils.ocp import PlaybackType, TrackState, PlayerState, MediaState
except ImportError:
    LOG.warning("Please update to ovos-utils~=0.1.")
    from enum import IntEnum


    class MediaState(IntEnum):
        # https://doc.qt.io/qt-5/qmediaplayer.html#MediaStatus-enum
        # The status of the media cannot be determined.
        UNKNOWN = 0
        # There is no current media. PlayerState == STOPPED
        NO_MEDIA = 1
        # The current media is being loaded. The player may be in any state.
        LOADING_MEDIA = 2
        # The current media has been loaded. PlayerState== STOPPED
        LOADED_MEDIA = 3
        # Playback of the current media has stalled due to
        # insufficient buffering or some other temporary interruption.
        # PlayerState != STOPPED
        STALLED_MEDIA = 4
        # The player is buffering data but has enough data buffered
        # for playback to continue for the immediate future.
        # PlayerState != STOPPED
        BUFFERING_MEDIA = 5
        # The player has fully buffered the current media. PlayerState != STOPPED
        BUFFERED_MEDIA = 6
        # Playback has reached the end of the current media. PlayerState == STOPPED
        END_OF_MEDIA = 7
        # The current media cannot be played. PlayerState == STOPPED
        INVALID_MEDIA = 8


    class PlayerState(IntEnum):
        # https://doc.qt.io/qt-5/qmediaplayer.html#State-enum
        STOPPED = 0
        PLAYING = 1
        PAUSED = 2


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


class AudioBackend(metaclass=ABCMeta):
    """Base class for all audio backend implementations.

    Arguments:
        config (dict): configuration dict for the instance
        bus (MessageBusClient): OpenVoiceOS messagebus emitter
    """

    def __init__(self, config=None, bus=None, name=None):
        self.name = name or self.__class__.__name__
        self._now_playing = None  # single uri
        self._tracks = []  # list of dicts for OCP entries
        self._idx = 0
        self._track_start_callback = None
        self.supports_mime_hints = False
        self.config = config or {}
        self.bus = bus or FakeBus()

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

    @property
    def playback_time(self) -> int:
        """ in milliseconds """
        return 0

    @abstractmethod
    def supported_uris(self) -> List[str]:
        """List of supported uri types.

        Returns:
            list: Supported uri's
        """

    @abstractmethod
    def play(self, repeat=False):
        """Start playback.

        Starts playing the first track in the playlist and will contiune
        until all tracks have been played.

        Arguments:
            repeat (bool): Repeat playlist, defaults to False
        """

    @abstractmethod
    def lower_volume(self):
        """Lower volume.

        This method is used to implement audio ducking. It will be called when
        OpenVoiceOS is listening or speaking to make sure the media playing isn't
        interfering.
        """

    @abstractmethod
    def restore_volume(self):
        """Restore normal volume.

        Called when to restore the playback volume to previous level after
        OpenVoiceOS has lowered it using lower_volume().
        """

    @abstractmethod
    def get_track_length(self) -> int:
        """
        getting the duration of the audio in miliseconds
        """

    @abstractmethod
    def get_track_position(self) -> int:
        """
        get current position in miliseconds
        """

    @abstractmethod
    def set_track_position(self, milliseconds):
        """Go to X position.
        Arguments:
           milliseconds (int): position to go to in milliseconds
        """

    @abstractmethod
    def pause(self):
        """Pause playback.

        Stops playback but may be resumed at the exact position the pause
        occured.
        """

    @abstractmethod
    def resume(self):
        """Resume paused playback.

        Resumes playback after being paused.
        """

    @abstractmethod
    def stop(self):
        """Stop playback.

        Stops the current playback.

        Returns:
            bool: True if playback was stopped, otherwise False
        """

    #####################
    # internals and default implementations
    def track_info(self) -> dict:
        """Request information of current playing track.
        Returns:
            Dict with track info.
        """
        return self._uri2meta(self._now_playing)

    def clear_list(self):
        """Clear playlist."""
        self._tracks = []
        self._idx = 0

    def add_list(self, tracks):
        """Add tracks to backend's playlist.

        Arguments:
            tracks (list): list of tracks.
        """
        tracks = tracks or []
        if isinstance(tracks, str):
            tracks = [tracks]
        elif not isinstance(tracks, list):
            raise ValueError
        if tracks and not self._tracks:
            self.load_track(tracks[0])
            self._idx = 0
        self._tracks += tracks

    def next(self):
        """Skip to next track in playlist."""
        self._idx += 1
        if self._idx < len(self._tracks):
            self.load_track(self._tracks[self._idx])
            self.play()
        else:
            LOG.error("no more tracks!")

    def previous(self):
        """Skip to previous track in playlist."""
        self._idx = max(self._idx - 1, 0)
        if self._idx < len(self._tracks):
            self.load_track(self._tracks[self._idx])
            self.play()
        else:
            LOG.error("already in first track!")

    def seek_forward(self, seconds=1):
        """Skip X seconds.

        Arguments:
            seconds (int): number of seconds to seek, if negative rewind
        """
        miliseconds = seconds * 1000
        new_pos = self.get_track_position() + miliseconds
        self.set_track_position(new_pos)

    def seek_backward(self, seconds=1):
        """Rewind X seconds.

        Arguments:
            seconds (int): number of seconds to seek, if negative jump forward.
        """
        miliseconds = seconds * 1000
        new_pos = self.get_track_position() - miliseconds
        self.set_track_position(new_pos)

    def set_track_start_callback(self, callback_func):
        """Register callback on track start.

        This method should be called as each track in a playlist is started.
        """
        self._track_start_callback = callback_func

    def shutdown(self):
        """Perform clean shutdown.

        Implements any audio backend specific shutdown procedures.
        """
        self.stop()

    def _format_msg(self, msg_type, msg_data=None):
        # this method ensures all skills are .forward from the utterance
        # that triggered the skill, this ensures proper routing and metadata
        msg_data = msg_data or {}
        msg = dig_for_message()
        if msg:
            msg = msg.forward(msg_type, msg_data)
        else:
            msg = Message(msg_type, msg_data)
        # at this stage source == skills, lets indicate audio service took over
        sauce = msg.context.get("source")
        if sauce == "skills":
            msg.context["source"] = "audio_service"
        return msg

    ############################
    # OCP extensions - new methods to improve compat with OCP
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

    def load_track(self, uri):
        """ This method is only used by ovos-core
        In ovos audio backends are single-track, playlists are handled by OCP
        """
        self._now_playing = uri
        LOG.debug(f"queuing for {self.__class__.__name__} playback: {uri}")
        self.bus.emit(Message("ovos.common_play.media.state",
                              {"state": MediaState.LOADING_MEDIA}))
        self.bus.emit(Message("ovos.common_play.track.state", {
            "state": TrackState.QUEUED_AUDIOSERVICE
        }))

    def ocp_sync_playback(self, playback_time):
        self.bus.emit(Message("ovos.common_play.playback_time",
                              {"position": playback_time,
                               "length": self.get_track_length()}))

    def ocp_start(self):
        """Emit OCP status events for play"""
        self.bus.emit(Message("ovos.common_play.player.state",
                              {"state": PlayerState.PLAYING}))
        self.bus.emit(Message("ovos.common_play.media.state",
                              {"state": MediaState.LOADED_MEDIA}))
        self.bus.emit(Message("ovos.common_play.track.state",
                              {"state": TrackState.PLAYING_AUDIOSERVICE}))

    def ocp_error(self):
        """Emit OCP status events for playback error"""
        if self._now_playing:
            self.bus.emit(Message("ovos.common_play.media.state",
                                  {"state": MediaState.INVALID_MEDIA}))
            self._now_playing = None

    def ocp_stop(self):
        """Emit OCP status events for stop"""
        if self._now_playing:
            self._now_playing = None
            self.bus.emit(Message("ovos.common_play.player.state",
                                  {"state": PlayerState.STOPPED}))
            self.bus.emit(Message("ovos.common_play.media.state",
                                  {"state": MediaState.END_OF_MEDIA}))

    def ocp_pause(self):
        """Emit OCP status events for pause"""
        if self._now_playing:
            self.bus.emit(Message("ovos.common_play.player.state",
                                  {"state": PlayerState.PAUSED}))

    def ocp_resume(self):
        """Emit OCP status events for resume"""
        if self._now_playing:
            self.bus.emit(Message("ovos.common_play.player.state",
                                  {"state": PlayerState.PLAYING}))
            self.bus.emit(Message("ovos.common_play.track.state",
                                  {"state": TrackState.PLAYING_AUDIOSERVICE}))


class RemoteAudioBackend(AudioBackend):
    """Base class for remote audio backends.

    RemoteAudioBackends will always be checked after the normal
    AudioBackends to make playback start locally by default.

    An example of a RemoteAudioBackend would be things like Chromecasts,
    mopidy servers, etc.
    """
