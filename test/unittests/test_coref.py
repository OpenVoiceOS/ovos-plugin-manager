import unittest

from ovos_plugin_manager.coreference import CoreferenceSolverEngine


class TestCoref(unittest.TestCase):
    def test_coref(self):
        solver = CoreferenceSolverEngine()

        self.assertFalse(solver.contains_corefs("FOSS is awesome"))
        self.assertFalse(solver.contains_corefs("That is a cool story bro"))

        text = "Turn on the light and change it to blue"
        solved = "Turn on the light and change the light to blue"
        self.assertTrue(solver.contains_corefs(text))
        self.assertEqual(solver.extract_replacements(text, solved),
                         {'it': ['the light']})

        text = "My sister has a dog. She loves him"
        solved = "My sister has a dog. My sister loves a dog"
        self.assertTrue(solver.contains_corefs(text))
        self.assertEqual(solver.extract_replacements(text, solved),
                         {'him': ['a dog'], 'she': ['my sister']})

        solver.add_context("her", "mom")
        text = "tell her to buy eggs"
        self.assertTrue(solver.contains_corefs(text))
        self.assertEqual(solver.replace_coreferences_with_context(text),
                         "tell mom to buy eggs")
        text = "tell her to buy coffee"
        self.assertTrue(solver.contains_corefs(text))
        self.assertEqual(solver.replace_coreferences_with_context(text),
                         "tell mom to buy coffee")
        text = "tell her to buy milk"
        self.assertTrue(solver.contains_corefs(text))
        self.assertEqual(solver.replace_coreferences_with_context(text),
                         "tell mom to buy milk")
