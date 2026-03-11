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

"""Tests for TTS uncovered paths: plugin_id, _init_playback, stop, ConcatTTS, StreamingTTS."""

import asyncio
import os
import tempfile
import unittest
from typing import AsyncIterable, Optional, Set, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

from ovos_plugin_manager.templates.tts import (
    ConcatTTS,
    StreamingTTS,
    StreamingTTSCallbacks,
    TTS,
    TTSContext,
    TTSValidator,
)


# ---------------------------------------------------------------------------
# Concrete subclasses
# ---------------------------------------------------------------------------

class _DummyTTS(TTS):
    """Minimal TTS for test use."""

    @classmethod
    def available_languages(cls) -> Set[str]:
        """Return supported languages."""
        return {"en-us"}

    def get_tts(self, sentence: str, wav_file: str,
                lang: Optional[str] = None,
                voice: Optional[str] = None) -> Tuple[str, None]:
        """Write a dummy WAV and return it."""
        with open(wav_file, "wb") as f:
            f.write(b"RIFF" + b"\x00" * 36)
        return wav_file, None


class _DummyConcatTTS(ConcatTTS):
    """Minimal ConcatTTS implementation."""

    @classmethod
    def available_languages(cls) -> Set[str]:
        """Return supported languages."""
        return {"en-us"}

    def sentence_to_files(self, sentence: str) -> Tuple[list, Optional[str]]:
        """Return empty file list and no phonemes."""
        return [], None


class _DummyStreamingTTS(StreamingTTS):
    """Minimal StreamingTTS implementation."""

    @classmethod
    def available_languages(cls) -> Set[str]:
        """Return supported languages."""
        return {"en-us"}

    async def stream_tts(self, sentence: str, **kwargs) -> AsyncIterable[bytes]:
        """Yield a single chunk of audio bytes."""
        yield b"\x00" * 1024
        yield b"\x00" * 1024


# ---------------------------------------------------------------------------
# Tests for TTS.plugin_id property
# ---------------------------------------------------------------------------

class TestTTSPluginId(unittest.TestCase):
    """Tests for TTS.plugin_id auto-discovery and fallback."""

    def test_plugin_id_empty_when_not_registered(self) -> None:
        """plugin_id returns '' when plugin is not found in the registry."""
        tts = _DummyTTS(config={})
        with patch("ovos_plugin_manager.tts.find_tts_plugins", return_value={}):
            pid = tts.plugin_id
        self.assertEqual(pid, "")

    def test_plugin_id_found_in_registry(self) -> None:
        """plugin_id returns the registered plugin name."""
        tts = _DummyTTS(config={})
        tts._plugin_id = ""  # reset cache
        with patch("ovos_plugin_manager.tts.find_tts_plugins",
                   return_value={"my.tts.plugin": _DummyTTS}):
            pid = tts.plugin_id
        self.assertEqual(pid, "my.tts.plugin")

    def test_plugin_id_cached(self) -> None:
        """plugin_id is cached after first resolution."""
        tts = _DummyTTS(config={})
        tts._plugin_id = "cached-id"
        # Should return cached value without calling find_tts_plugins
        self.assertEqual(tts.plugin_id, "cached-id")


# ---------------------------------------------------------------------------
# Tests for TTS._init_playback
# ---------------------------------------------------------------------------

class TestTTSInitPlayback(unittest.TestCase):
    """Tests for TTS._init_playback."""

    def setUp(self) -> None:
        """Reset class-level playback state."""
        TTS.playback = None

    def test_init_playback_sets_playback(self) -> None:
        """_init_playback stores the playback thread on the class."""
        tts = _DummyTTS(config={})
        mock_playback: MagicMock = MagicMock()
        mock_playback.enclosure = None
        mock_playback.is_alive.return_value = False
        mock_bus: MagicMock = MagicMock()
        tts.bus = mock_bus
        tts._init_playback(mock_playback)
        self.assertIs(TTS.playback, mock_playback)

    def test_init_playback_starts_thread_when_not_alive(self) -> None:
        """_init_playback starts the thread if not already alive."""
        tts = _DummyTTS(config={})
        mock_playback: MagicMock = MagicMock()
        mock_playback.enclosure = MagicMock()  # already set
        mock_playback.is_alive.return_value = False
        tts.bus = MagicMock()
        tts._init_playback(mock_playback)
        mock_playback.start.assert_called_once()

    def test_init_playback_skips_start_when_alive(self) -> None:
        """_init_playback does not start thread if already running."""
        tts = _DummyTTS(config={})
        mock_playback: MagicMock = MagicMock()
        mock_playback.enclosure = MagicMock()
        mock_playback.is_alive.return_value = True
        tts.bus = MagicMock()
        tts._init_playback(mock_playback)
        mock_playback.start.assert_not_called()


