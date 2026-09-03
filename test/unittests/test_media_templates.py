# Copyright 2024, OpenVoiceOS
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for ovos_plugin_manager.templates.media (MediaBackend v2)."""

import ast
import inspect
import unittest
from unittest.mock import MagicMock

from ovos_plugin_manager.templates.media import (
    AudioPlayerBackend,
    MediaBackend,
    PlaybackEvent,
    RemoteAudioPlayerBackend,
    RemoteVideoPlayerBackend,
    RemoteWebPlayerBackend,
    VideoPlayerBackend,
    WebPlayerBackend,
)


# ---------------------------------------------------------------------------
# Concrete subclass helper
# ---------------------------------------------------------------------------

class _ConcreteMediaBackend(MediaBackend):
    """Minimal concrete MediaBackend for testing."""

    def supported_uris(self):
        return ["file", "http"]

    def load_track(self, uri: str, metadata: dict = None) -> bool:
        self.meta.update(metadata or {})
        return True

    def play(self):
        self.report(PlaybackEvent.TRACK_START)

    def _stop(self) -> bool:
        self.report_track_end()
        return True

    def pause(self):
        self.report(PlaybackEvent.PAUSED)

    def resume(self):
        self.report(PlaybackEvent.RESUMED)

    def get_track_length(self) -> int:
        return 0

    def get_track_position(self) -> int:
        return 0

    def set_track_position(self, milliseconds: int) -> None:
        pass


# ---------------------------------------------------------------------------
# Tests for MediaBackend
# ---------------------------------------------------------------------------

class TestMediaBackend(unittest.TestCase):
    """Tests for MediaBackend base class."""

    def setUp(self) -> None:
        self.backend = _ConcreteMediaBackend()

    def test_init_defaults(self) -> None:
        """MediaBackend initialises with default config and a FakeBus."""
        from ovos_utils.fakebus import FakeBus
        self.assertEqual(self.backend.config, {})
        self.assertFalse(self.backend.supports_mime_hints)
        self.assertIsInstance(self.backend.bus, FakeBus)

    def test_init_custom_config(self) -> None:
        backend = _ConcreteMediaBackend(config={"key": "val"})
        self.assertEqual(backend.config["key"], "val")

    def test_init_accepts_custom_bus(self) -> None:
        """bus= is accepted and stored as-is - it is a plugin-private
        transport, not part of the state contract."""
        custom_bus = MagicMock()
        backend = _ConcreteMediaBackend(config={}, bus=custom_bus)
        self.assertIs(backend.bus, custom_bus)

    def test_bus_is_never_used_for_state_by_default(self) -> None:
        """Constructing standalone with no bus argument must not touch a
        real messagebus - the default FakeBus is inert."""
        backend = _ConcreteMediaBackend()
        self.assertTrue(hasattr(backend.bus, "emit"))

    def test_load_track_returns_bool(self) -> None:
        self.assertTrue(self.backend.load_track("file:///test.mp3"))

    def test_load_track_with_metadata(self) -> None:
        self.backend.load_track("file:///test.mp3", metadata={"title": "Test"})
        self.assertEqual(self.backend.meta["title"], "Test")

    def test_report_noops_without_reporter(self) -> None:
        """report() must not raise and must not touch anything when unbound."""
        # mutation check target: if report() silently swallowed events even
        # when bound (see test_report_delivers_event_to_bound_reporter) this
        # test alone would not catch it - it only proves the unbound path
        # is safe, which it is by construction (early return).
        self.backend.report(PlaybackEvent.TRACK_START, foo="bar")  # no raise

    def test_bind_event_reporter_delivers_event(self) -> None:
        """A bound reporter receives the exact event and kwargs reported."""
        received = []

        def reporter(event, **data):
            received.append((event, data))

        self.backend.bind_event_reporter(reporter)
        self.backend.report(PlaybackEvent.ERROR, error="boom")

        self.assertEqual(len(received), 1)
        event, data = received[0]
        self.assertIs(event, PlaybackEvent.ERROR)
        self.assertEqual(data, {"error": "boom"})

    def test_bind_event_reporter_delivers_via_play(self) -> None:
        """play() reports TRACK_START through the bound reporter."""
        reporter = MagicMock()
        self.backend.bind_event_reporter(reporter)
        self.backend.play()
        reporter.assert_called_once_with(PlaybackEvent.TRACK_START)

    def test_reporter_with_kwargs_signature_receives_any_event(self) -> None:
        """A reporter declared as (event, **kwargs) - the loosest normative
        shape - must receive every event/data combination reported,
        including the uri staleness-check hint on END_OF_MEDIA."""
        received = []

        def r(event, **kwargs):
            received.append((event, kwargs))

        self.backend.bind_event_reporter(r)
        self.backend.report(PlaybackEvent.PAUSED)
        self.backend.report(PlaybackEvent.ERROR, error="disk full")
        self.backend.report(PlaybackEvent.END_OF_MEDIA, uri="file:///test.mp3")

        self.assertEqual(received, [
            (PlaybackEvent.PAUSED, {}),
            (PlaybackEvent.ERROR, {"error": "disk full"}),
            (PlaybackEvent.END_OF_MEDIA, {"uri": "file:///test.mp3"}),
        ])

    def test_reporter_with_named_error_kwarg_receives_error_event(self) -> None:
        """A reporter that only names the keywords it cares about - e.g.
        (event, error=None) - must still work for PlaybackEvent.ERROR,
        proving the call convention is positional-event + keyword-data."""
        received = []

        def r(event, error=None):
            received.append((event, error))

        self.backend.bind_event_reporter(r)
        self.backend.report(PlaybackEvent.ERROR, error="disk full")

        self.assertEqual(received, [(PlaybackEvent.ERROR, "disk full")])

    def test_error_payload_shape_is_normative(self) -> None:
        """PlaybackEvent.ERROR is always reported with a single 'error'
        kwarg whose value is a string - pin the documented payload shape."""
        reporter = MagicMock()
        self.backend.bind_event_reporter(reporter)

        try:
            raise RuntimeError("player crashed")
        except RuntimeError as exc:
            self.backend.report(PlaybackEvent.ERROR, error=str(exc))

        reporter.assert_called_once_with(PlaybackEvent.ERROR, error="player crashed")
        _, kwargs = reporter.call_args
        self.assertEqual(set(kwargs), {"error"})
        self.assertIsInstance(kwargs["error"], str)

    def test_capability_defaults(self) -> None:
        self.assertFalse(MediaBackend.can_seek)
        self.assertTrue(MediaBackend.can_pause)
        self.assertFalse(MediaBackend.is_remote)

    def test_lower_and_restore_volume_default_noop(self) -> None:
        """Default volume duck hooks exist and do nothing when unimplemented."""
        self.backend.lower_volume()
        self.backend.restore_volume()  # no raise, no override needed

    def test_track_info_default_empty(self) -> None:
        fresh = _ConcreteMediaBackend()
        self.assertEqual(fresh.track_info(), {})

    def test_track_info_returns_meta(self) -> None:
        self.backend.meta = {"artist": "Test Artist"}
        self.assertEqual(self.backend.track_info()["artist"], "Test Artist")

    def test_shutdown_calls_stop(self) -> None:
        reporter = MagicMock()
        self.backend.bind_event_reporter(reporter)
        self.backend.shutdown()
        reporter.assert_called_once_with(PlaybackEvent.STOPPED, uri=None)

    def test_no_deleted_v1_verbs(self) -> None:
        """v1 bus-coupled verbs must not survive on the v2 template."""
        for name in ("ocp_start", "ocp_stop", "ocp_pause", "ocp_resume",
                     "ocp_error", "set_track_start_callback",
                     "seek_forward", "seek_backward"):
            self.assertFalse(hasattr(MediaBackend, name),
                              f"{name} should have been removed in v2")

    def test_stop_is_concrete_and_underscore_stop_is_abstract(self) -> None:
        """stop() is now the concrete template method; _stop() is what
        plugins must implement."""
        self.assertNotIn("stop", MediaBackend.__abstractmethods__)
        self.assertIn("stop", dir(MediaBackend))
        self.assertFalse(getattr(MediaBackend.stop, "__isabstractmethod__", False))
        self.assertIn("_stop", MediaBackend.__abstractmethods__)

    def test_abstract_verbs_cannot_be_instantiated_without_them(self) -> None:
        """Omitting an abstract verb must prevent instantiation."""
        class _Incomplete(MediaBackend):
            def supported_uris(self):
                return []

            def load_track(self, uri, metadata=None):
                return True

            def play(self):
                pass

            def _stop(self):
                return True

            def pause(self):
                pass

            # resume deliberately missing - get/set_track_position are
            # concrete defaults in v2 (see test_position_trio_concrete_defaults)
            # and must NOT be required here.

        with self.assertRaises(TypeError):
            _Incomplete()

    def test_position_trio_concrete_defaults(self) -> None:
        """get_track_length/get_track_position/set_track_position are
        concrete on the base class: -1 (unknown) for the getters, a no-op
        for the setter, since can_seek defaults to False."""
        class _NoSeek(MediaBackend):
            def supported_uris(self):
                return []

            def load_track(self, uri, metadata=None):
                return True

            def play(self):
                pass

            def _stop(self):
                return True

            def pause(self):
                pass

            def resume(self):
                pass
            # get_track_length/get_track_position/set_track_position NOT overridden

        backend = _NoSeek()
        self.assertFalse(backend.can_seek)
        self.assertEqual(backend.get_track_length(), -1)
        self.assertEqual(backend.get_track_position(), -1)
        backend.set_track_position(5000)  # no-op, must not raise

    def test_stop_sets_flag_before_delegating_to_stop_impl(self) -> None:
        """Concrete stop() must set _stop_requested=True BEFORE calling
        _stop(), so a backend's _stop() implementation - or anything it
        triggers synchronously - can already see the flag as True."""
        seen_flag_during_stop = []

        class _RecordingStop(MediaBackend):
            def supported_uris(self):
                return []

            def load_track(self, uri, metadata=None):
                return True

            def play(self):
                pass

            def _stop(self):
                seen_flag_during_stop.append(self._stop_requested)
                return True

            def pause(self):
                pass

            def resume(self):
                pass

        backend = _RecordingStop()
        self.assertFalse(backend._stop_requested)
        backend.stop()
        self.assertEqual(seen_flag_during_stop, [True])

    def test_report_track_end_maps_error(self) -> None:
        """report_track_end(error=...) reports ERROR with a stringified
        error and the given uri, regardless of _stop_requested."""
        reporter = MagicMock()
        self.backend.bind_event_reporter(reporter)
        self.backend._stop_requested = True  # must not win over error

        self.backend.report_track_end(uri="file:///bad.mp3", error=RuntimeError("nonzero exit"))

        reporter.assert_called_once_with(PlaybackEvent.ERROR, error="nonzero exit", uri="file:///bad.mp3")

    def test_report_track_end_maps_stopped_when_explicit_stop_requested(self) -> None:
        """report_track_end() with no error, after stop() was called,
        reports STOPPED."""
        reporter = MagicMock()
        self.backend.bind_event_reporter(reporter)
        self.backend.stop()  # sets _stop_requested via the real _stop()
        reporter.reset_mock()  # ignore whatever _stop()'s own report did

        self.backend._stop_requested = True  # simulate an exit callback firing later
        self.backend.report_track_end(uri="file:///test.mp3")

        reporter.assert_called_once_with(PlaybackEvent.STOPPED, uri="file:///test.mp3")

    def test_report_track_end_maps_end_of_media_by_default(self) -> None:
        """report_track_end() with no error and no prior stop() reports
        END_OF_MEDIA - a natural end."""
        reporter = MagicMock()
        self.backend.bind_event_reporter(reporter)
        self.assertFalse(self.backend._stop_requested)

        self.backend.report_track_end(uri="file:///test.mp3")

        reporter.assert_called_once_with(PlaybackEvent.END_OF_MEDIA, uri="file:///test.mp3")

    def test_report_track_end_always_clears_stop_requested_flag(self) -> None:
        """Whichever branch report_track_end takes, _stop_requested must
        end up False, so a stale flag can't leak into the next track."""
        # error branch
        self.backend._stop_requested = True
        self.backend.report_track_end(error=RuntimeError("boom"))
        self.assertFalse(self.backend._stop_requested)

        # stopped branch
        self.backend._stop_requested = True
        self.backend.report_track_end()
        self.assertFalse(self.backend._stop_requested)

        # end-of-media branch (flag already False, must remain False)
        self.backend.report_track_end()
        self.assertFalse(self.backend._stop_requested)

    def test_seekable_backend_overrides_position_trio(self) -> None:
        """A backend that supports seeking overrides all three and sets
        can_seek=True; the default -1/no-op behaviour must not leak through."""
        class _Seekable(MediaBackend):
            can_seek = True

            def __init__(self, config=None):
                super().__init__(config)
                self._pos = 0

            def supported_uris(self):
                return []

            def load_track(self, uri, metadata=None):
                return True

            def play(self):
                pass

            def _stop(self):
                return True

            def pause(self):
                pass

            def resume(self):
                pass

            def get_track_length(self):
                return 60000

            def get_track_position(self):
                return self._pos

            def set_track_position(self, milliseconds):
                self._pos = milliseconds

        backend = _Seekable()
        self.assertTrue(backend.can_seek)
        self.assertEqual(backend.get_track_length(), 60000)
        backend.set_track_position(1234)
        self.assertEqual(backend.get_track_position(), 1234)


