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

"""Unit tests for ovos_plugin_manager.templates.g2p.Grapheme2PhonemePlugin."""

import unittest
from typing import List, Set
from unittest.mock import MagicMock, patch

from ovos_plugin_manager.templates.g2p import (
    Grapheme2PhonemePlugin,
    OutOfVocabulary,
    PhonemeAlphabet,
)


class _ArpaG2PPlugin(Grapheme2PhonemePlugin):
    """Minimal G2P plugin with ARPA support."""

    @classmethod
    def available_languages(cls) -> Set[str]:
        """Return supported languages."""
        return {"en-us"}

    def get_arpa(self, word: str, lang: str, ignore_oov: bool = False) -> List[str]:
        """Return simple ARPA stub."""
        table = {
            "hello": ["HH", "AH", "L", "OW"],
            "world": ["W", "ER", "L", "D"],
        }
        result = table.get(word.lower())
        if result is None:
            if ignore_oov:
                return None
            raise OutOfVocabulary(f"Unknown word: {word}")
        return result


class _IPAPlugin(Grapheme2PhonemePlugin):
    """Minimal G2P plugin with IPA support."""

    @classmethod
    def available_languages(cls) -> Set[str]:
        """Return supported languages."""
        return {"en-us"}

    def get_ipa(self, word: str, lang: str, ignore_oov: bool = False) -> List[str]:
        """Return simple IPA stub."""
        table = {
            "hello": ["h", "ɛ", "l", "oʊ"],
            "world": ["w", "ɜ", "l", "d"],
        }
        result = table.get(word.lower())
        if result is None:
            if ignore_oov:
                return None
            raise OutOfVocabulary(f"Unknown word: {word}")
        return result


class TestPhonemeAlphabet(unittest.TestCase):
    """Tests for PhonemeAlphabet enum."""

    def test_arpa_value(self) -> None:
        """ARPA has expected value."""
        self.assertEqual(PhonemeAlphabet.ARPA.value, "arpa")

    def test_ipa_value(self) -> None:
        """IPA has expected value."""
        self.assertEqual(PhonemeAlphabet.IPA.value, "ipa")


