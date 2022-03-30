import unittest
from ovos_plugin_manager.postag import PosTagger
from ovos_plugin_manager.tokenization import Tokenizer


class TestDummyPosTagger(unittest.TestCase):

    def test_postag(self):
        solver = PosTagger()
        spans = Tokenizer().span_tokenize("Once upon a time there was a free and open voice assistant")
        # obviously it's almost completely wrong
        self.assertEqual(solver.postag(spans),
                         [(0, 4, 'Once', 'NOUN'),
                          (5, 9, 'upon', 'NOUN'),
                          (10, 11, 'a', 'DET'),
                          (12, 16, 'time', 'NOUN'),
                          (17, 22, 'there', 'NOUN'),
                          (23, 26, 'was', 'VERB'),
                          (27, 28, 'a', 'DET'),
                          (29, 33, 'free', 'NOUN'),
                          (34, 37, 'and', 'CONJ'),
                          (38, 42, 'open', 'NOUN'),
                          (43, 48, 'voice', 'NOUN'),
                          (49, 58, 'assistant', 'NOUN')])
