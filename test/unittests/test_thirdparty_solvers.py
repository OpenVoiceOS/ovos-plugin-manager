"""Tests for ovos_plugin_manager.thirdparty.solvers.AbstractSolver."""
import unittest
from unittest.mock import MagicMock, patch, PropertyMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_solver(internal_lang="en", enable_tx=False, config=None):
    """Return a patched AbstractSolver so factory create() calls are mocked."""
    with (
        patch("ovos_plugin_manager.thirdparty.solvers.OVOSLangTranslationFactory.create",
              return_value=MagicMock()),
        patch("ovos_plugin_manager.thirdparty.solvers.OVOSLangDetectionFactory.create",
              return_value=MagicMock()),
    ):
        from ovos_plugin_manager.thirdparty.solvers import AbstractSolver
        return AbstractSolver(config=config, internal_lang=internal_lang,
                              enable_tx=enable_tx)


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------

class TestAbstractSolverInit(unittest.TestCase):

    def test_default_lang_from_internal_lang(self):
        solver = _make_solver(internal_lang="fr")
        self.assertEqual(solver.default_lang, "fr")

    def test_default_lang_from_config(self):
        with (
            patch("ovos_plugin_manager.thirdparty.solvers.OVOSLangTranslationFactory.create",
                  return_value=MagicMock()),
            patch("ovos_plugin_manager.thirdparty.solvers.OVOSLangDetectionFactory.create",
                  return_value=MagicMock()),
        ):
            from ovos_plugin_manager.thirdparty.solvers import AbstractSolver
            solver = AbstractSolver(config={"lang": "de"})
        self.assertEqual(solver.default_lang, "de")

    def test_supported_langs_includes_default(self):
        solver = _make_solver(internal_lang="en")
        self.assertIn("en", solver.supported_langs)

    def test_supported_langs_from_config(self):
        solver = _make_solver(config={"supported_langs": ["en", "de"],
                                      "lang": "en"})
        self.assertIn("de", solver.supported_langs)

    def test_enable_tx_false_means_no_translator(self):
        solver = _make_solver(enable_tx=False)
        self.assertIsNone(solver._translator)
        self.assertIsNone(solver._detector)

    def test_enable_tx_true_creates_translator_and_detector(self):
        with (
            patch("ovos_plugin_manager.thirdparty.solvers.OVOSLangTranslationFactory.create",
                  return_value=MagicMock()) as mock_tx,
            patch("ovos_plugin_manager.thirdparty.solvers.OVOSLangDetectionFactory.create",
                  return_value=MagicMock()) as mock_det,
        ):
            from ovos_plugin_manager.thirdparty.solvers import AbstractSolver
            solver = AbstractSolver(enable_tx=True, internal_lang="en")
        mock_tx.assert_called_once()
        mock_det.assert_called_once()
        self.assertIsNotNone(solver._translator)
        self.assertIsNotNone(solver._detector)

    def test_priority_default(self):
        solver = _make_solver()
        self.assertEqual(solver.priority, 50)

    def test_priority_custom(self):
        solver = _make_solver()
        solver.priority = 75
        self.assertEqual(solver.priority, 75)


# ---------------------------------------------------------------------------
# translator / detector properties
# ---------------------------------------------------------------------------

class TestSolverProperties(unittest.TestCase):

    def test_translator_property_lazy_init(self):
        solver = _make_solver(enable_tx=False)
        self.assertIsNone(solver._translator)
        mock_tx = MagicMock()
        with patch("ovos_plugin_manager.thirdparty.solvers.OVOSLangTranslationFactory.create",
                   return_value=mock_tx):
            tx = solver.translator
        self.assertIs(tx, mock_tx)

    def test_translator_property_setter(self):
        solver = _make_solver()
        custom = MagicMock()
        solver.translator = custom
        self.assertIs(solver._translator, custom)

    def test_detector_property_lazy_init(self):
        solver = _make_solver(enable_tx=False)
        self.assertIsNone(solver._detector)
        mock_det = MagicMock()
        with patch("ovos_plugin_manager.thirdparty.solvers.OVOSLangDetectionFactory.create",
                   return_value=mock_det):
            det = solver.detector
        self.assertIs(det, mock_det)

    def test_detector_property_setter(self):
        solver = _make_solver()
        custom = MagicMock()
        solver.detector = custom
        self.assertIs(solver._detector, custom)

    def test_translator_cached_on_second_access(self):
        solver = _make_solver(enable_tx=False)
        mock_tx = MagicMock()
        with patch("ovos_plugin_manager.thirdparty.solvers.OVOSLangTranslationFactory.create",
                   return_value=mock_tx):
            first = solver.translator
            second = solver.translator
        self.assertIs(first, second)


