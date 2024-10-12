import unittest

from unittest.mock import patch
from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes


class TestSegmentationTemplate(unittest.TestCase):
    def test_segment(self):
        from ovos_plugin_manager.templates.segmentation import Segmenter
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
        from ovos_plugin_manager.templates.segmentation import Segmenter
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
        from ovos_plugin_manager.templates.segmentation import Segmenter
        solver = Segmenter()
        self.assertEqual(solver.segment(
            "This is a test This is another test"),
            ["This is a test", "This is another test"])
        self.assertEqual(solver.segment(
            "I am Batman I live in gotham"),
            ["I am Batman", "I live in gotham"])

    def test_segment_pt(self):
        from ovos_plugin_manager.templates.segmentation import Segmenter
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


class TestSegmentation(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.UTTERANCE_SEGMENTATION
    CONFIG_TYPE = PluginConfigTypes.UTTERANCE_SEGMENTATION
    TEST_CONFIG = {"test": True}
    CONFIG_SECTION = "segmentation"
    TEST_LANG = "en-US"

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.segmentation import find_segmentation_plugins
        find_segmentation_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_plugin(self, load_plugin):
        from ovos_plugin_manager.segmentation import load_segmentation_plugin
        load_segmentation_plugin("test_mod")
        load_plugin.assert_called_once_with("test_mod", self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_configs_for_plugin_type")
    def test_get_configs(self, load_configs):
        from ovos_plugin_manager.segmentation import get_segmentation_configs
        get_segmentation_configs()
        load_configs.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_plugin_configs")
    def test_get_module_configs(self, load_plugin_configs):
        from ovos_plugin_manager.segmentation import get_segmentation_module_configs
        get_segmentation_module_configs("test_mod")
        load_plugin_configs.assert_called_once_with("test_mod",
                                                    self.CONFIG_TYPE, True)

    @patch("ovos_plugin_manager.utils.config.get_plugin_language_configs")
    def test_get_lang_configs(self, get_language_configs):
        from ovos_plugin_manager.segmentation import get_segmentation_lang_configs
        get_segmentation_lang_configs(self.TEST_LANG)
        get_language_configs.assert_called_once_with(self.PLUGIN_TYPE,
                                                     self.TEST_LANG, False)

    @patch("ovos_plugin_manager.utils.config.get_plugin_supported_languages")
    def test_get_supported_langs(self, get_supported_languages):
        from ovos_plugin_manager.segmentation import get_segmentation_supported_langs
        get_segmentation_supported_langs()
        get_supported_languages.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.get_plugin_config")
    def test_get_config(self, get_config):
        from ovos_plugin_manager.segmentation import get_segmentation_config
        get_segmentation_config(self.TEST_CONFIG)
        get_config.assert_called_once_with(self.TEST_CONFIG,
                                           self.CONFIG_SECTION)


class TestUtteranceSegmenterFactory(unittest.TestCase):
    from ovos_plugin_manager.segmentation import OVOSUtteranceSegmenterFactory
    # TODO


class TestQuebraFrasesSegmenter(unittest.TestCase):
    def test_find_plugin(self):
        from ovos_plugin_manager.segmentation import find_segmentation_plugins
        plugs = find_segmentation_plugins()
        self.assertTrue(len(plugs) > 0)
        self.assertIn("ovos-segmentation-plugin-quebrafrases", plugs)

