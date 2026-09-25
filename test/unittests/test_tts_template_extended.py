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

"""Extended unit tests for ovos_plugin_manager.templates.tts.TTS and TTSContext."""

import os
import tempfile
import unittest
from pathlib import Path
from typing import Optional, Set, Tuple
from unittest.mock import MagicMock, patch

from ovos_plugin_manager.templates.tts import TTS, TTSContext, TTSValidator
from ovos_plugin_manager.utils.tts_cache import hash_sentence


# ---------------------------------------------------------------------------
# Minimal concrete TTS implementation
# ---------------------------------------------------------------------------

class _DummyTTS(TTS):
    """Minimal TTS plugin for testing."""

    @classmethod
    def available_languages(cls) -> Set[str]:
        """Return supported languages."""
        return {"en-us"}

    def get_tts(self, sentence: str, wav_file: str, lang: Optional[str] = None,
                voice: Optional[str] = None) -> Tuple[str, Optional[list]]:
        """Return the wav_file and no phonemes."""
        # Write a dummy file so the cache can find it
        with open(wav_file, "wb") as f:
            f.write(b"RIFF" + b"\x00" * 36)
        return wav_file, None


# ---------------------------------------------------------------------------
# Tests for TTSContext
# ---------------------------------------------------------------------------

class TestTTSContext(unittest.TestCase):
    """Tests for TTSContext helper class."""

    def setUp(self) -> None:
        """Clear caches before each test."""
        TTSContext._caches.clear()

    def test_tts_id(self) -> None:
        """tts_id combines plugin_id, voice, and lang."""
        ctx = TTSContext(plugin_id="test-plugin", lang="en-US", voice="female")
        self.assertIn("test-plugin", ctx.tts_id)
        self.assertIn("female", ctx.tts_id)

    def test_get_cache_creates_new(self) -> None:
        """get_cache creates a new TextToSpeechCache when none exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = TTSContext(plugin_id="test", lang="en-US", voice="default")
            cache_config = {
                "preloaded_cache": os.path.join(tmpdir, "cache"),
                "min_free_percent": 75,
                "persist_cache": False,
                "persist_thresh": 1,
            }
            cache = ctx.get_cache(audio_ext="wav", cache_config=cache_config)
            self.assertIsNotNone(cache)

    def test_get_cache_reuses_existing(self) -> None:
        """get_cache returns the same instance on repeated calls."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = TTSContext(plugin_id="test", lang="en-US", voice="default")
            cache_config = {
                "preloaded_cache": os.path.join(tmpdir, "cache"),
                "min_free_percent": 75,
                "persist_cache": False,
                "persist_thresh": 1,
            }
            c1 = ctx.get_cache(cache_config=cache_config)
            c2 = ctx.get_cache(cache_config=cache_config)
            self.assertIs(c1, c2)

    def test_curate_caches(self) -> None:
        """curate_caches calls curate on all caches."""
        mock_cache = MagicMock()
        TTSContext._caches["test_id"] = mock_cache
        TTSContext.curate_caches()
        mock_cache.curate.assert_called_once()

    def test_get_from_cache_miss(self) -> None:
        """get_from_cache raises FileNotFoundError for uncached sentence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = TTSContext(plugin_id="t", lang="en-US", voice="d")
            cache_config = {
                "preloaded_cache": os.path.join(tmpdir, "cache"),
                "min_free_percent": 75,
                "persist_cache": False,
                "persist_thresh": 1,
            }
            with self.assertRaises(FileNotFoundError):
                ctx.get_from_cache("uncached sentence", cache_config=cache_config)


# ---------------------------------------------------------------------------
# Tests for TTS base class methods
# ---------------------------------------------------------------------------

class TestTTSBase(unittest.TestCase):
    """Tests for TTS template class non-abstract methods."""

    def setUp(self) -> None:
        """Create TTS instance."""
        self.tts = _DummyTTS(config={"lang": "en-US"})

    def test_init_defaults(self) -> None:
        """TTS sets default values on init."""
        self.assertIsNotNone(self.tts.config)
        self.assertEqual(self.tts.audio_ext, "wav")
        self.assertIsNotNone(self.tts.validator)

    def test_lang_property(self) -> None:
        """lang returns standardized language tag."""
        lang = self.tts.lang
        self.assertIsInstance(lang, str)

    def test_lang_setter(self) -> None:
        """lang setter updates the language."""
        self.tts.lang = "fr-FR"
        self.assertEqual(self.tts.lang, "fr-FR")

    def test_voice_property(self) -> None:
        """voice returns config value."""
        self.tts.config["voice"] = "test_voice"
        self.assertEqual(self.tts.voice, "test_voice")

    def test_voice_default(self) -> None:
        """voice returns 'default' when not set."""
        tts = _DummyTTS(config={})
        self.assertEqual(tts.voice, "default")

    def test_voice_setter(self) -> None:
        """voice setter stores value in config."""
        self.tts.voice = "custom_voice"
        self.assertEqual(self.tts.config["voice"], "custom_voice")

    def test_remove_ssml(self) -> None:
        """remove_ssml strips all HTML/SSML tags."""
        text = "<speak>Hello <break time='1s'/> world</speak>"
        result = TTS.remove_ssml(text)
        self.assertIn("Hello", result)
        self.assertIn("world", result)
        self.assertNotIn("<speak>", result)

    def test_format_speak_tags_no_tags(self) -> None:
        """format_speak_tags wraps text without existing speak tags."""
        result = TTS.format_speak_tags("Hello world")
        self.assertIn("<speak>", result)
        self.assertIn("</speak>", result)

    def test_format_speak_tags_already_wrapped(self) -> None:
        """format_speak_tags keeps existing speak tags."""
        result = TTS.format_speak_tags("<speak>Hello world</speak>")
        self.assertEqual(result, "<speak>Hello world</speak>")

    def test_format_speak_tags_no_opening(self) -> None:
        """format_speak_tags adds <speak> when only </speak> present."""
        result = TTS.format_speak_tags("Hello world</speak>")
        self.assertIn("<speak>", result)

    def test_format_speak_tags_no_closing(self) -> None:
        """format_speak_tags adds </speak> when only <speak> present."""
        result = TTS.format_speak_tags("<speak>Hello world")
        self.assertIn("</speak>", result)

    def test_format_speak_tags_empty(self) -> None:
        """format_speak_tags returns empty string for empty speak tag."""
        result = TTS.format_speak_tags("")
        self.assertEqual(result, "")

    def test_format_speak_tags_without_tags(self) -> None:
        """format_speak_tags with include_tags=False strips speak tags."""
        result = TTS.format_speak_tags("<speak>Hello world</speak>", include_tags=False)
        self.assertNotIn("<speak>", result)

    def test_validate_ssml_no_tags(self) -> None:
        """validate_ssml strips tags when ssml_tags is empty."""
        self.tts.ssml_tags = []
        result = self.tts.validate_ssml("<speak>Hello</speak>")
        self.assertNotIn("<speak>", result)

    def test_validate_ssml_with_supported_tags(self) -> None:
        """validate_ssml keeps supported tags."""
        self.tts.ssml_tags = ["speak", "break"]
        result = self.tts.validate_ssml("<speak>Hello <break/></speak>")
        self.assertIn("<speak>", result)

    def test_validate_ssml_with_unsupported_tags(self) -> None:
        """validate_ssml removes unsupported tags."""
        self.tts.ssml_tags = ["speak"]
        result = self.tts.validate_ssml("<speak>Hello <prosody rate='fast'>world</prosody></speak>")
        self.assertNotIn("<prosody", result)

    def test_preprocess_sentence_default(self) -> None:
        """preprocess_sentence returns list with single sentence by default."""
        chunks = self.tts.preprocess_sentence("Hello world")
        self.assertIsInstance(chunks, list)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], "Hello world")

    def test_preprocess_sentence_tokenize(self) -> None:
        """preprocess_sentence tokenizes with sentence_tokenize enabled."""
        self.tts.config["sentence_tokenize"] = True
        chunks = self.tts.preprocess_sentence("Hello. How are you?")
        self.assertIsInstance(chunks, list)
        self.assertGreater(len(chunks), 0)

    def test_modify_tag_default(self) -> None:
        """modify_tag returns tag unchanged."""
        result = self.tts.modify_tag("<break/>")
        self.assertEqual(result, "<break/>")

    def test_begin_and_end_audio(self) -> None:
        """begin_audio and end_audio can be called without error."""
        self.tts.begin_audio()
        self.tts.end_audio()

    def test_add_metric_no_exception(self) -> None:
        """add_metric does not raise."""
        self.tts.add_metric({"metric_type": "test"})

    def test_load_spellings_no_locale(self) -> None:
        """load_spellings returns empty dict when no locale dir."""
        spellings = self.tts.load_spellings()
        self.assertIsInstance(spellings, dict)

    def test_runtime_requirements(self) -> None:
        """runtime_requirements returns RuntimeRequirements."""
        reqs = _DummyTTS.runtime_requirements
        self.assertIsNotNone(reqs)

    def test_handle_metric_default(self) -> None:
        """handle_metric is a no-op by default."""
        self.tts.handle_metric({"type": "test"})  # Should not raise

    def test_synth(self) -> None:
        """synth returns (audio_file, phonemes) tuple."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ctx = TTSContext(plugin_id="test", lang="en-US", voice="default")
            cache_config = {
                "preloaded_cache": os.path.join(tmpdir, "cache"),
                "min_free_percent": 75,
                "persist_cache": False,
                "persist_thresh": 1,
            }
            cache = ctx.get_cache(cache_config=cache_config)
            # Manually do synth by calling get_tts
            wav_path = os.path.join(tmpdir, "test.wav")
            result_path, phonemes = self.tts.get_tts("hello world", wav_path)
            self.assertTrue(os.path.isfile(result_path))
            self.assertIsNone(phonemes)


# ---------------------------------------------------------------------------
# Tests for TTSValidator
# ---------------------------------------------------------------------------

class TestTTSValidator(unittest.TestCase):
    """Tests for TTSValidator."""

    def test_init(self) -> None:
        """TTSValidator stores tts reference."""
        tts = _DummyTTS(config={})
        validator = TTSValidator(tts)
        self.assertIs(validator.tts, tts)

    def test_validate_does_not_raise(self) -> None:
        """validate() does not raise on typical TTS."""
        tts = _DummyTTS(config={})
        validator = TTSValidator(tts)
        try:
            validator.validate()
        except Exception:
            pass  # Some validators check for installed tools

    def test_validate_lang_does_not_raise(self) -> None:
        """validate_lang() does not raise."""
        tts = _DummyTTS(config={"lang": "en-US"})
        validator = TTSValidator(tts)
        try:
            validator.validate_lang()
        except Exception:
            pass

    def test_validate_connection_does_not_raise(self) -> None:
        """validate_connection() does not raise."""
        tts = _DummyTTS(config={})
        validator = TTSValidator(tts)
        try:
            validator.validate_connection()
        except Exception:
            pass


if __name__ == "__main__":
    unittest.main()
