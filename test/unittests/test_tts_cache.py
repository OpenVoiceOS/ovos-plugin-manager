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

"""Unit tests for ovos_plugin_manager.utils.tts_cache."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from ovos_plugin_manager.utils.tts_cache import (
    AudioFile,
    PhonemeFile,
    TextToSpeechCache,
    _delete_oldest,
    _get_cache_entries,
    curate_cache,
    hash_from_path,
    hash_sentence,
    mb_to_bytes,
)


class TestHashFunctions(unittest.TestCase):
    """Tests for hash utility functions."""

    def test_hash_sentence_returns_string(self) -> None:
        """hash_sentence returns a hex string."""
        result = hash_sentence("hello world")
        self.assertIsInstance(result, str)
        self.assertEqual(len(result), 32)  # md5 hex length

    def test_hash_sentence_deterministic(self) -> None:
        """Same sentence produces same hash."""
        h1 = hash_sentence("test sentence")
        h2 = hash_sentence("test sentence")
        self.assertEqual(h1, h2)

    def test_hash_sentence_different_inputs(self) -> None:
        """Different sentences produce different hashes."""
        h1 = hash_sentence("hello")
        h2 = hash_sentence("world")
        self.assertNotEqual(h1, h2)

    def test_hash_from_path(self) -> None:
        """hash_from_path strips extension and folder."""
        p = Path("/cache/tts/abcdef123456.wav")
        result = hash_from_path(p)
        self.assertEqual(result, "abcdef123456")

    def test_mb_to_bytes(self) -> None:
        """mb_to_bytes converts correctly."""
        self.assertEqual(mb_to_bytes(1), 1024 * 1024)
        self.assertEqual(mb_to_bytes(10), 10 * 1024 * 1024)


class TestAudioFile(unittest.TestCase):
    """Tests for AudioFile class."""

    def setUp(self) -> None:
        """Create temp dir for cache operations."""
        self.tmpdir = tempfile.mkdtemp()
        self.cache_dir = Path(self.tmpdir)
        self.audio_file = AudioFile(self.cache_dir, "abc123", "wav")

    def tearDown(self) -> None:
        """Remove temp files."""
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_name(self) -> None:
        """AudioFile name is hash.ext."""
        self.assertEqual(self.audio_file.name, "abc123.wav")

    def test_path(self) -> None:
        """AudioFile path is cache_dir / name."""
        self.assertEqual(self.audio_file.path, self.cache_dir / "abc123.wav")

    def test_str(self) -> None:
        """str(AudioFile) returns path string."""
        self.assertEqual(str(self.audio_file), str(self.cache_dir / "abc123.wav"))

    def test_exists_false(self) -> None:
        """exists returns False for missing file."""
        self.assertFalse(self.audio_file.exists())

    def test_save_and_load(self) -> None:
        """save writes file, load reads it back."""
        audio_data = b"fake wav data"
        self.audio_file.save(audio_data)
        self.assertTrue(self.audio_file.exists())
        loaded = AudioFile(self.cache_dir, "abc123", "wav")
        result = loaded.load()
        self.assertEqual(result, audio_data)

    def test_load_nonexistent(self) -> None:
        """load returns None for nonexistent file."""
        result = self.audio_file.load()
        self.assertIsNone(result)

    def test_cache_dir_as_string(self) -> None:
        """AudioFile accepts str cache_dir."""
        af = AudioFile(self.tmpdir, "test123", "mp3")
        self.assertIsInstance(af.path, Path)

    def test_save_stores_audio_data(self) -> None:
        """save sets audio_data attribute."""
        self.audio_file.save(b"data")
        self.assertEqual(self.audio_file.audio_data, b"data")


class TestPhonemeFile(unittest.TestCase):
    """Tests for PhonemeFile class."""

    def setUp(self) -> None:
        """Create temp dir."""
        self.tmpdir = tempfile.mkdtemp()
        self.cache_dir = Path(self.tmpdir)
        self.pho_file = PhonemeFile(self.cache_dir, "abc123")

    def tearDown(self) -> None:
        """Remove temp files."""
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_name(self) -> None:
        """PhonemeFile name is hash.pho."""
        self.assertEqual(self.pho_file.name, "abc123.pho")

    def test_exists_false(self) -> None:
        """exists returns False for missing file."""
        self.assertFalse(self.pho_file.exists())

    def test_save_and_load(self) -> None:
        """save writes phonemes, load reads them back."""
        phonemes = [["HH", 0.1], ["AH", 0.1]]
        self.pho_file.save(phonemes)
        self.assertTrue(self.pho_file.exists())
        loaded = PhonemeFile(self.cache_dir, "abc123")
        result = loaded.load()
        self.assertEqual(result, phonemes)

    def test_load_nonexistent(self) -> None:
        """load returns None for nonexistent file."""
        result = self.pho_file.load()
        self.assertIsNone(result)

    def test_str(self) -> None:
        """str(PhonemeFile) returns path string."""
        self.assertEqual(str(self.pho_file), str(self.cache_dir / "abc123.pho"))

    def test_cache_dir_as_string(self) -> None:
        """PhonemeFile accepts str cache_dir."""
        pf = PhonemeFile(self.tmpdir, "test123")
        self.assertIsInstance(pf.path, Path)

    def test_save_stores_phonemes(self) -> None:
        """save sets phonemes attribute."""
        phonemes = [["B", 0.1]]
        self.pho_file.save(phonemes)
        self.assertEqual(self.pho_file.phonemes, phonemes)


class TestTextToSpeechCache(unittest.TestCase):
    """Tests for TextToSpeechCache."""

    def setUp(self) -> None:
        """Create cache with temp directories."""
        self.tmpdir = tempfile.mkdtemp()
        self.config = {
            "preloaded_cache": os.path.join(self.tmpdir, "persistent"),
            "min_free_percent": 75,
            "persist_cache": False,
            "persist_thresh": 1,
        }
        os.makedirs(self.config["preloaded_cache"], exist_ok=True)
        with patch("ovos_plugin_manager.utils.tts_cache.get_tmp_cache_dir",
                   return_value=os.path.join(self.tmpdir, "tmp")):
            self.cache = TextToSpeechCache(self.config, "test_tts", "wav")

    def tearDown(self) -> None:
        """Remove temp files."""
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_init(self) -> None:
        """TextToSpeechCache initialises correctly."""
        self.assertEqual(self.cache.tts_name, "test_tts")
        self.assertEqual(self.cache.audio_file_type, "wav")

    def test_contains_false_unknown(self) -> None:
        """__contains__ returns False for unknown hash."""
        self.assertNotIn("unknown_hash", self.cache)

    def test_define_audio_file_tmp(self) -> None:
        """define_audio_file returns AudioFile in tmp dir by default."""
        af = self.cache.define_audio_file("abc123")
        self.assertIsInstance(af, AudioFile)

    def test_define_audio_file_persistent(self) -> None:
        """define_audio_file with persistent=True uses persistent dir."""
        af = self.cache.define_audio_file("abc123", persistent=True)
        self.assertIn("persistent", str(af.path))

    def test_define_phoneme_file(self) -> None:
        """define_phoneme_file returns PhonemeFile."""
        pf = self.cache.define_phoneme_file("abc123")
        self.assertIsInstance(pf, PhonemeFile)

    def test_define_phoneme_file_persistent(self) -> None:
        """define_phoneme_file with persistent=True uses persistent dir."""
        pf = self.cache.define_phoneme_file("abc123", persistent=True)
        self.assertIn("persistent", str(pf.path))

    def test_should_persist_false_by_default(self) -> None:
        """_should_persist returns False when persist=False."""
        self.assertFalse(self.cache._should_persist("any_hash"))

    def test_should_persist_true_when_configured(self) -> None:
        """_should_persist returns True when persist=True and thresh reached."""
        self.cache.persist = True
        self.cache.persist_thresh = 2
        # First call - not yet reached
        self.assertFalse(self.cache._should_persist("hash1"))
        # Second call - threshold reached
        self.assertTrue(self.cache._should_persist("hash1"))

    def test_contains_with_existing_audio(self) -> None:
        """__contains__ returns True when audio file exists on disk."""
        sentence_hash = hash_sentence("hello world")
        af = self.cache.define_audio_file(sentence_hash, persistent=True)
        af.save(b"fake audio data")
        self.cache.cached_sentences[sentence_hash] = (af, None)
        self.assertIn(sentence_hash, self.cache)

    def test_contains_missing_audio(self) -> None:
        """__contains__ returns False when audio file not on disk."""
        sentence_hash = "missing_hash"
        af = AudioFile(self.cache.temporary_cache_dir, sentence_hash, "wav")
        self.cache.cached_sentences[sentence_hash] = (af, None)
        self.assertNotIn(sentence_hash, self.cache)

    def test_load_persistent_cache_empty(self) -> None:
        """load_persistent_cache works with empty directory."""
        self.cache.load_persistent_cache()
        # Should not raise

    def test_clear(self) -> None:
        """clear removes temporary cache files."""
        # Write a temp file
        tmp_file = self.cache.temporary_cache_dir / "test.wav"
        tmp_file.write_bytes(b"data")
        self.cache.clear()
        self.assertFalse(tmp_file.exists())

    def test_curate_no_directory(self) -> None:
        """curate handles missing temp directory gracefully."""
        import shutil
        shutil.rmtree(str(self.cache.temporary_cache_dir), ignore_errors=True)
        self.cache.curate()  # Should not raise


class TestCurateCache(unittest.TestCase):
    """Tests for curate_cache and helper functions."""

    def test_curate_cache_not_a_directory(self) -> None:
        """curate_cache raises NotADirectoryError for non-existing path."""
        with self.assertRaises(NotADirectoryError):
            curate_cache("/path/that/does/not/exist")

    def test_mb_to_bytes_zero(self) -> None:
        """mb_to_bytes(0) returns 0."""
        self.assertEqual(mb_to_bytes(0), 0)

    def test_delete_oldest_empty(self) -> None:
        """_delete_oldest with empty entries returns empty list."""
        result = _delete_oldest(iter([]), 1000)
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
