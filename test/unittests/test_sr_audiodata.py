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

"""Unit tests for ovos_plugin_manager.thirdparty.sr.srAudioData."""

import io
import struct
import unittest
import wave

from ovos_plugin_manager.thirdparty.sr import srAudioData


def _make_audio_data(num_samples: int = 100, sample_rate: int = 16000,
                     sample_width: int = 2, value: int = 0) -> srAudioData:
    """Create a simple srAudioData instance with silence."""
    frame_data = struct.pack(f"<{num_samples}h", *([value] * num_samples))
    return srAudioData(frame_data, sample_rate, sample_width)


class TestSrAudioDataInit(unittest.TestCase):
    """Tests for srAudioData.__init__."""

    def test_basic_creation(self) -> None:
        """srAudioData can be created with valid parameters."""
        data = _make_audio_data()
        self.assertEqual(data.sample_rate, 16000)
        self.assertEqual(data.sample_width, 2)

    def test_invalid_sample_rate(self) -> None:
        """Zero sample_rate raises AssertionError."""
        with self.assertRaises(AssertionError):
            srAudioData(b"\x00\x00", 0, 2)

    def test_negative_sample_rate(self) -> None:
        """Negative sample_rate raises AssertionError."""
        with self.assertRaises(AssertionError):
            srAudioData(b"\x00\x00", -1, 2)

    def test_invalid_sample_width_zero(self) -> None:
        """Zero sample_width raises AssertionError."""
        with self.assertRaises(AssertionError):
            srAudioData(b"\x00", 16000, 0)

    def test_invalid_sample_width_five(self) -> None:
        """sample_width=5 raises AssertionError."""
        with self.assertRaises(AssertionError):
            srAudioData(b"\x00", 16000, 5)

    def test_sample_width_1(self) -> None:
        """sample_width=1 is valid."""
        data = srAudioData(b"\x80", 16000, 1)
        self.assertEqual(data.sample_width, 1)

    def test_sample_width_4(self) -> None:
        """sample_width=4 is valid."""
        data = srAudioData(b"\x00\x00\x00\x00", 16000, 4)
        self.assertEqual(data.sample_width, 4)


class TestSrAudioDataGetSegment(unittest.TestCase):
    """Tests for srAudioData.get_segment."""

    def setUp(self) -> None:
        """Create 1 second of silence at 16kHz, 16-bit."""
        self.data = _make_audio_data(num_samples=16000)

    def test_full_segment(self) -> None:
        """get_segment with no args returns the same data."""
        seg = self.data.get_segment()
        self.assertEqual(len(seg.frame_data), len(self.data.frame_data))

    def test_start_segment(self) -> None:
        """get_segment with start_ms extracts from that offset."""
        seg = self.data.get_segment(start_ms=500)
        # 500ms of 16kHz 2-byte = 16000 samples * 2 bytes
        self.assertLess(len(seg.frame_data), len(self.data.frame_data))

    def test_end_segment(self) -> None:
        """get_segment with end_ms truncates at that point."""
        seg = self.data.get_segment(end_ms=500)
        self.assertLess(len(seg.frame_data), len(self.data.frame_data))

    def test_start_and_end_segment(self) -> None:
        """get_segment with both start and end."""
        seg = self.data.get_segment(start_ms=100, end_ms=500)
        self.assertGreater(len(seg.frame_data), 0)

    def test_invalid_negative_start(self) -> None:
        """Negative start_ms raises AssertionError."""
        with self.assertRaises(AssertionError):
            self.data.get_segment(start_ms=-1)

    def test_invalid_end_before_start(self) -> None:
        """end_ms before start_ms raises AssertionError."""
        with self.assertRaises(AssertionError):
            self.data.get_segment(start_ms=500, end_ms=100)


