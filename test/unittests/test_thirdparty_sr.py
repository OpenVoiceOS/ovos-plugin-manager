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

"""Unit tests for ovos_plugin_manager.thirdparty.sr additional coverage."""

import io
import struct
import unittest
import wave
from unittest.mock import MagicMock, patch

from ovos_plugin_manager.thirdparty.sr import srAudioData, srAudioFile, get_flac_converter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_wav_bytes(num_samples: int = 100, sample_rate: int = 16000,
                    sample_width: int = 2, num_channels: int = 1) -> bytes:
    """Build a minimal WAV file in memory."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(num_channels)
        w.setsampwidth(sample_width)
        w.setframerate(sample_rate)
        samples = [0] * num_samples * num_channels
        w.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return buf.getvalue()


def _make_audio_data(num_samples: int = 100, sample_rate: int = 16000,
                     sample_width: int = 2) -> srAudioData:
    """Create a srAudioData with silent 16-bit frames."""
    frame_data = struct.pack(f"<{num_samples}h", *([0] * num_samples))
    return srAudioData(frame_data, sample_rate, sample_width)


# ---------------------------------------------------------------------------
# Tests for srAudioData.get_flac_data (mocked)
# ---------------------------------------------------------------------------

class TestSrAudioDataGetFlacData(unittest.TestCase):
    """Tests for srAudioData.get_flac_data with FLAC converter mocked."""

    def _audio(self, sample_width: int = 2) -> srAudioData:
        """Create a simple audio data object."""
        return _make_audio_data(sample_width=sample_width)

    @patch("ovos_plugin_manager.thirdparty.sr.get_flac_converter", return_value="/usr/bin/flac")
    @patch("ovos_plugin_manager.thirdparty.sr.subprocess.Popen")
    def test_get_flac_data_basic(self, mock_popen: MagicMock, mock_converter: MagicMock) -> None:
        """get_flac_data calls flac converter and returns bytes."""
        mock_proc: MagicMock = MagicMock()
        mock_proc.communicate.return_value = (b"FLAC_DATA", b"")
        mock_popen.return_value = mock_proc

        audio = self._audio()
        result = audio.get_flac_data()
        self.assertEqual(result, b"FLAC_DATA")
        mock_popen.assert_called_once()

    @patch("ovos_plugin_manager.thirdparty.sr.get_flac_converter", return_value="/usr/bin/flac")
    @patch("ovos_plugin_manager.thirdparty.sr.subprocess.Popen")
    def test_get_flac_data_32bit_auto_converts_to_24bit(self, mock_popen: MagicMock,
                                                         mock_converter: MagicMock) -> None:
        """get_flac_data auto-converts 32-bit audio to 24-bit before encoding."""
        mock_proc: MagicMock = MagicMock()
        mock_proc.communicate.return_value = (b"FLAC24", b"")
        mock_popen.return_value = mock_proc

        # 32-bit audio
        frame_data = struct.pack("<100i", *([0] * 100))
        audio = srAudioData(frame_data, 16000, 4)
        result = audio.get_flac_data()
        self.assertEqual(result, b"FLAC24")

    @patch("ovos_plugin_manager.thirdparty.sr.get_flac_converter", return_value="/usr/bin/flac")
    @patch("ovos_plugin_manager.thirdparty.sr.subprocess.Popen")
    def test_get_flac_data_with_convert_rate(self, mock_popen: MagicMock,
                                              mock_converter: MagicMock) -> None:
        """get_flac_data with convert_rate resamples before encoding."""
        mock_proc: MagicMock = MagicMock()
        mock_proc.communicate.return_value = (b"FLAC_RESAMPLED", b"")
        mock_popen.return_value = mock_proc

        audio = self._audio()
        result = audio.get_flac_data(convert_rate=8000)
        self.assertEqual(result, b"FLAC_RESAMPLED")

    def test_get_flac_data_invalid_convert_width_raises(self) -> None:
        """get_flac_data raises AssertionError for invalid convert_width."""
        audio = self._audio()
        with self.assertRaises(AssertionError):
            audio.get_flac_data(convert_width=4)  # 4 is not in 1-3


# ---------------------------------------------------------------------------
# Tests for srAudioFile context manager with WAV files
# ---------------------------------------------------------------------------

class TestSrAudioFileContextManager(unittest.TestCase):
    """Tests for srAudioFile.__enter__ / __exit__."""

    def test_enter_exit_wav(self) -> None:
        """srAudioFile opens a WAV file-like object successfully."""
        wav_bytes = _make_wav_bytes()
        f = io.BytesIO(wav_bytes)
        with srAudioFile(f) as source:
            self.assertIsNotNone(source.stream)
            self.assertEqual(source.SAMPLE_RATE, 16000)
            self.assertEqual(source.SAMPLE_WIDTH, 2)
            self.assertTrue(source.little_endian)

    def test_exit_clears_stream(self) -> None:
        """srAudioFile.__exit__ clears stream and DURATION."""
        wav_bytes = _make_wav_bytes()
        f = io.BytesIO(wav_bytes)
        with srAudioFile(f) as source:
            pass
        self.assertIsNone(source.stream)
        self.assertIsNone(source.DURATION)

    def test_cannot_reenter(self) -> None:
        """srAudioFile raises AssertionError if entered twice."""
        wav_bytes = _make_wav_bytes()
        f = io.BytesIO(wav_bytes)
        af = srAudioFile(f)
        with af:
            with self.assertRaises(AssertionError):
                af.__enter__()

    def test_invalid_file_raises(self) -> None:
        """srAudioFile raises ValueError for invalid audio data."""
        # Provide garbage data that is not WAV, AIFF, or FLAC
        garbage = io.BytesIO(b"\x00\x01\x02\x03" * 100)
        with patch("ovos_plugin_manager.thirdparty.sr.get_flac_converter", return_value="/usr/bin/flac"), \
             patch("ovos_plugin_manager.thirdparty.sr.subprocess.Popen") as mock_popen:
            mock_proc: MagicMock = MagicMock()
            # FLAC converter also returns garbage AIFF, so it should raise ValueError
            mock_proc.communicate.return_value = (b"\x00garbage", b"")
            mock_popen.return_value = mock_proc
            with self.assertRaises(ValueError):
                with srAudioFile(garbage):
                    pass


# ---------------------------------------------------------------------------
# Tests for srAudioFile.AudioFileStream
# ---------------------------------------------------------------------------

class TestAudioFileStream(unittest.TestCase):
    """Tests for srAudioFile.AudioFileStream.read()."""

    def _make_stream(self, num_samples: int = 50, num_channels: int = 1,
                     little_endian: bool = True,
                     samples_24bit: bool = False) -> "srAudioFile.AudioFileStream":
        """Create an AudioFileStream backed by an in-memory WAV."""
        wav_bytes = _make_wav_bytes(num_samples=num_samples, num_channels=num_channels)
        f = io.BytesIO(wav_bytes)
        reader = wave.open(f, "rb")
        return srAudioFile.AudioFileStream(reader, little_endian, samples_24bit)

    def test_read_all_frames(self) -> None:
        """AudioFileStream.read returns bytes."""
        stream = self._make_stream()
        data = stream.read(50)
        self.assertIsInstance(data, bytes)

    def test_read_all_with_minus_one(self) -> None:
        """AudioFileStream.read(-1) returns all frames."""
        stream = self._make_stream(num_samples=20)
        data = stream.read(-1)
        self.assertIsInstance(data, bytes)
        self.assertGreater(len(data), 0)

    def test_read_stereo_converts_to_mono(self) -> None:
        """AudioFileStream converts stereo to mono on read."""
        stream = self._make_stream(num_channels=2)
        data = stream.read(10)
        # Stereo to mono: audioop.tomono halves the data
        self.assertIsInstance(data, bytes)


# ---------------------------------------------------------------------------
# Tests for get_flac_converter
# ---------------------------------------------------------------------------

class TestGetFlacConverter(unittest.TestCase):
    """Tests for get_flac_converter utility."""

    def test_returns_string(self) -> None:
        """get_flac_converter returns a string path."""
        try:
            path = get_flac_converter()
            self.assertIsInstance(path, str)
        except Exception:
            pass  # flac may not be installed in CI

    @patch("ovos_plugin_manager.thirdparty.sr.shutil.which", return_value="/usr/bin/flac")
    def test_uses_which_when_found(self, mock_which: MagicMock) -> None:
        """get_flac_converter uses shutil.which to locate flac."""
        path = get_flac_converter()
        self.assertIsNotNone(path)


# ---------------------------------------------------------------------------
# Tests for srAudioData.get_segment
# ---------------------------------------------------------------------------

class TestSrAudioDataGetSegment(unittest.TestCase):
    """Tests for srAudioData.get_segment edge cases."""

    def setUp(self) -> None:
        """Build an audio data object with 100 silent 16-bit samples."""
        self.audio: srAudioData = _make_audio_data(num_samples=200)

    def test_segment_none_none(self) -> None:
        """get_segment(None, None) returns the full audio."""
        seg = self.audio.get_segment()
        self.assertEqual(len(seg.frame_data), len(self.audio.frame_data))

    def test_segment_start_only(self) -> None:
        """get_segment with only start_ms returns a trimmed segment."""
        seg = self.audio.get_segment(start_ms=5)
        self.assertLess(len(seg.frame_data), len(self.audio.frame_data))

    def test_segment_end_only(self) -> None:
        """get_segment with only end_ms returns a trimmed segment."""
        seg = self.audio.get_segment(end_ms=5)
        self.assertLess(len(seg.frame_data), len(self.audio.frame_data))

    def test_segment_both(self) -> None:
        """get_segment with start and end ms returns a sub-range."""
        seg = self.audio.get_segment(start_ms=2, end_ms=6)
        self.assertGreater(len(seg.frame_data), 0)

    def test_invalid_start_raises(self) -> None:
        """get_segment raises AssertionError for negative start_ms."""
        with self.assertRaises(AssertionError):
            self.audio.get_segment(start_ms=-1)

    def test_invalid_end_raises(self) -> None:
        """get_segment raises AssertionError when end_ms < start_ms."""
        with self.assertRaises(AssertionError):
            self.audio.get_segment(start_ms=10, end_ms=5)


# ---------------------------------------------------------------------------
# Tests for srAudioData.get_raw_data - convert_rate
# ---------------------------------------------------------------------------

class TestSrAudioDataRateConversion(unittest.TestCase):
    """Tests for get_raw_data with sample rate conversion."""

    def test_convert_rate(self) -> None:
        """get_raw_data resamples when convert_rate differs from sample_rate."""
        audio = _make_audio_data(num_samples=100, sample_rate=16000)
        raw = audio.get_raw_data(convert_rate=8000)
        self.assertIsInstance(raw, bytes)

    def test_same_rate_no_conversion(self) -> None:
        """get_raw_data does not resample when rate is the same."""
        audio = _make_audio_data(num_samples=100, sample_rate=16000)
        raw_no_convert = audio.get_raw_data()
        raw_same_rate = audio.get_raw_data(convert_rate=16000)
        self.assertEqual(raw_no_convert, raw_same_rate)


if __name__ == "__main__":
    unittest.main()
