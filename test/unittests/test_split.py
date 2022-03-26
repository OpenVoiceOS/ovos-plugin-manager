import unittest

from ovos_plugin_manager.segmentation import Segmenter, find_segmentation_plugins


class TestQuebraFrasesSegmenter(unittest.TestCase):

    def test_find_plugin(self):
        plugs = find_segmentation_plugins()
        self.assertTrue(len(plugs) > 0)
        self.assertIn("ovos-segmentation-plugin-quebrafrases", plugs)

    def test_segment(self):
        solver = Segmenter()
        # test quebra frases segmentation in punctuation
        test_sent = "Mr. Smith bought cheapsite.com for 1.5 million " \
                    "dollars, i.e. he paid a lot for it. Did he mind? Adam " \
                    "Jones Jr. thinks he didn't. In any case, this isn't true..." \
                    " Well, with a probability of .9 it isn't."
        self.assertEqual(
            solver.segment(test_sent),
            [
                'Mr. Smith bought cheapsite.com for 1.5 million dollars, i.e. he paid a lot for it.',
                'Did he mind?',
                "Adam Jones Jr. thinks he didn't.",
                "In any case, this isn't true...",
                "Well, with a probability of .9 it isn't."
            ]
        )

        # test lang marker joined sentences
        self.assertEqual(solver.segment("Turn on the lights and play some music"),
                         ["Turn on the lights", "play some music"])
        self.assertEqual(solver.segment("Make the lights red then play communist music"),
                         ['Make the lights red', 'play communist music'])
        self.assertEqual(
            solver.segment("tell me a joke and say hello"),
            ['tell me a joke', 'say hello'])
        self.assertEqual(
            solver.segment("tell me a joke and the weather"),
            ['tell me a joke', 'the weather'])

    def test_punc_settings(self):
        # test split at commas
        solver = Segmenter()
        solver2 = Segmenter(config={"split_commas": True, "split_punc": False})
        solver3 = Segmenter(config={"split_commas": False, "split_punc": True})
        solver4 = Segmenter(config={"split_commas": True, "split_punc": True})

        self.assertNotEqual(
            solver.segment("turn off the lights, open the door"),
            ['turn off the lights', 'open the door'])
        self.assertEqual(
            solver2.segment("turn off the lights, open the door"),
            ['turn off the lights', 'open the door'])
        self.assertNotEqual(
            solver3.segment("turn off the lights, open the door"),
            ['turn off the lights', 'open the door'])
        self.assertEqual(
            solver4.segment("turn off the lights, open the door"),
            ['turn off the lights', 'open the door'])

        self.assertNotEqual(
            solver.segment("nice work! get me a beer"),
            ['nice work', 'get me a beer'])
        self.assertNotEqual(
            solver2.segment("nice work! get me a beer"),
            ['nice work', 'get me a beer'])
        self.assertEqual(
            solver3.segment("nice work! get me a beer"),
            ['nice work', 'get me a beer'])
        self.assertEqual(
            solver4.segment("nice work! get me a beer"),
            ['nice work', 'get me a beer'])

    @unittest.skip("know segmentation failures, new plugins should handle these")
    def test_known_failures(self):
        solver = Segmenter()
        self.assertEqual(solver.segment(
            "This is a test This is another test"),
            ["This is a test", "This is another test"])
        self.assertEqual(solver.segment(
            "I am Batman I live in gotham"),
            ["I am Batman", "I live in gotham"])

    def test_segment_pt(self):
        # dig_for_message is used internally and takes priority over config lang
        solver = Segmenter({"lang": "pt-pt"})

        # test quebra frases segmentation in punctuation
        test_sent = "O Sr. Smith comprou o dominio sitebarato.pt por 1,5 milhões de dólares. " \
                    "Ele importou-se? " \
                    "Adam Jones Jr. acha que não. " \
                    "De qualquer forma, isto não é verdade... " \
                    "Bem, com uma probabilidade de .9 não é."

        self.assertEqual(
            solver.segment(test_sent),
            ['O Sr. Smith comprou o dominio sitebarato.pt por 1,5 milhões de dólares.',
             'Ele importou-se?',
             'Adam Jones Jr. acha que não.',
             'De qualquer forma, isto não é verdade...',
             'Bem, com uma probabilidade de .9 não é.']
        )

        # test lang marker joined sentences
        self.assertEqual(solver.segment("Liga a luz e bota ai um som"),
                         ['Liga a luz', 'bota ai um som'])
        self.assertEqual(solver.segment("Põe a luz vermelha e toca musica comunista"),
                         ['Põe a luz vermelha', 'toca musica comunista'])
        self.assertEqual(solver.segment("conta uma piada e depois desliga-te"),
                         ['conta uma piada', 'desliga-te'])
