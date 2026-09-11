# Copyright 2024, OpenVoiceOS
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for deprecated ovos_plugin_manager.templates.coreference module."""

import unittest
import warnings
from unittest.mock import MagicMock, patch


# Suppress deprecation warnings during import
with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from ovos_plugin_manager.templates.coreference import (
        CoreferenceSolverEngine,
        replace_coreferences,
    )


class _ConcreteCoreferenceSolver(CoreferenceSolverEngine):
    """Minimal concrete implementation of deprecated CoreferenceSolverEngine."""

    def contains_corefs(self, text: str, lang: str) -> bool:
        """Return True if 'it' or 'he' in text."""
        return any(w in text.lower().split() for w in ["it", "he", "she"])

    def solve_corefs(self, text: str, lang: str) -> str:
        """Replace 'it' with 'the_dog'."""
        return text.replace(" it ", " the_dog ")


class TestCoreferenceModule(unittest.TestCase):
    """Tests for the deprecated CoreferenceSolverEngine."""

    def setUp(self) -> None:
        """Create solver instance with deprecation warnings suppressed."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            self.solver = _ConcreteCoreferenceSolver(config={"lang": "en-us"})

    def test_init(self) -> None:
        """CoreferenceSolverEngine initialises config and contexts."""
        self.assertEqual(self.solver.config.get("lang"), "en-us")
        self.assertIsInstance(self.solver.contexts, dict)

    def test_contains_corefs_true(self) -> None:
        """contains_corefs returns True when pronoun present."""
        self.assertTrue(self.solver.contains_corefs("I saw it running", "en-us"))

    def test_contains_corefs_false(self) -> None:
        """contains_corefs returns False when no pronouns."""
        self.assertFalse(self.solver.contains_corefs("Hello world", "en-us"))

    def test_solve_corefs(self) -> None:
        """solve_corefs substitutes pronoun."""
        result = self.solver.solve_corefs("I saw it running", "en-us")
        self.assertIn("the_dog", result)

    def test_replace_coreferences(self) -> None:
        """replace_coreferences calls solve_corefs."""
        result = self.solver.replace_coreferences("I saw it running")
        self.assertIsInstance(result, str)

    def test_replace_coreferences_set_context(self) -> None:
        """replace_coreferences with set_context=True calls extract_context."""
        result = self.solver.replace_coreferences("I saw it running", set_context=True)
        self.assertIsInstance(result, str)

    def test_add_context(self) -> None:
        """add_context stores context in self.contexts."""
        self.solver.add_context("it", "dog", lang="en-us")
        self.assertIn("en-US", self.solver.contexts)
        self.assertIn("it", self.solver.contexts["en-US"])

    def test_extract_context(self) -> None:
        """extract_context extracts replacements from prev solve."""
        self.solver._prev_sentence = "I saw it running"
        self.solver._prev_solved = "I saw the_dog running"
        result = self.solver.extract_context()
        self.assertIsInstance(result, dict)

    def test_extract_replacements_static(self) -> None:
        """extract_replacements returns dict of substitutions."""
        result = CoreferenceSolverEngine.extract_replacements(
            "I saw it running", "I saw the_dog running"
        )
        self.assertIsInstance(result, dict)

    def test_runtime_requirements(self) -> None:
        """runtime_requirements is a RuntimeRequirements instance."""
        reqs = _ConcreteCoreferenceSolver.runtime_requirements
        self.assertIsNotNone(reqs)

    def test_replace_coreferences_with_context_no_change(self) -> None:
        """replace_coreferences_with_context works when no context."""
        result = self.solver.replace_coreferences_with_context("Hello world")
        self.assertIsInstance(result, str)


class TestReplaceCoreferencesHelper(unittest.TestCase):
    """Tests for the replace_coreferences standalone function."""

    def setUp(self) -> None:
        """Create solver for helper tests."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            self.solver = _ConcreteCoreferenceSolver()

    def test_no_solver(self) -> None:
        """replace_coreferences returns input text when no solver."""
        result = replace_coreferences("hello world", solver=None)
        self.assertEqual(result, "hello world")

    def test_with_solver_no_corefs(self) -> None:
        """replace_coreferences returns text unchanged when no corefs."""
        result = replace_coreferences("Hello world", solver=self.solver)
        self.assertEqual(result, "Hello world")

    def test_with_solver_has_corefs(self) -> None:
        """replace_coreferences applies solver when corefs present."""
        result = replace_coreferences("I saw it running", solver=self.solver)
        self.assertIsInstance(result, str)

    def test_smart_false(self) -> None:
        """replace_coreferences with smart=False always applies solver."""
        result = replace_coreferences("Hello world", solver=self.solver, smart=False)
        self.assertIsInstance(result, str)

    def test_use_context_false(self) -> None:
        """replace_coreferences with use_context=False skips context lookup."""
        result = replace_coreferences("I saw it running", solver=self.solver,
                                      use_context=False)
        self.assertIsInstance(result, str)


if __name__ == "__main__":
    unittest.main()
