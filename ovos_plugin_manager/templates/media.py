from abc import ABCMeta, abstractmethod

from ovos_bus_client.message import Message
from ovos_utils.log import LOG
from ovos_utils.fakebus import FakeBus
from ovos_utils.ocp import MediaState, PlayerState, TrackState


class MediaBackend(metaclass=ABCMeta):
    """Base class for all OCP media backend implementations.

    Media backends are single-track, playlists are handled by OCP

   Arguments:
       config (dict): configuration dict for the instance
       bus (MessageBusClient): Mycroft messagebus emitter
   """

    #: Whether this backend can seek within a track. Backends that cannot
    #: seek (e.g. live streams) should set this to False; consumers can
    #: check it before calling seek_forward/seek_backward.
    supports_seek = True

    #: Whether this backend can pause/resume playback. Backends that cannot
    #: pause (e.g. live streams) should set this to False; consumers can
    #: check it before calling ocp_pause/ocp_resume.
    supports_pause = True

    def __init__(self, config=None, bus=None):
        if MediaState is None:
            raise RuntimeError("Please update to ovos-utils~=0.1.")
        self._now_playing = None  # single uri
        self._ocp_playing = False  # tracks whether ocp_start has run without a matching stop/error
        self._track_start_callback = None
        self.supports_mime_hints = False
        self.config = config or {}
        self.bus = bus or FakeBus()
        self.meta = {}

    def set_track_start_callback(self, callback_func):
        """Register callback on track start.

        This method should be called as each track in a playlist is started.
        """
        self._track_start_callback = callback_func

    def load_track(self, uri: str, metadata: dict = None):
        self._now_playing = uri
        self._ocp_playing = False  # new track queued, ocp_start needs to (re)start playback
        self.meta.update(metadata or {})
        LOG.debug(f"queuing for {self.__class__.__name__} playback: {uri}")
        self.bus.emit(Message("ovos.common_play.media.state",
                              {"state": MediaState.LOADED_MEDIA}))

    def ocp_start(self):
        """Emit OCP status events for play.

        Idempotent: if playback was already started by a previous call and
        has not since been stopped (ocp_stop) or errored (ocp_error), this
        is a no-op. This prevents duplicate LOADED_MEDIA/PLAYING events and
        a duplicate call to play() when ocp_start is invoked again while
        playback is already active.
        """
        if self._ocp_playing:
            LOG.debug(f"{self.__class__.__name__}.ocp_start called while "
                      f"already playing, ignoring")
            return
        self._ocp_playing = True
        self.bus.emit(Message("ovos.common_play.player.state",
                              {"state": PlayerState.PLAYING}))
        self.bus.emit(Message("ovos.common_play.media.state",
                              {"state": MediaState.LOADED_MEDIA}))
        self.play()

    def ocp_error(self):
        """Emit OCP status events for playback error"""
        if self._now_playing:
            self._now_playing = None
            self._ocp_playing = False
            self.bus.emit(Message("ovos.common_play.media.state",
                                  {"state": MediaState.INVALID_MEDIA}))
            self.bus.emit(Message("ovos.common_play.player.state",
                                  {"state": PlayerState.STOPPED}))

    def ocp_stop(self):
        """Emit OCP status events for stop"""
        if self._now_playing:
            self._now_playing = None
            self._ocp_playing = False
            self.bus.emit(Message("ovos.common_play.player.state",
                                  {"state": PlayerState.STOPPED}))
            self.bus.emit(Message("ovos.common_play.media.state",
                                  {"state": MediaState.END_OF_MEDIA}))
            self.stop()

    def ocp_pause(self):
        """Emit OCP status events for pause"""
        if self._now_playing:
            self.bus.emit(Message("ovos.common_play.player.state",
                                  {"state": PlayerState.PAUSED}))
            self.pause()

    def ocp_resume(self):
        """Emit OCP status events for resume"""
        if self._now_playing:
            self.bus.emit(Message("ovos.common_play.player.state",
                                  {"state": PlayerState.PLAYING}))
            self.bus.emit(Message("ovos.common_play.track.state",
                                  {"state": TrackState.PLAYING_AUDIO}))
            self.resume()

    @property
    def playback_time(self):
        return 0

    @abstractmethod
    def supported_uris(self):
        """List of supported uri types.

        Returns:
            list: Supported uri's
        """

    @abstractmethod
    def play(self):
        """Start playback.

        Starts playing the first track in the playlist and will contiune
        until all tracks have been played.
        """

    @abstractmethod
    def stop(self):
        """Stop playback.

        Stops the current playback.

        Returns:
            bool: True if playback was stopped, otherwise False
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
        getting the duration of the audio in milliseconds
        """

    @abstractmethod
    def get_track_position(self) -> int:
        """
        get current position in milliseconds
        """

    @abstractmethod
    def set_track_position(self, milliseconds):
        """
        go to position in milliseconds
          Args:
                milliseconds (int): number of milliseconds of final position
        """

    def seek_forward(self, seconds=1):
        """Skip X seconds.

        Arguments:
            seconds (int): number of seconds to seek, if negative rewind
        """
        miliseconds = seconds * 1000
        position = self.get_track_position()
        if position is None:
            LOG.debug(f"{self.__class__.__name__} reported no track "
                      f"position, ignoring seek_forward")
            return
        self.set_track_position(position + miliseconds)

    def seek_backward(self, seconds=1):
        """Rewind X seconds.

        Arguments:
            seconds (int): number of seconds to seek, if negative jump forward.
        """
        miliseconds = seconds * 1000
        position = self.get_track_position()
        if position is None:
            LOG.debug(f"{self.__class__.__name__} reported no track "
                      f"position, ignoring seek_backward")
            return
        self.set_track_position(position - miliseconds)

    def track_info(self):
        """Get info about current playing track.

        Returns:
            dict: Track info containing atleast the keys artist and album.
        """
        return self.meta

    def shutdown(self):
        """Perform clean shutdown.

        Implements any audio backend specific shutdown procedures.
        """
        self.stop()


