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

"""Unit tests for intent_transformers, triples, and gui_adapter modules."""

import unittest
from typing import Iterable, List, Tuple
from unittest.mock import MagicMock, patch

from ovos_plugin_manager.templates.triples import TriplesExtractor
from ovos_plugin_manager.utils import PluginTypes


# ---------------------------------------------------------------------------
# Concrete implementations for abstract classes
# ---------------------------------------------------------------------------

class _TriplesExtractorImpl(TriplesExtractor):
    """Simple concrete implementation for testing TriplesExtractor."""

    def extract_triples(self, documents: List[str]) -> Iterable[Tuple[str, str, str]]:
        """Return stub triples."""
        for doc in documents:
            words = doc.split()
            if len(words) >= 3:
                yield (words[0], words[1], words[2])


# ---------------------------------------------------------------------------
# Tests for TriplesExtractor template
# ---------------------------------------------------------------------------

class TestTriplesExtractor(unittest.TestCase):
    """Tests for TriplesExtractor base class."""

    def test_init_default_config(self) -> None:
        """TriplesExtractor sets default first_person_token from config."""
        extractor = _TriplesExtractorImpl()
        self.assertEqual(extractor.first_person_token, "USER")

    def test_init_custom_config(self) -> None:
        """TriplesExtractor reads first_person_token from config."""
        extractor = _TriplesExtractorImpl(config={"first_person_token": "ME"})
        self.assertEqual(extractor.first_person_token, "ME")

    def test_extract_triples(self) -> None:
        """extract_triples returns triples from documents."""
        extractor = _TriplesExtractorImpl()
        triples = list(extractor.extract_triples(["Alice loves Bob"]))
        self.assertEqual(len(triples), 1)
        self.assertEqual(triples[0], ("Alice", "loves", "Bob"))

    def test_extract_triples_short_doc(self) -> None:
        """extract_triples handles documents with fewer than 3 words."""
        extractor = _TriplesExtractorImpl()
        triples = list(extractor.extract_triples(["hello"]))
        self.assertEqual(triples, [])


# ---------------------------------------------------------------------------
# Tests for triples.py (discovery wrappers)
# ---------------------------------------------------------------------------

class TestTriplesModule(unittest.TestCase):
    """Tests for ovos_plugin_manager.triples module."""

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_triples_plugins(self, mock_find: MagicMock) -> None:
        """find_triples_plugins calls find_plugins with COREFERENCE_SOLVER."""
        from ovos_plugin_manager.triples import find_triples_plugins
        mock_find.return_value = {}
        find_triples_plugins()
        mock_find.assert_called_once_with(PluginTypes.COREFERENCE_SOLVER)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_triples_plugin(self, mock_load: MagicMock) -> None:
        """load_triples_plugin calls load_plugin with COREFERENCE_SOLVER."""
        from ovos_plugin_manager.triples import load_triples_plugin
        mock_load.return_value = MagicMock()
        load_triples_plugin("my-triples")
        mock_load.assert_called_once_with("my-triples", PluginTypes.COREFERENCE_SOLVER)

    @patch("ovos_plugin_manager.utils.config.load_configs_for_plugin_type")
    def test_get_triples_configs(self, mock_load: MagicMock) -> None:
        """get_triples_configs calls load_configs_for_plugin_type."""
        from ovos_plugin_manager.triples import get_triples_configs
        mock_load.return_value = {}
        result = get_triples_configs()
        self.assertEqual(result, {})

    @patch("ovos_plugin_manager.utils.config.load_plugin_configs")
    def test_get_triples_module_configs(self, mock_load: MagicMock) -> None:
        """get_triples_module_configs calls load_plugin_configs."""
        from ovos_plugin_manager.triples import get_triples_module_configs
        mock_load.return_value = {}
        result = get_triples_module_configs("my-triples")
        self.assertEqual(result, {})


# ---------------------------------------------------------------------------
# Tests for intent_transformers.py
# ---------------------------------------------------------------------------

class TestIntentTransformersModule(unittest.TestCase):
    """Tests for ovos_plugin_manager.intent_transformers module."""

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_intent_transformer_plugins(self, mock_find: MagicMock) -> None:
        """find_intent_transformer_plugins calls find_plugins with INTENT_TRANSFORMER."""
        from ovos_plugin_manager.intent_transformers import find_intent_transformer_plugins
        mock_find.return_value = {}
        find_intent_transformer_plugins()
        mock_find.assert_called_once_with(PluginTypes.INTENT_TRANSFORMER)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_intent_transformer_plugin(self, mock_load: MagicMock) -> None:
        """load_intent_transformer_plugin calls load_plugin with INTENT_TRANSFORMER."""
        from ovos_plugin_manager.intent_transformers import load_intent_transformer_plugin
        mock_load.return_value = MagicMock()
        load_intent_transformer_plugin("intent-plug")
        mock_load.assert_called_once_with("intent-plug", PluginTypes.INTENT_TRANSFORMER)


