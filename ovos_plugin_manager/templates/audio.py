from abc import ABCMeta, abstractmethod
from typing import List

from ovos_bus_client import Message
from ovos_bus_client.message import dig_for_message
from ovos_utils import classproperty
from ovos_utils.fakebus import FakeBus
from ovos_utils.log import LOG
from ovos_utils.ocp import PlaybackType, TrackState, PlayerState, MediaState
from ovos_utils.process_utils import RuntimeRequirements


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
    def runtime_requirements(cls):
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