class TestSrAudioDataGetRawData(unittest.TestCase):
    """Tests for srAudioData.get_raw_data."""

    def setUp(self) -> None:
        """Create test audio data."""
        self.data = _make_audio_data(num_samples=100)

    def test_no_conversion(self) -> None:
        """get_raw_data without conversion returns original data."""
        raw = self.data.get_raw_data()
        self.assertEqual(raw, self.data.frame_data)

    def test_convert_rate(self) -> None:
        """get_raw_data with convert_rate resamples data."""
        raw = self.data.get_raw_data(convert_rate=8000)
        self.assertIsInstance(raw, bytes)
        # Should be roughly half the size
        self.assertLess(len(raw), len(self.data.frame_data))

    def test_convert_width_to_1(self) -> None:
        """get_raw_data with convert_width=1 converts to 8-bit."""
        raw = self.data.get_raw_data(convert_width=1)
        self.assertIsInstance(raw, bytes)
        # 16-bit -> 8-bit, half the bytes
        self.assertEqual(len(raw), len(self.data.frame_data) // 2)

    def test_convert_width_to_4(self) -> None:
        """get_raw_data with convert_width=4 converts to 32-bit."""
        raw = self.data.get_raw_data(convert_width=4)
        self.assertIsInstance(raw, bytes)
        # 16-bit -> 32-bit, double the bytes
        self.assertEqual(len(raw), len(self.data.frame_data) * 2)

    def test_invalid_convert_rate(self) -> None:
        """convert_rate=0 raises AssertionError."""
        with self.assertRaises(AssertionError):
            self.data.get_raw_data(convert_rate=0)

    def test_invalid_convert_width(self) -> None:
        """convert_width=5 raises AssertionError."""
        with self.assertRaises(AssertionError):
            self.data.get_raw_data(convert_width=5)

    def test_8bit_audio_handling(self) -> None:
        """8-bit audio is handled correctly (signed/unsigned conversion)."""
        # 8-bit unsigned PCM: values 0-255, 128 = silence
        frame_data = bytes([128] * 100)
        data_8bit = srAudioData(frame_data, 16000, 1)
        raw = data_8bit.get_raw_data()
        self.assertIsInstance(raw, bytes)

    def test_convert_width_to_3(self) -> None:
        """get_raw_data with convert_width=3 converts to 24-bit."""
        raw = self.data.get_raw_data(convert_width=3)
        self.assertIsInstance(raw, bytes)


class TestSrAudioDataGetWavData(unittest.TestCase):
    """Tests for srAudioData.get_wav_data."""

    def setUp(self) -> None:
        """Create test audio data."""
        self.data = _make_audio_data(num_samples=100)

    def test_returns_valid_wav(self) -> None:
        """get_wav_data returns bytes that form a valid WAV file."""
        wav_bytes = self.data.get_wav_data()
        self.assertIsInstance(wav_bytes, bytes)
        # WAV files start with RIFF
        self.assertTrue(wav_bytes.startswith(b"RIFF"))

    def test_wav_sample_rate(self) -> None:
        """get_wav_data embeds correct sample rate."""
        wav_bytes = self.data.get_wav_data()
        with wave.open(io.BytesIO(wav_bytes)) as wf:
            self.assertEqual(wf.getframerate(), self.data.sample_rate)

    def test_wav_sample_width(self) -> None:
        """get_wav_data embeds correct sample width."""
        wav_bytes = self.data.get_wav_data()
        with wave.open(io.BytesIO(wav_bytes)) as wf:
            self.assertEqual(wf.getsampwidth(), self.data.sample_width)

    def test_wav_with_rate_conversion(self) -> None:
        """get_wav_data with convert_rate returns WAV at new rate."""
        wav_bytes = self.data.get_wav_data(convert_rate=8000)
        with wave.open(io.BytesIO(wav_bytes)) as wf:
            self.assertEqual(wf.getframerate(), 8000)

    def test_wav_with_width_conversion(self) -> None:
        """get_wav_data with convert_width returns WAV at new width."""
        wav_bytes = self.data.get_wav_data(convert_width=1)
        with wave.open(io.BytesIO(wav_bytes)) as wf:
            self.assertEqual(wf.getsampwidth(), 1)


class TestSrAudioDataGetAiffData(unittest.TestCase):
    """Tests for srAudioData.get_aiff_data."""

    def setUp(self) -> None:
        """Create test audio data."""
        self.data = _make_audio_data(num_samples=100)

    def test_returns_bytes(self) -> None:
        """get_aiff_data returns bytes."""
        aiff_bytes = self.data.get_aiff_data()
        self.assertIsInstance(aiff_bytes, bytes)
        # AIFF files start with FORM
        self.assertTrue(aiff_bytes.startswith(b"FORM"))


if __name__ == "__main__":
    unittest.main()
