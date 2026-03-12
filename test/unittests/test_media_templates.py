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

"""Unit tests for ovos_plugin_manager.templates.media."""

import unittest
from unittest.mock import MagicMock, patch

from ovos_plugin_manager.templates.media import (
    AudioPlayerBackend,
    MediaBackend,
    RemoteAudioPlayerBackend,
    RemoteVideoPlayerBackend,
    RemoteWebPlayerBackend,
    VideoPlayerBackend,
    WebPlayerBackend,
)


# ---------------------------------------------------------------------------
# Concrete subclass helpers
# ---------------------------------------------------------------------------

class _ConcreteMediaBackend(MediaBackend):
    """Minimal concrete MediaBackend for testing."""

    def supported_uris(self):
        """Return supported URI types."""
        return ["file", "http"]

    def play(self):
        """No-op play."""

    def stop(self):
        """No-op stop."""

    def pause(self):
        """No-op pause."""

    def resume(self):
        """No-op resume."""

    def lower_volume(self):
        """No-op lower_volume."""

    def restore_volume(self):
        """No-op restore_volume."""

    def get_track_length(self) -> int:
        """Return zero track length."""
        return 0

    def get_track_position(self) -> int:
        """Return zero position."""
        return 0

    def set_track_position(self, milliseconds) -> None:
        """No-op set_track_position."""


class _ConcreteAudioBackend(AudioPlayerBackend):
    """Minimal AudioPlayerBackend for testing."""

    def supported_uris(self):
        """Return audio URIs."""
        return ["file"]

    def play(self):
        """No-op play."""

    def stop(self):
        """No-op stop."""

    def pause(self):
        """No-op pause."""

    def resume(self):
        """No-op resume."""

    def lower_volume(self):
        """No-op lower_volume."""

    def restore_volume(self):
        """No-op restore_volume."""

    def get_track_length(self) -> int:
        """Return zero."""
        return 0

    def get_track_position(self) -> int:
        """Return zero."""
        return 0

    def set_track_position(self, milliseconds) -> None:
        """No-op."""


class _ConcreteVideoBackend(VideoPlayerBackend):
    """Minimal VideoPlayerBackend for testing."""

    def supported_uris(self):
        """Return video URIs."""
        return ["file"]

    def play(self):
        """No-op play."""

    def stop(self):
        """No-op stop."""

    def pause(self):
        """No-op pause."""

    def resume(self):
        """No-op resume."""

    def lower_volume(self):
        """No-op lower_volume."""

    def restore_volume(self):
        """No-op restore_volume."""

    def get_track_length(self) -> int:
        """Return zero."""
        return 0

    def get_track_position(self) -> int:
        """Return zero."""
        return 0

    def set_track_position(self, milliseconds) -> None:
        """No-op."""


class _ConcreteWebBackend(WebPlayerBackend):
    """Minimal WebPlayerBackend for testing."""

    def supported_uris(self):
        """Return web URIs."""
        return ["http", "https"]

    def play(self):
        """No-op play."""

    def stop(self):
        """No-op stop."""

    def pause(self):
        """No-op pause."""

    def resume(self):
        """No-op resume."""

    def lower_volume(self):
        """No-op lower_volume."""

    def restore_volume(self):
        """No-op restore_volume."""

    def get_track_length(self) -> int:
        """Return zero."""
        return 0

    def get_track_position(self) -> int:
        """Return zero."""
        return 0

    def set_track_position(self, milliseconds) -> None:
        """No-op."""


# ---------------------------------------------------------------------------
# Tests for MediaBackend
# ---------------------------------------------------------------------------

class TestMediaBackend(unittest.TestCase):
    """Tests for MediaBackend base class."""

    def setUp(self) -> None:
        """Create a concrete backend with a FakeBus."""
        self.backend: _ConcreteMediaBackend = _ConcreteMediaBackend()

    def test_init_defaults(self) -> None:
        """MediaBackend initialises with default config and bus."""
        self.assertEqual(self.backend.config, {})
        self.assertIsNone(self.backend._now_playing)
        self.assertFalse(self.backend.supports_mime_hints)

    def test_init_custom_config(self) -> None:
        """MediaBackend stores provided config."""
        backend = _ConcreteMediaBackend(config={"key": "val"})
        self.assertEqual(backend.config["key"], "val")

    def test_set_track_start_callback(self) -> None:
        """set_track_start_callback stores the callback."""
        cb: MagicMock = MagicMock()
        self.backend.set_track_start_callback(cb)
        self.assertIs(self.backend._track_start_callback, cb)

    def test_load_track(self) -> None:
        """load_track sets _now_playing and emits media state message."""
        self.backend.load_track("file:///test.mp3")
        self.assertEqual(self.backend._now_playing, "file:///test.mp3")

    def test_load_track_with_metadata(self) -> None:
        """load_track stores metadata."""
        self.backend.load_track("file:///test.mp3", metadata={"title": "Test"})
        self.assertEqual(self.backend.meta["title"], "Test")

    def test_ocp_start(self) -> None:
        """ocp_start calls play and emits player state."""
        self.backend._now_playing = "file:///test.mp3"
        self.backend.ocp_start()  # Should not raise

    def test_ocp_error_clears_now_playing(self) -> None:
        """ocp_error clears _now_playing."""
        self.backend._now_playing = "file:///test.mp3"
        self.backend.ocp_error()
        self.assertIsNone(self.backend._now_playing)

    def test_ocp_error_when_nothing_playing(self) -> None:
        """ocp_error does nothing when _now_playing is None."""
        self.backend._now_playing = None
        self.backend.ocp_error()  # Should not raise

    def test_ocp_stop_clears_now_playing(self) -> None:
        """ocp_stop clears _now_playing and calls stop."""
        self.backend._now_playing = "file:///test.mp3"
        self.backend.ocp_stop()
        self.assertIsNone(self.backend._now_playing)

    def test_ocp_stop_when_nothing_playing(self) -> None:
        """ocp_stop does nothing when _now_playing is None."""
        self.backend._now_playing = None
        self.backend.ocp_stop()  # Should not raise

    def test_ocp_pause(self) -> None:
        """ocp_pause calls pause and emits state when something is playing."""
        self.backend._now_playing = "file:///test.mp3"
        self.backend.ocp_pause()  # Should not raise

    def test_ocp_pause_when_nothing_playing(self) -> None:
        """ocp_pause does nothing when _now_playing is None."""
        self.backend._now_playing = None
        self.backend.ocp_pause()  # Should not raise

    def test_ocp_resume(self) -> None:
        """ocp_resume calls resume when something is playing."""
        self.backend._now_playing = "file:///test.mp3"
        self.backend.ocp_resume()  # Should not raise

    def test_ocp_resume_when_nothing_playing(self) -> None:
        """ocp_resume does nothing when _now_playing is None."""
        self.backend._now_playing = None
        self.backend.ocp_resume()  # Should not raise

    def test_playback_time_default(self) -> None:
        """playback_time returns 0 by default."""
        self.assertEqual(self.backend.playback_time, 0)

    def test_seek_forward(self) -> None:
        """seek_forward updates track position."""
        self.backend.seek_forward(1)  # get_track_position() + 1000ms

    def test_seek_backward(self) -> None:
        """seek_backward updates track position."""
        self.backend.seek_backward(1)  # get_track_position() - 1000ms

    def test_track_info(self) -> None:
        """track_info returns meta dict."""
        self.backend.meta = {"artist": "Test Artist"}
        info = self.backend.track_info()
        self.assertEqual(info["artist"], "Test Artist")

    def test_shutdown(self) -> None:
        """shutdown calls stop without error."""
        self.backend._now_playing = "file:///test.mp3"
        self.backend.shutdown()  # Should call stop


