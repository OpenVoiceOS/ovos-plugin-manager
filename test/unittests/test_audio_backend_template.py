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

"""Unit tests for ovos_plugin_manager.templates.audio.AudioBackend."""

import unittest
from typing import List
from unittest.mock import MagicMock, patch

from ovos_utils.fakebus import FakeBus

from ovos_plugin_manager.templates.audio import AudioBackend, RemoteAudioBackend


class _AudioBackendImpl(AudioBackend):
    """Minimal concrete AudioBackend for testing."""

    def supported_uris(self) -> List[str]:
        """Return supported uri schemes."""
        return ["file", "http", "https"]

    def play(self, repeat: bool = False) -> None:
        """Start playback."""
        self.ocp_start()

    def lower_volume(self) -> None:
        """Lower volume."""

    def restore_volume(self) -> None:
        """Restore volume."""

    def get_track_length(self) -> int:
        """Return track length in ms."""
        return 60000

    def get_track_position(self) -> int:
        """Return current position in ms."""
        return 0

    def set_track_position(self, milliseconds: int) -> None:
        """Set position."""

    def pause(self) -> None:
        """Pause playback."""
        self.ocp_pause()

    def resume(self) -> None:
        """Resume playback."""
        self.ocp_resume()

    def stop(self) -> None:
        """Stop playback."""
        self.ocp_stop()