# ---------------------------------------------------------------------------
# Tests for TTS.init
# ---------------------------------------------------------------------------

class TestTTSInit(unittest.TestCase):
    """Tests for TTS.init method."""

    def test_init_raises_without_playback(self) -> None:
        """TTS.init raises ValueError when playback is None."""
        tts = _DummyTTS(config={})
        with self.assertRaises(ValueError):
            tts.init(bus=MagicMock(), playback=None)

    def test_init_sets_bus(self) -> None:
        """TTS.init stores the provided bus."""
        tts = _DummyTTS(config={})
        mock_bus: MagicMock = MagicMock()
        mock_playback: MagicMock = MagicMock()
        mock_playback.enclosure = MagicMock()
        mock_playback.is_alive.return_value = True
        tts.init(bus=mock_bus, playback=mock_playback)
        self.assertIs(tts.bus, mock_bus)


# ---------------------------------------------------------------------------
# Tests for TTS.stop / shutdown
# ---------------------------------------------------------------------------

class TestTTSStop(unittest.TestCase):
    """Tests for TTS.stop and TTS.shutdown."""

    def setUp(self) -> None:
        """Reset playback state."""
        TTS.playback = None

    def test_stop_when_no_playback(self) -> None:
        """stop() does not raise when TTS.playback is None."""
        tts = _DummyTTS(config={})
        TTS.playback = None
        tts.stop()  # Should not raise

    def test_stop_calls_playback_stop(self) -> None:
        """stop() calls playback.stop() when playback exists."""
        tts = _DummyTTS(config={})
        mock_playback: MagicMock = MagicMock()
        TTS.playback = mock_playback
        tts.stop()
        self.assertTrue(mock_playback.stop.called)

    def test_stop_ignores_playback_exception(self) -> None:
        """stop() swallows exceptions from playback.stop()."""
        tts = _DummyTTS(config={})
        mock_playback: MagicMock = MagicMock()
        mock_playback.stop.side_effect = RuntimeError("oops")
        TTS.playback = mock_playback
        tts.stop()  # Should not raise

    def test_shutdown_calls_stop(self) -> None:
        """shutdown() calls stop()."""
        tts = _DummyTTS(config={})
        tts.stop = MagicMock()
        tts.shutdown()
        tts.stop.assert_called_once()


# ---------------------------------------------------------------------------
# Tests for TTS.viseme
# ---------------------------------------------------------------------------

class TestTTSViseme(unittest.TestCase):
    """Tests for TTS.viseme phoneme-to-viseme conversion."""

    def setUp(self) -> None:
        """Create a TTS instance."""
        self.tts: _DummyTTS = _DummyTTS(config={})

    def test_viseme_empty_phonemes(self) -> None:
        """viseme returns None for empty phonemes string."""
        result = self.tts.viseme("")
        self.assertIsNone(result)

    def test_viseme_with_duration(self) -> None:
        """viseme parses 'phoneme:duration' format."""
        result = self.tts.viseme("AA:0.1 B:0.2")
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        code, dur = result[0]
        self.assertIsInstance(code, str)
        self.assertIsInstance(dur, float)

    def test_viseme_without_duration(self) -> None:
        """viseme parses bare phoneme tokens with default duration 0.2."""
        result = self.tts.viseme("AA BB")
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        for code, dur in result:
            self.assertAlmostEqual(dur, 0.2)


# ---------------------------------------------------------------------------
# Tests for TTS._replace_phonetic_spellings
# ---------------------------------------------------------------------------

class TestTTSPhoneticSpellings(unittest.TestCase):
    """Tests for TTS._replace_phonetic_spellings."""

    def test_no_spellings_dict(self) -> None:
        """_replace_phonetic_spellings returns unchanged sentence when no entry."""
        tts = _DummyTTS(config={})
        result = tts._replace_phonetic_spellings("hello world", "en-US")
        self.assertEqual(result, "hello world")

    def test_with_spellings(self) -> None:
        """_replace_phonetic_spellings substitutes matching words."""
        tts = _DummyTTS(config={})
        tts.spellings = {"en-US": {"hello": "helo"}}
        result = tts._replace_phonetic_spellings("hello world", "en-US")
        self.assertEqual(result, "helo world")

    def test_phonetic_spelling_disabled(self) -> None:
        """_replace_phonetic_spellings skips when phonetic_spelling=False."""
        tts = _DummyTTS(config={})
        tts.phonetic_spelling = False
        tts.spellings = {"en-US": {"hello": "helo"}}
        result = tts._replace_phonetic_spellings("hello world", "en-US")
        self.assertEqual(result, "hello world")


