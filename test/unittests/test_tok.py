import unittest
from ovos_plugin_manager.tokenization import Tokenizer


class TestTokenizer(unittest.TestCase):

    def test_tok(self):
        tokenizer = Tokenizer()
        spans = tokenizer.span_tokenize("Once upon a time there was a free and open voice assistant")
        self.assertEqual(tokenizer.restore_spans(spans), "Once upon a time there was a free and open voice assistant")
        self.assertEqual(spans,
                         [(0, 4, 'Once'),
                          (5, 9, 'upon'),
                          (10, 11, 'a'),
                          (12, 16, 'time'),
                          (17, 22, 'there'),
                          (23, 26, 'was'),
                          (27, 28, 'a'),
                          (29, 33, 'free'),
                          (34, 37, 'and'),
                          (38, 42, 'open'),
                          (43, 48, 'voice'),
                          (49, 58, 'assistant')])