# ---------------------------------------------------------------------------
# Tests for gui_adapter.py
# ---------------------------------------------------------------------------

class TestGUIAdapterModule(unittest.TestCase):
    """Tests for ovos_plugin_manager.gui_adapter module."""

    @patch("ovos_plugin_manager.gui_adapter.find_plugins")
    def test_find_gui_adapter_plugins(self, mock_find: MagicMock) -> None:
        """find_gui_adapter_plugins calls find_plugins with GUI_ADAPTER."""
        from ovos_plugin_manager.gui_adapter import find_gui_adapter_plugins
        mock_find.return_value = {}
        result = find_gui_adapter_plugins()
        mock_find.assert_called_once_with(PluginTypes.GUI_ADAPTER)
        self.assertEqual(result, {})

    @patch("ovos_plugin_manager.gui_adapter.load_plugin")
    def test_load_gui_adapter_plugin(self, mock_load: MagicMock) -> None:
        """load_gui_adapter_plugin calls load_plugin with GUI_ADAPTER."""
        from ovos_plugin_manager.gui_adapter import load_gui_adapter_plugin
        mock_cls = MagicMock()
        mock_load.return_value = mock_cls
        result = load_gui_adapter_plugin("gui-plug")
        mock_load.assert_called_once_with("gui-plug", PluginTypes.GUI_ADAPTER)
        self.assertEqual(result, mock_cls)

    @patch("ovos_plugin_manager.gui_adapter.load_gui_adapter_plugin")
    def test_factory_create_success(self, mock_load: MagicMock) -> None:
        """OVOSGUIAdapterFactory.create returns plugin instance on success."""
        from ovos_plugin_manager.gui_adapter import OVOSGUIAdapterFactory
        mock_cls = MagicMock(return_value=MagicMock())
        mock_load.return_value = mock_cls
        result = OVOSGUIAdapterFactory.create("gui-plug", config={}, bus=None)
        self.assertIsNotNone(result)
        mock_cls.assert_called_once_with({}, bus=None)

    @patch("ovos_plugin_manager.gui_adapter.load_gui_adapter_plugin")
    def test_factory_create_not_found(self, mock_load: MagicMock) -> None:
        """OVOSGUIAdapterFactory.create returns None when plugin not found."""
        from ovos_plugin_manager.gui_adapter import OVOSGUIAdapterFactory
        mock_load.return_value = None
        result = OVOSGUIAdapterFactory.create("missing-plug")
        self.assertIsNone(result)

    @patch("ovos_plugin_manager.gui_adapter.load_gui_adapter_plugin")
    def test_factory_create_exception(self, mock_load: MagicMock) -> None:
        """OVOSGUIAdapterFactory.create returns None when instantiation fails."""
        from ovos_plugin_manager.gui_adapter import OVOSGUIAdapterFactory
        mock_cls = MagicMock(side_effect=RuntimeError("fail"))
        mock_load.return_value = mock_cls
        result = OVOSGUIAdapterFactory.create("bad-plug")
        self.assertIsNone(result)

    @patch("ovos_plugin_manager.gui_adapter.find_gui_adapter_plugins")
    def test_factory_create_all_success(self, mock_find: MagicMock) -> None:
        """OVOSGUIAdapterFactory.create_all instantiates all found plugins."""
        from ovos_plugin_manager.gui_adapter import OVOSGUIAdapterFactory
        mock_instance = MagicMock()
        mock_cls = MagicMock(return_value=mock_instance)
        mock_find.return_value = {"plug1": mock_cls}
        result = OVOSGUIAdapterFactory.create_all()
        self.assertEqual(len(result), 1)
        self.assertIs(result[0], mock_instance)

    @patch("ovos_plugin_manager.gui_adapter.find_gui_adapter_plugins")
    def test_factory_create_all_empty(self, mock_find: MagicMock) -> None:
        """OVOSGUIAdapterFactory.create_all returns empty list when no plugins."""
        from ovos_plugin_manager.gui_adapter import OVOSGUIAdapterFactory
        mock_find.return_value = {}
        result = OVOSGUIAdapterFactory.create_all()
        self.assertEqual(result, [])

    @patch("ovos_plugin_manager.gui_adapter.find_gui_adapter_plugins")
    def test_factory_create_all_exception_skipped(self, mock_find: MagicMock) -> None:
        """OVOSGUIAdapterFactory.create_all skips failing plugins."""
        from ovos_plugin_manager.gui_adapter import OVOSGUIAdapterFactory
        bad_cls = MagicMock(side_effect=RuntimeError("fail"))
        mock_find.return_value = {"bad": bad_cls}
        result = OVOSGUIAdapterFactory.create_all()
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
