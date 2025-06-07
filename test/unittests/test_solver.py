import unittest
from unittest.mock import Mock, patch, MagicMock

from ovos_plugin_manager.templates.solvers import QuestionSolver, auto_detect_lang, auto_translate, AbstractSolver
from ovos_plugin_manager.utils import PluginTypes, PluginConfigTypes


# TODO: Test Tldr, Evidence, MultipleChoice, Entailment


class MySolver(QuestionSolver):
    def __init__(self):
        # set the "internal" language, defined by dev, not user
        # this plugin only accepts and outputs english
        config = {"lang": "en"}
        super(MySolver, self).__init__(name="MySolver", priority=100,
                                       config=config, enable_tx=True, enable_cache=True)

    # expected solver methods to be implemented
    def get_data(self, query, context):
        """
        query assured to be in self.default_lang
        return a dict response
        """
        return {"error": "404 answer not found"}

    def get_image(self, query, context=None):
        """
        query assured to be in self.default_lang
        return path/url to a single image to acompany spoken_answer
        """
        return "http://stock.image.jpg"

    def get_spoken_answer(self, query, context=None):
        """
        query assured to be in self.default_lang
        return a single sentence text response
        """
        return "The full answer is XXX"

    def get_expanded_answer(self, query, context=None):
        """
        query assured to be in self.default_lang
        return a list of ordered steps to expand the answer, eg, "tell me more"
        {
            "title": "optional",
            "summary": "speak this",
            "img": "optional/path/or/url
        }
        :return:
        """
        steps = [
            {"title": "the question", "summary": "we forgot the question", "image": "404.jpg"},
            {"title": "the answer", "summary": "but the answer is 42", "image": "42.jpg"}
        ]
        return steps


class TestQuestionSolverBaseMethods(unittest.TestCase):
    def test_internal_cfg(self):
        solver = MySolver()
        self.assertEqual(solver.default_lang, "en")

    def test_get_spoken(self):
        solver = MySolver()
        solver.get_spoken_answer = Mock()
        solver.get_spoken_answer.return_value = "42"

        solver.spoken_cache.clear()
        ans = solver.spoken_answer("some query")
        solver.get_spoken_answer.assert_called()

    def test_get_expanded(self):
        solver = MySolver()
        solver.cache.clear()
        solver.get_expanded_answer = Mock()
        solver.get_expanded_answer.return_value = []

        ans = solver.long_answer("some query")
        solver.get_expanded_answer.assert_called()

    def test_get_image(self):
        solver = MySolver()
        solver.cache.clear()
        solver.get_image = Mock()
        solver.get_image.return_value = "42.jpeg"

        ans = solver.visual_answer("some query")
        solver.get_image.assert_called()

    def test_get_data(self):
        solver = MySolver()
        solver.cache.clear()
        solver.get_data = Mock()
        solver.get_data.return_value = {}

        ans = solver.search("some query")
        solver.get_data.assert_called()

    def test_get_spoken_cache(self):
        solver = MySolver()
        solver.spoken_cache.clear()
        solver.get_spoken_answer = Mock()
        solver.get_spoken_answer.return_value = "42"

        ans = solver.spoken_answer("some query")
        solver.get_spoken_answer.assert_called()

        # now test that the cache is loaded and method not called again
        solver.get_spoken_answer = Mock()
        solver.get_spoken_answer.return_value = "42"
        ans = solver.spoken_answer("some query")
        solver.get_spoken_answer.assert_not_called()

        # clear cache, method is called again
        solver.spoken_cache.clear()
        ans = solver.spoken_answer("some query")
        solver.get_spoken_answer.assert_called()

    def test_get_data_cache(self):
        solver = MySolver()
        solver.cache.clear()
        solver.get_data = Mock()
        solver.get_data.return_value = {"dummy": "42"}

        ans = solver.search("some query")
        solver.get_data.assert_called()

        # now test that the cache is loaded and method not called again
        solver.get_data = Mock()
        solver.get_data.return_value = {"dummy": "42"}
        ans = solver.search("some query")
        solver.get_data.assert_not_called()

        # clear cache, method is called again
        solver.cache.clear()
        ans = solver.search("some query")
        solver.get_data.assert_called()

    def test_translation(self):
        solver = MySolver()
        solver.translator.translate = Mock()
        solver.translator.translate.return_value = "a wild translation appears"

        # no translation
        ans = solver.spoken_answer("some query", lang="en")
        solver.translator.translate.assert_not_called()

        # translation
        ans = solver.spoken_answer("not english", lang="unk")
        solver.translator.translate.assert_called()