# ---------------------------------------------------------------------------
# sentence_split
# ---------------------------------------------------------------------------

class TestSentenceSplit(unittest.TestCase):

    def setUp(self):
        self.solver = _make_solver()

    def test_empty_string_returns_empty_list(self):
        result = self.solver.sentence_split("")
        self.assertEqual(result, [])

    def test_none_like_falsy_returns_empty_list(self):
        # sentence_split checks `if not text`
        result = self.solver.sentence_split("")
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    def test_single_sentence(self):
        result = self.solver.sentence_split("Hello world.")
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

    def test_multi_sentence(self):
        result = self.solver.sentence_split("Hello. How are you?")
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

    def test_respects_max_sentences(self):
        text = ". ".join([f"Sentence {i}" for i in range(30)])
        result = self.solver.sentence_split(text, max_sentences=5)
        self.assertLessEqual(len(result), 5)

    def test_newlines_handled(self):
        result = self.solver.sentence_split("Line one.\nLine two.")
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

    def test_exception_returns_split_by_newline(self):
        with patch("ovos_plugin_manager.thirdparty.solvers.sentence_tokenize",
                   side_effect=Exception("fail")):
            result = self.solver.sentence_split("Hello.\nWorld.")
        self.assertIn("Hello.", result)
        self.assertIn("World.", result)


# ---------------------------------------------------------------------------
# detect_language
# ---------------------------------------------------------------------------

class TestDetectLanguage(unittest.TestCase):

    def test_calls_detector_detect(self):
        solver = _make_solver(enable_tx=False)
        mock_det = MagicMock()
        mock_det.detect.return_value = "fr"
        solver.detector = mock_det
        result = solver.detect_language("Bonjour")
        self.assertEqual(result, "fr")
        mock_det.detect.assert_called_once_with("Bonjour")

    def test_result_is_cached(self):
        solver = _make_solver(enable_tx=False)
        mock_det = MagicMock()
        mock_det.detect.return_value = "de"
        solver.detector = mock_det
        solver.detect_language("Hallo")
        solver.detect_language("Hallo")
        self.assertEqual(mock_det.detect.call_count, 1)


# ---------------------------------------------------------------------------
# translate
# ---------------------------------------------------------------------------

class TestTranslate(unittest.TestCase):

    def _solver_with_translator(self, translated_text="translated"):
        solver = _make_solver(internal_lang="en", enable_tx=False)
        mock_tx = MagicMock()
        mock_tx.translate.return_value = translated_text
        solver.translator = mock_tx
        return solver, mock_tx

    def test_translate_calls_translator(self):
        solver, mock_tx = self._solver_with_translator("bonjour")
        result = solver.translate("hello", target_lang="fr", source_lang="en")
        self.assertEqual(result, "bonjour")
        mock_tx.translate.assert_called_once()

    def test_same_lang_skips_translation(self):
        solver, mock_tx = self._solver_with_translator()
        result = solver.translate("hello", target_lang="en", source_lang="en")
        self.assertEqual(result, "hello")
        mock_tx.translate.assert_not_called()

    def test_auto_detect_source_lang(self):
        solver, mock_tx = self._solver_with_translator("hello")
        mock_det = MagicMock()
        mock_det.detect.return_value = "fr"
        solver.detector = mock_det
        solver.translate("bonjour", target_lang="en")
        mock_tx.translate.assert_called_once()

    def test_translate_list(self):
        solver, mock_tx = self._solver_with_translator()
        mock_tx.translate_list.return_value = ["a", "b"]
        result = solver.translate_list(["x", "y"], target_lang="fr")
        self.assertEqual(result, ["a", "b"])
        mock_tx.translate_list.assert_called_once()

    def test_translate_dict(self):
        solver, mock_tx = self._solver_with_translator()
        mock_tx.translate_dict.return_value = {"k": "v_translated"}
        result = solver.translate_dict({"k": "v"}, target_lang="fr")
        self.assertEqual(result, {"k": "v_translated"})
        mock_tx.translate_dict.assert_called_once()