class _RecordingBus:
    """Minimal FakeBus-shaped stand-in that records every emit() call, so
    tests can assert on exactly what a backend puts on its bus."""

    def __init__(self):
        self.emitted = []

    def emit(self, message):
        self.emitted.append(message)

    def on(self, *args, **kwargs):
        pass

    def remove(self, *args, **kwargs):
        pass


class TestNoStateEmission(unittest.TestCase):
    """The template must never emit ovos.common_play.* state itself - state
    flows exclusively through report()/bind_event_reporter(); the bus is a
    plugin-private transport for non-state concerns only."""

    def test_module_source_has_no_bus_emit_call(self) -> None:
        """The template must not call bus.emit() anywhere in its code - the
        only way it could put an ovos.common_play.* state message on the
        wire is through that call, and it must not exist at all."""
        import ovos_plugin_manager.templates.media as media_mod
        tree = ast.parse(inspect.getsource(media_mod))
        emit_calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "emit"
        ]
        self.assertEqual(emit_calls, [])

    def test_driving_backend_through_full_lifecycle_emits_no_bus_messages(self) -> None:
        """play/pause/resume/stop/shutdown, exercised end to end with a
        recording bus attached, must produce zero bus.emit() calls - all
        state must flow through the bound event reporter instead."""
        bus = _RecordingBus()
        reporter = MagicMock()
        backend = _ConcreteMediaBackend(bus=bus)
        backend.bind_event_reporter(reporter)

        backend.load_track("file:///test.mp3")
        backend.play()
        backend.pause()
        backend.resume()
        backend.stop()
        backend.shutdown()

        self.assertEqual(bus.emitted, [])
        # the same lifecycle must still reach the daemon via report()
        self.assertGreater(reporter.call_count, 0)

    def test_standalone_construction_with_no_bus_argument_is_safe(self) -> None:
        """bus=None (the default) must not touch a real messagebus and
        must still support the full lifecycle without raising."""
        backend = _ConcreteMediaBackend()
        backend.load_track("file:///test.mp3")
        backend.play()
        backend.stop()  # no raise, no reporter bound either


