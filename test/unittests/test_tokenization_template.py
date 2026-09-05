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

"""Unit tests for ovos_plugin_manager.templates.tokenization.Tokenizer."""

import unittest
from typing import List, Optional, Tuple

from ovos_plugin_manager.templates.tokenization import Tokenizer


class _WordTokenizer(Tokenizer):
    """Simple whitespace tokenizer for testing."""

    def span_tokenize(self, text: str, lang: Optional[str] = None) -> List[Tuple[int, int, str]]:
        """Return (start, end, token) tuples for each word."""
        spans = []
        pos = 0
        for word in text.split():
            start = text.index(word, pos)
            end = start + len(word)
            spans.append((start, end, word))
            pos = end
        return spans


class TestTokenizer(unittest.TestCase):
    """Tests for Tokenizer base class."""

    def setUp(self) -> None:
        """Create tokenizer instance."""
        self.tok = _WordTokenizer(config={"lang": "en-us"})

    def test_init_config(self) -> None:
        """Tokenizer stores config."""
        self.assertEqual(self.tok.config["lang"], "en-us")

    def test_init_default_config(self) -> None:
        """Tokenizer uses empty dict for missing config."""
        tok = _WordTokenizer()
        self.assertEqual(tok.config, {})

    def test_lang_from_config(self) -> None:
        """lang property reads from config."""
        lang = self.tok.lang
        self.assertIsInstance(lang, str)

    def test_span_tokenize(self) -> None:
        """span_tokenize returns list of (start, end, token) tuples."""
        spans = self.tok.span_tokenize("hello world")
        self.assertEqual(len(spans), 2)
        self.assertEqual(spans[0][2], "hello")
        self.assertEqual(spans[1][2], "world")

    def test_tokenize(self) -> None:
        """tokenize returns list of token strings."""
        tokens = self.tok.tokenize("hello world")
        self.assertEqual(tokens, ["hello", "world"])

    def test_tokenize_empty(self) -> None:
        """tokenize returns empty list for empty string."""
        tokens = self.tok.tokenize("")
        self.assertEqual(tokens, [])

    def test_restore_spans(self) -> None:
        """restore_spans reconstructs text from spans."""
        spans = self.tok.span_tokenize("hello world")
        restored = Tokenizer.restore_spans(spans)
        self.assertIn("hello", restored)
        self.assertIn("world", restored)

    def test_restore_spans_with_gap(self) -> None:
        """restore_spans adds space when gap detected."""
        # spans with a gap (start > len(sentence))
        spans = [(0, 5, "hello"), (10, 15, "world")]
        result = Tokenizer.restore_spans(spans)
        self.assertIn("hello", result)
        self.assertIn("world", result)

    def test_runtime_requirements(self) -> None:
        """runtime_requirements returns a RuntimeRequirements."""
        reqs = _WordTokenizer.runtime_requirements
        self.assertIsNotNone(reqs)


if __name__ == "__main__":
    unittest.main()
