"""Definition of the audio service backends base classes.

These classes can be used to create an Audioservice plugin extending
OpenVoiceOS's media playback options.
"""
from abc import ABCMeta, abstractmethod

from ovos_bus_client import Message
from ovos_bus_client.message import dig_for_message
from ovos_utils import classproperty
from ovos_utils.log import log_deprecation, LOG
from ovos_utils.fakebus import FakeBus
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


class AudioBackend(metaclass=ABCMeta):
    """Base class for all audio backend implementations.

    Arguments:
        config (dict): configuration dict for the instance
        bus (MessageBusClient): OpenVoiceOS messagebus emitter
    """

    def __init__(self, config=None, bus=None):
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
    def playback_time(self):
        return 0

    def supported_uris(self):
        """List of supported uri types.

        Returns:
            list: Supported uri's
        """

    def clear_list(self):
        """Clear playlist."""
        msg = Message('ovos.common_play.playlist.clear')
        self.bus.emit(msg)

    @abstractmethod
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

    @abstractmethod
    def play(self, repeat=False):
        """Start playback.

        Starts playing the first track in the playlist and will contiune
        until all tracks have been played.

        Arguments:
            repeat (bool): Repeat playlist, defaults to False
        """

    def stop(self):
        """Stop playback.

        Stops the current playback.

        Returns:
            bool: True if playback was stopped, otherwise False
        """

    def set_track_start_callback(self, callback_func):
        """Register callback on track start.

        This method should be called as each track in a playlist is started.
        """
        self._track_start_callback = callback_func

    def pause(self):
        """Pause playback.

        Stops playback but may be resumed at the exact position the pause
        occured.
        """
        msg = Message('ovos.common_play.pause')
        self.bus.emit(msg)

    def resume(self):
        """Resume paused playback.

        Resumes playback after being paused.
        """
        msg = Message('ovos.common_play.resume')

    def next(self):
        """Skip to next track in playlist."""
        self.bus.emit(Message("ovos.common_play.next"))

    def previous(self):
        """Skip to previous track in playlist."""
        self.bus.emit(Message("ovos.common_play.previous"))

    def lower_volume(self):
        """Lower volume.

        This method is used to implement audio ducking. It will be called when
        OpenVoiceOS is listening or speaking to make sure the media playing isn't
        interfering.
        """

    def restore_volume(self):
        """Restore normal volume.

        Called when to restore the playback volume to previous level after
        OpenVoiceOS has lowered it using lower_volume().
        """

    def get_track_length(self):
        """
        getting the duration of the audio in miliseconds
        """
        length = 0
        msg = self._format_msg('ovos.common_play.get_track_length')
        info = self.bus.wait_for_response(msg, timeout=1)
        if info:
            length = info.data.get("length", 0)
        return length

    def get_track_position(self):
        """
        get current position in miliseconds
        """
        pos = 0
        msg = self._format_msg('ovos.common_play.get_track_position')
        info = self.bus.wait_for_response(msg, timeout=1)
        if info:
            pos = info.data.get("position", 0)
        return pos

    def set_track_position(self, milliseconds):
        """Go to X position.
        Arguments:
           milliseconds (int): position to go to in milliseconds
        """
        msg = self._format_msg('ovos.common_play.set_track_position',
                               {"position": milliseconds})
        self.bus.emit(msg)

    def seek_forward(self, seconds=1):
        """Skip X seconds.

        Arguments:
            seconds (int): number of seconds to seek, if negative rewind
        """
        msg = self._format_msg('ovos.common_play.seek',
                               {"seconds": seconds})
        self.bus.emit(msg)

    def seek_backward(self, seconds=1):
        """Rewind X seconds.

        Arguments:
            seconds (int): number of seconds to seek, if negative jump forward.
        """
        msg = self._format_msg('ovos.common_play.seek',
                               {"seconds": seconds * -1})
        self.bus.emit(msg)

    def track_info(self):
        """Request information of current playing track.
        Returns:
            Dict with track info.
        """
        msg = self._format_msg('ovos.common_play.track_info')
        response = self.bus.wait_for_response(msg)
        return response.data if response else {}

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


class RemoteAudioBackend(AudioBackend):
    """Base class for remote audio backends.

    RemoteAudioBackends will always be checked after the normal
    AudioBackends to make playback start locally by default.

    An example of a RemoteAudioBackend would be things like Chromecasts,
    mopidy servers, etc.
    """
