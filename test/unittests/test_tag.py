import unittest
from quebra_frases import span_indexed_word_tokenize
from ovos_plugin_manager.postag import PosTagger


class TestDummyPosTagger(unittest.TestCase):

    def test_postag(self):
        solver = PosTagger()
        tokens = span_indexed_word_tokenize("Once upon a time there was a free and open voice assistant")
        # obviously it's almost completely wrong
        self.assertEqual(solver.postag(tokens),
                         [('Once', 'NOUN'),
                          ('upon', 'NOUN'),
                          ('a', 'DET'),
                          ('time', 'NOUN'),
                          ('there', 'NOUN'),
                          ('was', 'VERB'),
                          ('a', 'DET'),
                          ('free', 'NOUN'),
                          ('and', 'CONJ'),
                          ('open', 'NOUN'),
                          ('voice', 'NOUN'),
                          ('assistant', 'NOUN')])