class AudioPlayerBackend(MediaBackend):
    """ for audio"""

    def load_track(self, uri, metadata: dict = None):
        super().load_track(uri, metadata)
        self.bus.emit(Message("ovos.common_play.track.state",
                              {"state": TrackState.QUEUED_AUDIO}))

    def ocp_start(self):
        """Emit OCP status events for play. Idempotent, see MediaBackend.ocp_start."""
        was_playing = self._ocp_playing
        super().ocp_start()
        if not was_playing:
            self.bus.emit(Message("ovos.common_play.track.state",
                                  {"state": TrackState.PLAYING_AUDIO}))


class RemoteAudioPlayerBackend(AudioPlayerBackend):
    """Base class for remote audio backends.

    RemoteAudioBackends will always be checked after the normal
    AudioBackends to make playback start locally by default.

    An example of a RemoteAudioBackend would be things like mopidy servers, etc.
    """


class VideoPlayerBackend(MediaBackend):
    """ for video"""
    def load_track(self, uri, metadata: dict = None):
        super().load_track(uri, metadata)
        self.bus.emit(Message("ovos.common_play.track.state",
                              {"state": TrackState.QUEUED_VIDEO}))

    def ocp_start(self):
        """Emit OCP status events for play. Idempotent, see MediaBackend.ocp_start."""
        was_playing = self._ocp_playing
        super().ocp_start()
        if not was_playing:
            self.bus.emit(Message("ovos.common_play.track.state",
                                  {"state": TrackState.PLAYING_VIDEO}))


class RemoteVideoPlayerBackend(VideoPlayerBackend):
    """Base class for remote audio backends.

    RemoteVideoBackends will always be checked after the normal
    VideoBackends to make playback start locally by default.

    An example of a RemoteVideoBackend would be things like Chromecasts, etc.
    """


class WebPlayerBackend(MediaBackend):
    """ for web pages"""

    def load_track(self, uri, metadata: dict = None):
        super().load_track(uri, metadata)
        self.bus.emit(Message("ovos.common_play.track.state",
                              {"state": TrackState.QUEUED_WEBVIEW}))

    def ocp_start(self):
        """Emit OCP status events for play. Idempotent, see MediaBackend.ocp_start."""
        was_playing = self._ocp_playing
        super().ocp_start()
        if not was_playing:
            self.bus.emit(Message("ovos.common_play.track.state",
                                  {"state": TrackState.PLAYING_WEBVIEW}))


class RemoteWebPlayerBackend(WebPlayerBackend):
    """Base class for remote web backends.

    RemoteWebBackends will always be checked after the normal
    VideoBackends to make playback start locally by default.

    An example of a RemoteWebBackend would be
    things that can render a webpage in a different machine
    """