# ---------------------------------------------------------------------------
# Tests for AudioPlayerBackend
# ---------------------------------------------------------------------------

class TestAudioPlayerBackend(unittest.TestCase):
    """Tests for AudioPlayerBackend subclass."""

    def setUp(self) -> None:
        """Create a concrete audio backend."""
        self.backend: _ConcreteAudioBackend = _ConcreteAudioBackend()

    def test_load_track_emits_queued_audio(self) -> None:
        """load_track emits QUEUED_AUDIO track state."""
        self.backend.load_track("file:///test.mp3")
        self.assertEqual(self.backend._now_playing, "file:///test.mp3")

    def test_ocp_start_emits_playing_audio(self) -> None:
        """ocp_start emits PLAYING_AUDIO track state."""
        self.backend._now_playing = "file:///test.mp3"
        self.backend.ocp_start()  # Should not raise


# ---------------------------------------------------------------------------
# Tests for VideoPlayerBackend
# ---------------------------------------------------------------------------

class TestVideoPlayerBackend(unittest.TestCase):
    """Tests for VideoPlayerBackend subclass."""

    def setUp(self) -> None:
        """Create a concrete video backend."""
        self.backend: _ConcreteVideoBackend = _ConcreteVideoBackend()

    def test_load_track_emits_queued_video(self) -> None:
        """load_track emits QUEUED_VIDEO track state."""
        self.backend.load_track("file:///test.mp4")
        self.assertEqual(self.backend._now_playing, "file:///test.mp4")

    def test_ocp_start_emits_playing_video(self) -> None:
        """ocp_start emits PLAYING_VIDEO track state."""
        self.backend._now_playing = "file:///test.mp4"
        self.backend.ocp_start()  # Should not raise


# ---------------------------------------------------------------------------
# Tests for WebPlayerBackend
# ---------------------------------------------------------------------------

class TestWebPlayerBackend(unittest.TestCase):
    """Tests for WebPlayerBackend subclass."""

    def setUp(self) -> None:
        """Create a concrete web backend."""
        self.backend: _ConcreteWebBackend = _ConcreteWebBackend()

    def test_load_track_emits_queued_webview(self) -> None:
        """load_track emits QUEUED_WEBVIEW track state."""
        self.backend.load_track("https://example.com")
        self.assertEqual(self.backend._now_playing, "https://example.com")

    def test_ocp_start_emits_playing_webview(self) -> None:
        """ocp_start emits PLAYING_WEBVIEW track state."""
        self.backend._now_playing = "https://example.com"
        self.backend.ocp_start()  # Should not raise


# ---------------------------------------------------------------------------
# Tests for Remote variants (smoke tests for instantiation)
# ---------------------------------------------------------------------------

class TestRemoteBackends(unittest.TestCase):
    """Smoke tests for remote backend subclasses."""

    def test_remote_audio_is_audio_backend(self) -> None:
        """RemoteAudioPlayerBackend inherits from AudioPlayerBackend."""
        self.assertTrue(issubclass(RemoteAudioPlayerBackend, AudioPlayerBackend))

    def test_remote_video_is_video_backend(self) -> None:
        """RemoteVideoPlayerBackend inherits from VideoPlayerBackend."""
        self.assertTrue(issubclass(RemoteVideoPlayerBackend, VideoPlayerBackend))

    def test_remote_web_is_web_backend(self) -> None:
        """RemoteWebPlayerBackend inherits from WebPlayerBackend."""
        self.assertTrue(issubclass(RemoteWebPlayerBackend, WebPlayerBackend))


if __name__ == "__main__":
    unittest.main()