# ---------------------------------------------------------------------------
# shutdown
# ---------------------------------------------------------------------------

class TestShutdown(unittest.TestCase):

    def test_shutdown_is_noop(self):
        solver = _make_solver()
        # Should not raise
        result = solver.shutdown()
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# priority: the class attribute must survive construction
# ---------------------------------------------------------------------------

class TestPriorityResolution(unittest.TestCase):
    """A solver that declares ``priority`` in its class body keeps that value.

    ovos-persona builds every handler as ``plug_class(config=config)`` and then
    orders them on ``.priority``. ``AbstractSolver.__init__`` used to assign its
    own ``priority=50`` keyword unconditionally, so the instance attribute
    shadowed the class attribute: a plugin that declared ``priority = 9999`` to
    sort last still sorted at 50, and a fallback answered before the real
    engine. The whole constructor chain is covered, because every subclass
    passes ``priority`` up positionally and each one had its own default of 50.
    """

    @staticmethod
    def _solvers():
        """One subclass per constructor in the chain, each declaring 9999."""
        from ovos_plugin_manager.thirdparty.solvers import AbstractSolver
        from ovos_plugin_manager.templates.solvers import (
            QuestionSolver, ChatMessageSolver, CorpusSolver, QACorpusSolver)

        class _Direct(AbstractSolver):
            priority = 9999

        class _Question(QuestionSolver):
            priority = 9999

            def get_spoken_answer(self, query, lang=None, units=None):
                return "answer"

        class _Chat(ChatMessageSolver):
            priority = 9999

            def continue_chat(self, messages, lang=None, units=None):
                return "answer"

        class _Corpus(CorpusSolver):
            priority = 9999

            def retrieve_from_corpus(self, query, k=3, lang=None):
                return []

        class _QACorpus(QACorpusSolver):
            priority = 9999

            def retrieve_from_corpus(self, query, k=3, lang=None):
                return []

        return (_Direct, _Question, _Chat, _Corpus, _QACorpus)

    def test_class_priority_is_not_shadowed(self):
        """The declared value reaches the instance, built with config only."""
        for cls in self._solvers():
            with self.subTest(solver=cls.__name__):
                self.assertEqual(cls(config={}).priority, 9999)

    def test_an_explicit_keyword_still_wins(self):
        """Passing priority= is unchanged behaviour and must keep working."""
        for cls in self._solvers():
            with self.subTest(solver=cls.__name__):
                self.assertEqual(cls(config={}, priority=7).priority, 7)

    def test_a_solver_that_declares_nothing_gets_fifty(self):
        """The neutral default is unchanged for every existing plugin."""
        from ovos_plugin_manager.templates.solvers import QuestionSolver

        class _Plain(QuestionSolver):
            def get_spoken_answer(self, query, lang=None, units=None):
                return None

        self.assertEqual(_Plain(config={}).priority, 50)

    def test_zero_is_kept_and_not_read_as_missing(self):
        """0 is a real priority; a falsy check would turn it into 50."""
        from ovos_plugin_manager.templates.solvers import QuestionSolver

        class _First(QuestionSolver):
            priority = 0

            def get_spoken_answer(self, query, lang=None, units=None):
                return None

        self.assertEqual(_First(config={}).priority, 0)
        self.assertEqual(_First(config={}, priority=0).priority, 0)

    def test_the_chain_sorts_by_declared_priority(self):
        """The expression ovos_persona uses to order .modules."""
        from ovos_plugin_manager.templates.solvers import QuestionSolver

        class _Fallback(QuestionSolver):
            priority = 9999

            def get_spoken_answer(self, query, lang=None, units=None):
                return "fallback"

        class _Real(QuestionSolver):
            priority = 50

            def get_spoken_answer(self, query, lang=None, units=None):
                return "real"

        loaded = {"failure": _Fallback(config={}), "openai": _Real(config={})}
        ordered = sorted(loaded.values(), key=lambda k: k.priority)
        self.assertEqual([type(m).__name__ for m in ordered],
                         ["_Real", "_Fallback"])