class TestGrapheme2PhonemePlugin(unittest.TestCase):
    """Tests for Grapheme2PhonemePlugin base class logic."""

    def setUp(self) -> None:
        """Create both plugin types."""
        self.arpa_plugin = _ArpaG2PPlugin(config={"lang": "en-us"})
        self.ipa_plugin = _IPAPlugin(config={"lang": "en-us"})

    def test_init_config(self) -> None:
        """Plugin stores config."""
        self.assertEqual(self.arpa_plugin.config["lang"], "en-us")

    def test_arpa_is_implemented(self) -> None:
        """arpa_is_implemented returns True for ARPA plugin."""
        self.assertTrue(self.arpa_plugin.arpa_is_implemented)

    def test_ipa_is_implemented(self) -> None:
        """ipa_is_implemented returns True for IPA plugin."""
        self.assertTrue(self.ipa_plugin.ipa_is_implemented)

    def test_arpa_not_implemented(self) -> None:
        """arpa_is_implemented returns False for IPA-only plugin."""
        self.assertFalse(self.ipa_plugin.arpa_is_implemented)

    def test_ipa_not_implemented(self) -> None:
        """ipa_is_implemented returns False for ARPA-only plugin."""
        self.assertFalse(self.arpa_plugin.ipa_is_implemented)

    def test_get_arpa(self) -> None:
        """get_arpa returns list of ARPA phonemes."""
        result = self.arpa_plugin.get_arpa("hello", "en-us")
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

    def test_get_arpa_oov_raises(self) -> None:
        """get_arpa raises OutOfVocabulary for unknown word."""
        with self.assertRaises(OutOfVocabulary):
            self.arpa_plugin.get_arpa("xyzzy", "en-us")

    def test_get_arpa_oov_ignore(self) -> None:
        """get_arpa returns None with ignore_oov=True."""
        result = self.arpa_plugin.get_arpa("xyzzy", "en-us", ignore_oov=True)
        self.assertIsNone(result)

    def test_get_ipa_from_arpa(self) -> None:
        """get_ipa converts from ARPA when only arpa is implemented."""
        result = self.arpa_plugin.get_ipa("hello", "en-us")
        # May return empty if arpabet2ipa doesn't have the phoneme, but shouldn't raise
        self.assertIsInstance(result, list)

    def test_get_ipa(self) -> None:
        """get_ipa returns list of IPA phonemes."""
        result = self.ipa_plugin.get_ipa("hello", "en-us")
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

    def test_get_ipa_oov_raises(self) -> None:
        """get_ipa raises OutOfVocabulary for unknown word."""
        with self.assertRaises(OutOfVocabulary):
            self.ipa_plugin.get_ipa("xyzzy", "en-us")

    def test_get_ipa_oov_ignore(self) -> None:
        """get_ipa returns None for unknown word with ignore_oov=True."""
        result = self.ipa_plugin.get_ipa("xyzzy", "en-us", ignore_oov=True)
        self.assertIsNone(result)

    def test_utterance2arpa(self) -> None:
        """utterance2arpa returns list of phonemes for a sentence."""
        result = self.arpa_plugin.utterance2arpa("hello world", "en-us")
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

    def test_utterance2arpa_oov_raises(self) -> None:
        """utterance2arpa raises OutOfVocabulary for unknown word."""
        with self.assertRaises(OutOfVocabulary):
            self.arpa_plugin.utterance2arpa("hello xyzzy", "en-us")

    def test_utterance2arpa_oov_ignore(self) -> None:
        """utterance2arpa ignores OOV words with ignore_oov=True."""
        result = self.arpa_plugin.utterance2arpa("hello xyzzy", "en-us", ignore_oov=True)
        # hello is known, xyzzy is ignored
        self.assertIsInstance(result, list)

    def test_utterance2ipa(self) -> None:
        """utterance2ipa returns list of IPA phonemes."""
        result = self.ipa_plugin.utterance2ipa("hello world", "en-us")
        self.assertIsInstance(result, list)

    def test_utterance2ipa_oov_raises(self) -> None:
        """utterance2ipa raises OutOfVocabulary for unknown word."""
        with self.assertRaises(OutOfVocabulary):
            self.ipa_plugin.utterance2ipa("hello xyzzy", "en-us")

    def test_utterance2ipa_oov_ignore(self) -> None:
        """utterance2ipa ignores OOV with ignore_oov=True."""
        result = self.ipa_plugin.utterance2ipa("hello xyzzy", "en-us", ignore_oov=True)
        self.assertIsInstance(result, list)

    def test_utterance2visemes(self) -> None:
        """utterance2visemes returns list of (viseme, duration) tuples."""
        result = self.arpa_plugin.utterance2visemes("hello world", "en-us")
        self.assertIsInstance(result, list)
        for item in result:
            self.assertEqual(len(item), 2)

    def test_runtime_requirements(self) -> None:
        """runtime_requirements returns RuntimeRequirements."""
        reqs = _ArpaG2PPlugin.runtime_requirements
        self.assertIsNotNone(reqs)

    def test_get_arpa_no_impl_raises(self) -> None:
        """get_arpa raises OutOfVocabulary when neither ARPA nor IPA is implemented."""
        base = Grapheme2PhonemePlugin.__new__(Grapheme2PhonemePlugin)
        base.config = {}
        with self.assertRaises(OutOfVocabulary):
            base.get_arpa("hello", "en-us")

    def test_get_ipa_no_impl_raises(self) -> None:
        """get_ipa raises OutOfVocabulary when neither IPA nor ARPA is implemented."""
        base = Grapheme2PhonemePlugin.__new__(Grapheme2PhonemePlugin)
        base.config = {}
        with self.assertRaises(OutOfVocabulary):
            base.get_ipa("hello", "en-us")

    def test_get_arpa_no_impl_ignore_oov(self) -> None:
        """get_arpa returns None with ignore_oov=True when not implemented."""
        base = Grapheme2PhonemePlugin.__new__(Grapheme2PhonemePlugin)
        base.config = {}
        result = base.get_arpa("hello", "en-us", ignore_oov=True)
        self.assertIsNone(result)

    def test_get_ipa_no_impl_ignore_oov(self) -> None:
        """get_ipa returns None with ignore_oov=True when not implemented."""
        base = Grapheme2PhonemePlugin.__new__(Grapheme2PhonemePlugin)
        base.config = {}
        result = base.get_ipa("hello", "en-us", ignore_oov=True)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