# ---------------------------------------------------------------------------
# Tests for TTS.load_spellings with config arg warning
# ---------------------------------------------------------------------------

class TestTTSLoadSpellings(unittest.TestCase):
    """Tests for TTS.load_spellings."""

    def test_load_spellings_with_config_warns(self) -> None:
        """load_spellings logs a warning when config argument is passed."""
        tts = _DummyTTS(config={})
        result = tts.load_spellings(config={"deprecated": True})
        self.assertIsInstance(result, dict)


# ---------------------------------------------------------------------------
# Tests for TTSContext.get_from_cache hit
# ---------------------------------------------------------------------------

class TestTTSContextCacheHit(unittest.TestCase):
    """Tests for TTSContext.get_from_cache on a cached sentence."""

    def setUp(self) -> None:
        """Clear caches."""
        TTSContext._caches.clear()

    def test_get_from_cache_hit(self) -> None:
        """get_from_cache returns (audio_file, phonemes) for a cached sentence."""
        from ovos_plugin_manager.utils.tts_cache import hash_sentence

        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = TTSContext(plugin_id="t", lang="en-US", voice="d")
            cfg = {
                "preloaded_cache": os.path.join(tmpdir, "cache"),
                "min_free_percent": 75,
                "persist_cache": False,
                "persist_thresh": 1,
            }
            cache = ctx.get_cache(audio_ext="wav", cache_config=cfg)
            sentence = "test sentence"
            h = hash_sentence(sentence)

            # Create a fake audio file object
            mock_audio: MagicMock = MagicMock()
            mock_audio.name = f"{h}.wav"

            cache.cached_sentences[h] = (mock_audio, None)

            audio_file, phonemes = ctx.get_from_cache(sentence, cache_config=cfg)
            self.assertIs(audio_file, mock_audio)
            self.assertIsNone(phonemes)


# ---------------------------------------------------------------------------
# Tests for ConcatTTS
# ---------------------------------------------------------------------------

class TestConcatTTS(unittest.TestCase):
    """Tests for ConcatTTS base class."""

    def test_concat_tts_init(self) -> None:
        """ConcatTTS initialises with time_step, channels, rate."""
        tts = _DummyConcatTTS(config={})
        self.assertEqual(tts.time_step, 0.1)
        self.assertEqual(tts.channels, "1")
        self.assertEqual(tts.rate, "16000")

    def test_concat_tts_min_time_step(self) -> None:
        """ConcatTTS enforces minimum time_step of 0.1."""
        tts = _DummyConcatTTS(config={"time_step": 0.01})
        self.assertEqual(tts.time_step, 0.1)

    def test_concat_tts_custom_config(self) -> None:
        """ConcatTTS stores custom config values."""
        tts = _DummyConcatTTS(config={"channels": "2", "rate": "22050", "time_step": 0.5})
        self.assertEqual(tts.channels, "2")
        self.assertEqual(tts.rate, "22050")
        self.assertAlmostEqual(tts.time_step, 0.5)

    @patch("ovos_plugin_manager.templates.tts.subprocess.check_output")
    def test_concat_method_skips_missing_files(self, mock_check: MagicMock) -> None:
        """concat skips files that do not exist."""
        mock_check.return_value = b""
        tts = _DummyConcatTTS(config={})
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "out.wav")
            result = tts.concat(["nonexistent.wav"], out)
        self.assertEqual(result, out)

    def test_get_tts_calls_sentence_to_files(self) -> None:
        """ConcatTTS.get_tts delegates to sentence_to_files then concat."""
        tts = _DummyConcatTTS(config={})
        tts.sentence_to_files = MagicMock(return_value=([], None))
        tts.concat = MagicMock(return_value="/tmp/out.wav")
        wav, phonemes = tts.get_tts("hello", "/tmp/out.wav")
        tts.sentence_to_files.assert_called_once_with("hello")
        tts.concat.assert_called_once()
        self.assertEqual(wav, "/tmp/out.wav")
        self.assertIsNone(phonemes)


# ---------------------------------------------------------------------------
# Tests for StreamingTTSCallbacks
# ---------------------------------------------------------------------------