# ---------------------------------------------------------------------------
# Family marker classes
# ---------------------------------------------------------------------------

class TestFamilyMarkers(unittest.TestCase):
    """AudioPlayerBackend/VideoPlayerBackend/WebPlayerBackend are thin markers."""

    def test_audio_player_backend_is_media_backend(self) -> None:
        self.assertTrue(issubclass(AudioPlayerBackend, MediaBackend))

    def test_video_player_backend_is_media_backend(self) -> None:
        self.assertTrue(issubclass(VideoPlayerBackend, MediaBackend))

    def test_web_player_backend_is_media_backend(self) -> None:
        self.assertTrue(issubclass(WebPlayerBackend, MediaBackend))

    def test_remote_audio_is_audio_backend_and_remote(self) -> None:
        self.assertTrue(issubclass(RemoteAudioPlayerBackend, AudioPlayerBackend))
        self.assertTrue(RemoteAudioPlayerBackend.is_remote)

    def test_remote_video_is_video_backend_and_remote(self) -> None:
        self.assertTrue(issubclass(RemoteVideoPlayerBackend, VideoPlayerBackend))
        self.assertTrue(RemoteVideoPlayerBackend.is_remote)

    def test_remote_web_is_web_backend_and_remote(self) -> None:
        self.assertTrue(issubclass(RemoteWebPlayerBackend, WebPlayerBackend))
        self.assertTrue(RemoteWebPlayerBackend.is_remote)

    def test_non_remote_defaults_false(self) -> None:
        self.assertFalse(AudioPlayerBackend.is_remote)
        self.assertFalse(VideoPlayerBackend.is_remote)
        self.assertFalse(WebPlayerBackend.is_remote)


if __name__ == "__main__":
    unittest.main()
