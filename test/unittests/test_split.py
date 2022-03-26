import unittest

from ovos_plugin_manager.segmentation import Segmenter


class TestQuebraFrasesSegmenter(unittest.TestCase):

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

        # test marker joined sentences
        self.assertEqual(solver.segment("Turn on the lights and play some music"),
                         ["Turn on the lights", "play some music"])
        self.assertEqual(solver.segment("Make the lights red then play communist music"),
                         ['Make the lights red', 'play communist music'])

    @unittest.skip("know segmentation failures, new plugins should handle these")
    def test_known_failures(self):
        solver = Segmenter()
        self.assertEqual(solver.segment(
            "This is a test This is another test"),
            ["This is a test", "This is another test"])
        self.assertEqual(solver.segment(
            "I am Batman I live in gotham"),
            ["I am Batman", "I live in gotham"])