class TestQuestionSolver(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.QUESTION_SOLVER
    CONFIG_TYPE = PluginConfigTypes.QUESTION_SOLVER
    TEST_CONFIG = {"test": True}
    CONFIG_SECTION = ""
    TEST_LANG = "en-US"

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.solvers import find_question_solver_plugins
        find_question_solver_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_plugin(self, load_plugin):
        from ovos_plugin_manager.solvers import load_question_solver_plugin
        load_question_solver_plugin("test_mod")
        load_plugin.assert_called_once_with("test_mod", self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_configs_for_plugin_type")
    def test_get_configs(self, load_configs):
        from ovos_plugin_manager.solvers import get_question_solver_configs
        get_question_solver_configs()
        load_configs.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_plugin_configs")
    def test_get_module_configs(self, load_plugin_configs):
        from ovos_plugin_manager.solvers import \
            get_question_solver_module_configs
        get_question_solver_module_configs("test_mod")
        load_plugin_configs.assert_called_once_with("test_mod",
                                                    self.CONFIG_TYPE, True)

    @patch("ovos_plugin_manager.utils.config.get_plugin_language_configs")
    def test_get_lang_configs(self, get_language_configs):
        from ovos_plugin_manager.solvers import \
            get_question_solver_lang_configs
        get_question_solver_lang_configs(self.TEST_LANG)
        get_language_configs.assert_called_once_with(self.PLUGIN_TYPE,
                                                     self.TEST_LANG, False)

    @patch("ovos_plugin_manager.utils.config.get_plugin_supported_languages")
    def test_get_supported_langs(self, get_supported_languages):
        from ovos_plugin_manager.solvers import \
            get_question_solver_supported_langs
        get_question_solver_supported_langs()
        get_supported_languages.assert_called_once_with(self.PLUGIN_TYPE)


class TestTldrSolver(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.TLDR_SOLVER
    CONFIG_TYPE = PluginConfigTypes.TLDR_SOLVER
    TEST_CONFIG = {"test": True}
    CONFIG_SECTION = ""
    TEST_LANG = "en-US"

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.solvers import find_tldr_solver_plugins
        find_tldr_solver_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_plugin(self, load_plugin):
        from ovos_plugin_manager.solvers import load_tldr_solver_plugin
        load_tldr_solver_plugin("test_mod")
        load_plugin.assert_called_once_with("test_mod", self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_configs_for_plugin_type")
    def test_get_configs(self, load_configs):
        from ovos_plugin_manager.solvers import get_tldr_solver_configs
        get_tldr_solver_configs()
        load_configs.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_plugin_configs")
    def test_get_module_configs(self, load_plugin_configs):
        from ovos_plugin_manager.solvers import \
            get_tldr_solver_module_configs
        get_tldr_solver_module_configs("test_mod")
        load_plugin_configs.assert_called_once_with("test_mod",
                                                    self.CONFIG_TYPE, True)

    @patch("ovos_plugin_manager.utils.config.get_plugin_language_configs")
    def test_get_lang_configs(self, get_language_configs):
        from ovos_plugin_manager.solvers import \
            get_tldr_solver_lang_configs
        get_tldr_solver_lang_configs(self.TEST_LANG)
        get_language_configs.assert_called_once_with(self.PLUGIN_TYPE,
                                                     self.TEST_LANG, False)

    @patch("ovos_plugin_manager.utils.config.get_plugin_supported_languages")
    def test_get_supported_langs(self, get_supported_languages):
        from ovos_plugin_manager.solvers import \
            get_tldr_solver_supported_langs
        get_tldr_solver_supported_langs()
        get_supported_languages.assert_called_once_with(self.PLUGIN_TYPE)


class TestEntailmentSolver(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.ENTAILMENT_SOLVER
    CONFIG_TYPE = PluginConfigTypes.ENTAILMENT_SOLVER
    TEST_CONFIG = {"test": True}
    CONFIG_SECTION = ""
    TEST_LANG = "en-US"

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.solvers import find_entailment_solver_plugins
        find_entailment_solver_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_plugin(self, load_plugin):
        from ovos_plugin_manager.solvers import load_entailment_solver_plugin
        load_entailment_solver_plugin("test_mod")
        load_plugin.assert_called_once_with("test_mod", self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_configs_for_plugin_type")
    def test_get_configs(self, load_configs):
        from ovos_plugin_manager.solvers import get_entailment_solver_configs
        get_entailment_solver_configs()
        load_configs.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_plugin_configs")
    def test_get_module_configs(self, load_plugin_configs):
        from ovos_plugin_manager.solvers import \
            get_entailment_solver_module_configs
        get_entailment_solver_module_configs("test_mod")
        load_plugin_configs.assert_called_once_with("test_mod",
                                                    self.CONFIG_TYPE, True)

    @patch("ovos_plugin_manager.utils.config.get_plugin_language_configs")
    def test_get_lang_configs(self, get_language_configs):
        from ovos_plugin_manager.solvers import \
            get_entailment_solver_lang_configs
        get_entailment_solver_lang_configs(self.TEST_LANG)
        get_language_configs.assert_called_once_with(self.PLUGIN_TYPE,
                                                     self.TEST_LANG, False)

    @patch("ovos_plugin_manager.utils.config.get_plugin_supported_languages")
    def test_get_supported_langs(self, get_supported_languages):
        from ovos_plugin_manager.solvers import \
            get_entailment_solver_supported_langs
        get_entailment_solver_supported_langs()
        get_supported_languages.assert_called_once_with(self.PLUGIN_TYPE)


class TestMultipleChoiceSolver(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.MULTIPLE_CHOICE_SOLVER
    CONFIG_TYPE = PluginConfigTypes.MULTIPLE_CHOICE_SOLVER
    TEST_CONFIG = {"test": True}
    CONFIG_SECTION = ""
    TEST_LANG = "en-US"

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.solvers import \
            find_multiple_choice_solver_plugins
        find_multiple_choice_solver_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_plugin(self, load_plugin):
        from ovos_plugin_manager.solvers import \
            load_multiple_choice_solver_plugin
        load_multiple_choice_solver_plugin("test_mod")
        load_plugin.assert_called_once_with("test_mod", self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_configs_for_plugin_type")
    def test_get_configs(self, load_configs):
        from ovos_plugin_manager.solvers import \
            get_multiple_choice_solver_configs
        get_multiple_choice_solver_configs()
        load_configs.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_plugin_configs")
    def test_get_module_configs(self, load_plugin_configs):
        from ovos_plugin_manager.solvers import \
            get_multiple_choice_solver_module_configs
        get_multiple_choice_solver_module_configs("test_mod")
        load_plugin_configs.assert_called_once_with("test_mod",
                                                    self.CONFIG_TYPE, True)

    @patch("ovos_plugin_manager.utils.config.get_plugin_language_configs")
    def test_get_lang_configs(self, get_language_configs):
        from ovos_plugin_manager.solvers import \
            get_multiple_choice_solver_lang_configs
        get_multiple_choice_solver_lang_configs(self.TEST_LANG)
        get_language_configs.assert_called_once_with(self.PLUGIN_TYPE,
                                                     self.TEST_LANG, False)

    @patch("ovos_plugin_manager.utils.config.get_plugin_supported_languages")
    def test_get_supported_langs(self, get_supported_languages):
        from ovos_plugin_manager.solvers import \
            get_multiple_choice_solver_supported_langs
        get_multiple_choice_solver_supported_langs()
        get_supported_languages.assert_called_once_with(self.PLUGIN_TYPE)


class TestReadingComprehensionSolver(unittest.TestCase):
    PLUGIN_TYPE = PluginTypes.READING_COMPREHENSION_SOLVER
    CONFIG_TYPE = PluginConfigTypes.READING_COMPREHENSION_SOLVER
    TEST_CONFIG = {"test": True}
    CONFIG_SECTION = ""
    TEST_LANG = "en-US"

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_plugins(self, find_plugins):
        from ovos_plugin_manager.solvers import \
            find_reading_comprehension_solver_plugins
        find_reading_comprehension_solver_plugins()
        find_plugins.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_plugin(self, load_plugin):
        from ovos_plugin_manager.solvers import \
            load_reading_comprehension_solver_plugin
        load_reading_comprehension_solver_plugin("test_mod")
        load_plugin.assert_called_once_with("test_mod", self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_configs_for_plugin_type")
    def test_get_configs(self, load_configs):
        from ovos_plugin_manager.solvers import \
            get_reading_comprehension_solver_configs
        get_reading_comprehension_solver_configs()
        load_configs.assert_called_once_with(self.PLUGIN_TYPE)

    @patch("ovos_plugin_manager.utils.config.load_plugin_configs")
    def test_get_module_configs(self, load_plugin_configs):
        from ovos_plugin_manager.solvers import \
            get_reading_comprehension_solver_module_configs
        get_reading_comprehension_solver_module_configs("test_mod")
        load_plugin_configs.assert_called_once_with("test_mod",
                                                    self.CONFIG_TYPE, True)

    @patch("ovos_plugin_manager.utils.config.get_plugin_language_configs")
    def test_get_lang_configs(self, get_language_configs):
        from ovos_plugin_manager.solvers import \
            get_reading_comprehension_solver_lang_configs
        get_reading_comprehension_solver_lang_configs(self.TEST_LANG)
        get_language_configs.assert_called_once_with(self.PLUGIN_TYPE,
                                                     self.TEST_LANG, False)

    @patch("ovos_plugin_manager.utils.config.get_plugin_supported_languages")
    def test_get_supported_langs(self, get_supported_languages):
        from ovos_plugin_manager.solvers import \
            get_reading_comprehension_solver_supported_langs
        get_reading_comprehension_solver_supported_langs()
        get_supported_languages.assert_called_once_with(self.PLUGIN_TYPE)


class TestAutoTranslate(unittest.TestCase):
    def setUp(self):
        self.solver = AbstractSolver(enable_tx=True, default_lang='en')
        self.solver.translate = MagicMock(side_effect=lambda text, source_lang=None, target_lang=None: text[
                                                                                                       ::-1] if source_lang and target_lang else text)

    def test_auto_translate_decorator(self):
        @auto_translate(translate_keys=['text'])
        def test_func(solver, text, lang=None):
            return text[::-1]

        result = test_func(self.solver, 'hello', lang='es')
        self.assertEqual(result, 'olleh')  # 'hello' reversed due to mock translation

    def test_auto_translate_no_translation(self):
        @auto_translate(translate_keys=['text'])
        def test_func(solver, text, lang=None):
            return text

        result = test_func(self.solver, 'hello')
        self.assertEqual(result, 'hello')


class TestAutoDetectLang(unittest.TestCase):
    def setUp(self):
        self.solver = AbstractSolver()
        self.solver.detect_language = MagicMock(return_value='en')

    def test_auto_detect_lang_decorator(self):
        self.solver.detector = Mock()
        self.solver.detector.detect.return_value = "en"

        @auto_detect_lang(text_keys=['text'])
        def test_func(solver, text, lang=None):
            return lang

        result = test_func(self.solver, 'hello world')
        self.assertEqual(result, 'en')

    def test_auto_detect_lang_with_lang(self):
        @auto_detect_lang(text_keys=['text'])
        def test_func(solver, text, lang=None):
            return lang

        result = test_func(self.solver, 'hello', lang='es')
        self.assertEqual(result, 'es')


if __name__ == '__main__':
    unittest.main()
