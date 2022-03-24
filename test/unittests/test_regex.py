import unittest

from lingua_franca.internal import load_language

from ovos_plugin_manager.templates.intents import IntentExtractor


class TestRegex(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        load_language("en-us")  # setup LF normalizer

        intents = IntentExtractor()
        play = ["^play (?P<Music>.+)$"]
        location = [".*(at|in) (?P<Location>.+)$"]
        intents.register_regex_entity("Music", play)
        intents.register_regex_entity("Location", location)

        self.engine = intents

    def test_regex_entity(self):

        def test_entities(sent, entities):
            res = self.engine.extract_regex_entities(sent)
            self.assertEqual(res, entities)

        test_entities("bork the zork", {})
        test_entities("how is the weather in Paris", {'Location': 'paris'})
        test_entities("play metallica", {'Music': 'metallica'})