class TestStreamingTTSCallbacks(unittest.TestCase):
    """Tests for StreamingTTSCallbacks."""

    def _make_callbacks(self) -> StreamingTTSCallbacks:
        """Create callbacks with a mock bus and explicit player."""
        bus: MagicMock = MagicMock()
        return StreamingTTSCallbacks(bus=bus, play_args=["cat", "-"])

    def test_stream_start_emits_messages(self) -> None:
        """stream_start emits duck and audio_output_start messages."""
        cb = self._make_callbacks()
        with patch("ovos_plugin_manager.templates.tts.subprocess.Popen") as mock_popen:
            mock_proc: MagicMock = MagicMock()
            mock_popen.return_value = mock_proc
            cb.stream_start()
        cb.bus.emit.assert_called()

    def test_stream_chunk_writes_to_process(self) -> None:
        """stream_chunk writes data to the subprocess stdin."""
        cb = self._make_callbacks()
        mock_proc: MagicMock = MagicMock()
        cb._process = mock_proc
        cb.stream_chunk(b"\x00" * 512)
        mock_proc.stdin.write.assert_called_once_with(b"\x00" * 512)
        mock_proc.stdin.flush.assert_called_once()

    def test_stream_chunk_no_process(self) -> None:
        """stream_chunk does nothing when _process is None."""
        cb = self._make_callbacks()
        cb._process = None
        cb.stream_chunk(b"\x00" * 512)  # Should not raise

    def test_stream_stop_closes_process(self) -> None:
        """stream_stop closes stdin and waits for process."""
        cb = self._make_callbacks()
        mock_proc: MagicMock = MagicMock()
        cb._process = mock_proc
        cb.stream_stop()
        mock_proc.stdin.close.assert_called_once()
        mock_proc.wait.assert_called_once()
        self.assertIsNone(cb._process)

    def test_stream_stop_emits_messages(self) -> None:
        """stream_stop emits unduck and audio_output_end messages."""
        cb = self._make_callbacks()
        mock_proc: MagicMock = MagicMock()
        cb._process = mock_proc
        cb.stream_stop()
        cb.bus.emit.assert_called()

    def test_stream_stop_with_listen_emits_listen(self) -> None:
        """stream_stop with listen=True emits mycroft.mic.listen."""
        cb = self._make_callbacks()
        cb._process = None
        cb.stream_stop(listen=True)
        emitted_types = [c.args[0].msg_type for c in cb.bus.emit.call_args_list]
        self.assertIn("mycroft.mic.listen", emitted_types)

    def test_stream_start_stops_existing_process(self) -> None:
        """stream_start calls stream_stop if a process is already running."""
        cb = self._make_callbacks()
        mock_proc: MagicMock = MagicMock()
        cb._process = mock_proc
        with patch("ovos_plugin_manager.templates.tts.subprocess.Popen") as mock_popen:
            new_proc: MagicMock = MagicMock()
            mock_popen.return_value = new_proc
            cb.stream_start()
        # Old process should have been closed
        mock_proc.stdin.close.assert_called()

    def test_pulse_duck_suppresses_duck_message(self) -> None:
        """stream_start skips duck message when pulse_duck=True."""
        bus: MagicMock = MagicMock()
        cb = StreamingTTSCallbacks(bus=bus, play_args=["cat", "-"],
                                   tts_config={"pulse_duck": True})
        with patch("ovos_plugin_manager.templates.tts.subprocess.Popen") as mock_popen:
            mock_popen.return_value = MagicMock()
            cb.stream_start()
        emitted_types = [c.args[0].msg_type for c in bus.emit.call_args_list]
        self.assertNotIn("ovos.common_play.duck", emitted_types)

    def test_no_player_raises(self) -> None:
        """StreamingTTSCallbacks raises RuntimeError when no audio player found."""
        bus: MagicMock = MagicMock()
        with patch("ovos_plugin_manager.templates.tts.shutil.which", return_value=None):
            with self.assertRaises(RuntimeError):
                StreamingTTSCallbacks(bus=bus)


# ---------------------------------------------------------------------------
# Tests for StreamingTTS.get_tts
# ---------------------------------------------------------------------------

class TestStreamingTTSGetTts(unittest.TestCase):
    """Tests for StreamingTTS.get_tts (synchronous usage)."""

    def test_get_tts_returns_wav_and_no_phonemes(self) -> None:
        """get_tts writes audio and returns (wav_file, None)."""
        tts = _DummyStreamingTTS(config={})
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "out.wav")
            result_path, phonemes = tts.get_tts("hello", out)
        self.assertIsNone(phonemes)
        self.assertEqual(result_path, out)


if __name__ == "__main__":
    unittest.main()
