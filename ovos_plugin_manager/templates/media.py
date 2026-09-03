import enum
from abc import ABCMeta, abstractmethod
from typing import Callable, Optional

from ovos_utils.fakebus import FakeBus
from ovos_utils.log import LOG


class PlaybackEvent(enum.Enum):
    """Physical playback events a MediaBackend plugin can observe.

    These describe what actually happened inside the player process:
    a track started, playback paused/resumed/stopped, the media ended,
    or the player errored out. There is no "loaded" event here - loading
    is reported through ``load_track``'s return value, and turning that
    into a state transition (and any wire message) is the daemon's job,
    not the plugin's.
    """
    TRACK_START = "track_start"
    PAUSED = "paused"
    RESUMED = "resumed"
    STOPPED = "stopped"
    END_OF_MEDIA = "end_of_media"
    ERROR = "error"
    """Reported as ``report(PlaybackEvent.ERROR, error=str(exc))`` - the
    ``error`` kwarg is the normative payload key and its value is always a
    string description of what went wrong."""


class MediaBackend(metaclass=ABCMeta):
    """Base class for all OCP media backend implementations.

    Media backends are single-track, playlists are handled by OCP.

    ``self.bus`` is a plugin-private transport, not a state channel. Use it
    for whatever ecosystem integration or plugin-private protocol the
    backend needs - e.g. a discovery announcement like
    ovos-media-plugin-mass's ``ovos.mass.ping`` - never to report playback
    state. Playback state flows exclusively through ``report``/
    ``bind_event_reporter``: the physical events the plugin observes
    (track started, paused, resumed, stopped, ended, errored). The daemon
    that owns the plugin is the only thing that translates those physical
    events into bus messages and drives the player state machine -
    including the LOADED_MEDIA transition, which is bookkeeping on
    ``load_track``'s return value and therefore not a ``PlaybackEvent``. A
    backend that emits any ``ovos.common_play.*`` state message itself is
    buggy by definition - the daemon owns that wire.

    Subprocess-shaped backends (anything wrapping an external player
    binary): a player process exiting with a nonzero return code is an
    ``ERROR``, never an ``END_OF_MEDIA``. Check the return code in the
    exit callback before calling ``report_track_end`` - a subprocess that
    dies because the file doesn't exist and one that finishes playing
    cleanly both look like "the process exited" to a naive callback, and
    only the return code tells them apart.

    Remote/side-channel backends (Cast, MPRIS, network players): the verb
    methods (``play``/``pause``/``resume``/``stop``) SHOULD be pure asks
    with zero ``report()`` calls of their own - asking a remote player to
    pause does not mean it *will* pause. The status listener or poller
    that watches the remote player's actual state is the sole reporter of
    what happened, so a change made outside OVOS entirely (a user pausing
    from the device's own app) still surfaces correctly as a
    ``PAUSED``/``RESUMED``/``STOPPED`` report.

    External-state detection may be event-driven (native signals or
    listener callbacks from the remote player's own SDK - preferred where
    available) or polled state-diffing (acceptable when no event exists:
    compare the freshly-polled state against the last seen state and
    report only the transition, not the polled state itself).

    Arguments:
        config (dict): configuration dict for the instance
        bus (MessageBusClient): plugin-private messagebus connection, for
            non-state ecosystem integration only. Defaults to a FakeBus
            when not provided, so a backend is always safe to construct
            and drive standalone (e.g. in tests) without a real bus.
    """

    can_seek: bool = False
    can_pause: bool = True
    is_remote: bool = False

    def __init__(self, config=None, bus=None):
        self.supports_mime_hints = False
        self.config = config or {}
        self.bus = bus or FakeBus()
        self.meta = {}
        self._event_reporter: Optional[Callable[..., None]] = None
        self._stop_requested = False

    def bind_event_reporter(self, reporter: Callable[..., None]) -> None:
        """Register the callable the daemon uses to receive playback events.

        The normative call signature is ``reporter(event, **data)``: the
        reporter is always called positionally with a ``PlaybackEvent`` as
        the first argument, followed by event-specific data as keyword
        arguments (e.g. ``error=str(exc)`` for ``PlaybackEvent.ERROR``).
        A reporter may declare ``**kwargs`` to accept any event, or name
        only the specific keywords it cares about.

        Arguments:
            reporter: callable invoked as ``reporter(event, **data)`` every
                time the plugin observes a physical playback event.
        """
        self._event_reporter = reporter

    def report(self, event: PlaybackEvent, **data) -> None:
        """Report a physical playback event to the daemon, if bound.

        Always calls the bound reporter as ``reporter(event, **data)`` -
        see ``bind_event_reporter`` for the normative signature. No-ops
        (with a debug log) when no reporter has been registered, so
        backends can be constructed and exercised standalone, e.g. in
        tests, without a daemon attached.

        Plugins SHOULD attach the ``uri`` of the track the event belongs
        to when reporting ``PlaybackEvent.END_OF_MEDIA`` and
        ``PlaybackEvent.ERROR`` - ``self.report(PlaybackEvent.END_OF_MEDIA,
        uri=<the uri load_track received>)`` - so the daemon can detect and
        drop a stale event that outlives its track (e.g. a late callback
        from a previous track's watcher thread firing after a new track
        has already loaded). An event reported without a ``uri`` cannot be
        staleness-checked by the daemon.
        """
        if self._event_reporter is None:
            LOG.debug(f"{self.__class__.__name__} not bound to an event "
                      f"reporter, dropping {event}")
            return
        self._event_reporter(event, **data)

    def report_track_end(self, uri: str = None, error=None) -> None:
        """Report that a track ended, from a callback that cannot itself
        tell a requested stop from a natural end.

        This is THE way to report the end of a track from an exit/status
        callback that only sees "playback is no longer happening" -
        e.g. a subprocess exit handler, or an MPRIS ``Stopped`` transition
        - and has no other way to know whether OVOS asked for the stop or
        the track simply finished on its own.

        Dispatches based on why playback ended:

        - ``error`` is not None: reports ``PlaybackEvent.ERROR`` with
          ``error=str(error)``. A nonzero subprocess exit code or an
          engine-reported failure MUST be passed here - it must never be
          mapped to a natural end just because the process/session exited.
        - ``error`` is None and ``stop()`` was called since the last
          report: reports ``PlaybackEvent.STOPPED``.
        - otherwise: reports ``PlaybackEvent.END_OF_MEDIA``.

        Always clears the pending explicit-stop flag afterward, whichever
        branch was taken, so the next end-of-track callback starts clean.

        Arguments:
            uri: the uri of the track this end-of-playback event belongs
                to, forwarded to ``report`` for daemon-side staleness
                checks (see ``report``).
            error: the exception or error description if playback ended
                because of a failure, else None.
        """
        try:
            if error is not None:
                self.report(PlaybackEvent.ERROR, error=str(error), uri=uri)
            elif self._stop_requested:
                self.report(PlaybackEvent.STOPPED, uri=uri)
            else:
                self.report(PlaybackEvent.END_OF_MEDIA, uri=uri)
        finally:
            self._stop_requested = False

    @abstractmethod
    def supported_uris(self):
        """List of supported uri types.

        Returns:
            list: Supported uri's
        """

    @abstractmethod
    def load_track(self, uri: str, metadata: dict = None) -> bool:
        """Load a track for playback.

        Reports nothing - this only signals success/failure of loading.
        The daemon owns the LOADED_MEDIA state transition on a True return.

        Arguments:
            uri (str): uri to load
            metadata (dict): track metadata

        Returns:
            bool: True if the track was loaded successfully
        """

    @abstractmethod
    def play(self):
        """Start playback.

        Starts playing the loaded track.
        """

    def stop(self) -> bool:
        """Stop playback.

        Concrete template method: records that a stop was explicitly
        requested (so a subsequent ``report_track_end`` from an exit/
        status callback can tell this apart from a natural end), then
        delegates to ``_stop`` for the actual work. Plugins implement
        ``_stop``, not ``stop``.

        Returns:
            bool: True if playback was stopped, otherwise False
        """
        self._stop_requested = True
        return self._stop()

    @abstractmethod
    def _stop(self) -> bool:
        """Perform the actual stop.

        Called by ``stop()`` after it has recorded the explicit-stop flag.
        Implement this, not ``stop``, in backends.

        Returns:
            bool: True if playback was stopped, otherwise False
        """

    @abstractmethod
    def pause(self):
        """Pause playback.

        Stops playback but may be resumed at the exact position the pause
        occurred.
        """

    @abstractmethod
    def resume(self):
        """Resume paused playback.

        Resumes playback after being paused.
        """

    def lower_volume(self):
        """Lower volume.

        Used to implement audio ducking. Called when OpenVoiceOS is
        listening or speaking to make sure the media playing isn't
        interfering. No-op by default.
        """

    def restore_volume(self):
        """Restore normal volume.

        Called to restore the playback volume to its previous level after
        OpenVoiceOS has lowered it using ``lower_volume``. No-op by default.
        """

    def get_track_length(self) -> int:
        """
        Get the duration of the current track in milliseconds.

        Concrete default returns -1 (unknown), since ``can_seek`` defaults
        to False and a backend that can't seek has no reason to track
        duration. Backends that support seeking should override this,
        return a real value, and set ``can_seek = True``.
        """
        return -1

    def get_track_position(self) -> int:
        """
        Get current playback position in milliseconds.

        Concrete default returns -1 (unknown); see ``get_track_length``.
        Backends that support seeking should override this and set
        ``can_seek = True``.
        """
        return -1

    def set_track_position(self, milliseconds: int):
        """
        Seek to a position in milliseconds.

        Concrete default is a no-op (with a debug log); it is only
        meaningful when ``can_seek`` is True. Backends that support
        seeking should override this, perform the seek, and set
        ``can_seek = True``.

          Args:
                milliseconds (int): number of milliseconds of final position
        """
        LOG.debug(f"{self.__class__.__name__} does not support seeking "
                  f"(can_seek=False), ignoring set_track_position({milliseconds})")

    def track_info(self):
        """Get info about current playing track.

        Returns:
            dict: Track info containing atleast the keys artist and album.
        """
        return self.meta

    def shutdown(self):
        """Perform clean shutdown.

        Implements any media backend specific shutdown procedures.
        """
        self.stop()


class AudioPlayerBackend(MediaBackend):
    """ for audio"""


class RemoteAudioPlayerBackend(AudioPlayerBackend):
    """Base class for remote audio backends.

    RemoteAudioBackends will always be checked after the normal
    AudioBackends to make playback start locally by default.

    An example of a RemoteAudioBackend would be things like mopidy servers, etc.
    """
    is_remote = True


class VideoPlayerBackend(MediaBackend):
    """ for video"""


class RemoteVideoPlayerBackend(VideoPlayerBackend):
    """Base class for remote video backends.

    RemoteVideoBackends will always be checked after the normal
    VideoBackends to make playback start locally by default.

    An example of a RemoteVideoBackend would be things like Chromecasts, etc.
    """
    is_remote = True


class WebPlayerBackend(MediaBackend):
    """ for web pages"""


class RemoteWebPlayerBackend(WebPlayerBackend):
    """Base class for remote web backends.

    RemoteWebBackends will always be checked after the normal
    WebBackends to make playback start locally by default.

    An example of a RemoteWebBackend would be
    things that can render a webpage in a different machine
    """
    is_remote = True