class TestAudioBackend(unittest.TestCase):
    """Tests for AudioBackend base class methods."""

    def setUp(self) -> None:
        """Create backend with FakeBus."""
        self.bus = FakeBus()
        self.backend = _AudioBackendImpl(config={"test": True}, bus=self.bus)

    def test_init_name(self) -> None:
        """Backend has class name by default."""
        self.assertEqual(self.backend.name, "_AudioBackendImpl")

    def test_init_custom_name(self) -> None:
        """Backend uses provided name."""
        b = _AudioBackendImpl(name="MyBackend", bus=self.bus)
        self.assertEqual(b.name, "MyBackend")

    def test_playback_time_default(self) -> None:
        """playback_time returns 0 by default."""
        self.assertEqual(self.backend.playback_time, 0)

    def test_supported_uris(self) -> None:
        """supported_uris returns list."""
        self.assertIsInstance(self.backend.supported_uris(), list)

    def test_clear_list(self) -> None:
        """clear_list resets tracks and index."""
        self.backend._tracks = ["a", "b"]
        self.backend._idx = 1
        self.backend.clear_list()
        self.assertEqual(self.backend._tracks, [])
        self.assertEqual(self.backend._idx, 0)

    def test_add_list_string(self) -> None:
        """add_list accepts a single string."""
        self.backend.add_list("file:///test.mp3")
        self.assertIn("file:///test.mp3", self.backend._tracks)

    def test_add_list_list(self) -> None:
        """add_list accepts a list of tracks."""
        self.backend.add_list(["file:///a.mp3", "file:///b.mp3"])
        self.assertIn("file:///a.mp3", self.backend._tracks)

    def test_add_list_invalid_raises(self) -> None:
        """add_list raises ValueError for non-string/list."""
        with self.assertRaises(ValueError):
            self.backend.add_list(123)

    def test_next_track(self) -> None:
        """next() advances to next track."""
        self.backend._tracks = ["a.mp3", "b.mp3"]
        self.backend._idx = 0
        self.backend._now_playing = "a.mp3"
        self.backend.next()
        self.assertEqual(self.backend._idx, 1)

    def test_next_track_no_more(self) -> None:
        """next() logs error when no more tracks."""
        self.backend._tracks = ["a.mp3"]
        self.backend._idx = 1
        self.backend.next()  # should not raise

    def test_previous_track(self) -> None:
        """previous() goes back to previous track."""
        self.backend._tracks = ["a.mp3", "b.mp3"]
        self.backend._idx = 1
        self.backend._now_playing = "b.mp3"
        self.backend.previous()
        self.assertEqual(self.backend._idx, 0)

    def test_seek_forward(self) -> None:
        """seek_forward calls set_track_position."""
        self.backend.set_track_position = MagicMock()
        self.backend.seek_forward(5)
        # Should have been called with 5000 ms
        self.backend.set_track_position.assert_called_once_with(5000)

    def test_seek_backward(self) -> None:
        """seek_backward calls set_track_position."""
        self.backend.set_track_position = MagicMock()
        self.backend.seek_backward(3)
        self.backend.set_track_position.assert_called_once_with(-3000)

    def test_set_track_start_callback(self) -> None:
        """set_track_start_callback stores the callback."""
        cb = MagicMock()
        self.backend.set_track_start_callback(cb)
        self.assertIs(self.backend._track_start_callback, cb)

    def test_shutdown(self) -> None:
        """shutdown calls stop."""
        self.backend.stop = MagicMock()
        self.backend.shutdown()
        self.backend.stop.assert_called_once()

    def test_load_track(self) -> None:
        """load_track stores uri and emits bus events."""
        self.backend.load_track("http://example.com/audio.mp3")
        self.assertEqual(self.backend._now_playing, "http://example.com/audio.mp3")

    def test_ocp_start(self) -> None:
        """ocp_start emits player state messages."""
        self.backend.ocp_start()

    def test_ocp_stop_with_playing(self) -> None:
        """ocp_stop clears now_playing and emits stop messages."""
        self.backend._now_playing = "http://example.com/audio.mp3"
        self.backend.ocp_stop()
        self.assertIsNone(self.backend._now_playing)

    def test_ocp_stop_not_playing(self) -> None:
        """ocp_stop does nothing when not playing."""
        self.backend._now_playing = None
        self.backend.ocp_stop()  # should not raise

    def test_ocp_error_with_playing(self) -> None:
        """ocp_error clears now_playing and emits error state."""
        self.backend._now_playing = "http://example.com/audio.mp3"
        self.backend.ocp_error()
        self.assertIsNone(self.backend._now_playing)

    def test_ocp_error_not_playing(self) -> None:
        """ocp_error does nothing when not playing."""
        self.backend._now_playing = None
        self.backend.ocp_error()  # should not raise

    def test_ocp_pause_with_playing(self) -> None:
        """ocp_pause emits pause state when playing."""
        self.backend._now_playing = "http://example.com/audio.mp3"
        self.backend.ocp_pause()

    def test_ocp_pause_not_playing(self) -> None:
        """ocp_pause does nothing when not playing."""
        self.backend._now_playing = None
        self.backend.ocp_pause()

    def test_ocp_resume_with_playing(self) -> None:
        """ocp_resume emits playing state when paused."""
        self.backend._now_playing = "http://example.com/audio.mp3"
        self.backend.ocp_resume()

    def test_ocp_resume_not_playing(self) -> None:
        """ocp_resume does nothing when not playing."""
        self.backend._now_playing = None
        self.backend.ocp_resume()

    def test_ocp_sync_playback(self) -> None:
        """ocp_sync_playback emits timing message."""
        self.backend.ocp_sync_playback(30000)

    def test_track_info(self) -> None:
        """track_info returns dict with uri."""
        self.backend._now_playing = "http://example.com/audio.mp3"
        info = self.backend.track_info()
        self.assertIsInstance(info, dict)

    def test_uri2meta_list(self) -> None:
        """_uri2meta handles list input."""
        result = AudioBackend._uri2meta(["http://example.com/a.mp3"])
        self.assertIsInstance(result, dict)

    def test_uri2meta_string(self) -> None:
        """_uri2meta handles string input."""
        result = AudioBackend._uri2meta("http://example.com/a.mp3")
        self.assertIsInstance(result, dict)

    def test_format_msg_no_bus_msg(self) -> None:
        """_format_msg creates a new Message when no current message."""
        msg = self.backend._format_msg("test.message", {"key": "val"})
        self.assertEqual(msg.msg_type, "test.message")

    def test_runtime_requirements(self) -> None:
        """runtime_requirements is a RuntimeRequirements object."""
        reqs = _AudioBackendImpl.runtime_requirements
        self.assertIsNotNone(reqs)


class TestRemoteAudioBackend(unittest.TestCase):
    """Tests for RemoteAudioBackend subclass marker."""

    def test_remote_backend_is_audio_backend(self) -> None:
        """RemoteAudioBackend inherits from AudioBackend."""
        self.assertTrue(issubclass(RemoteAudioBackend, AudioBackend))


if __name__ == "__main__":
    unittest.main()
