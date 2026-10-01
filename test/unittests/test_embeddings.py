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

"""Unit tests for ovos_plugin_manager.embeddings and ovos_plugin_manager.templates.embeddings."""

import unittest
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import MagicMock, patch

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

from ovos_plugin_manager.templates.embeddings import (
    EmbeddingsDB,
    FaceEmbedder,
    ImageEmbedder,
    TextEmbedder,
    VoiceEmbedder,
)
from ovos_plugin_manager.utils import PluginTypes


# ---------------------------------------------------------------------------
# Minimal concrete implementations
# ---------------------------------------------------------------------------

class _EmbeddingsDBImpl(EmbeddingsDB):
    """In-memory EmbeddingsDB for testing."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Set up in-memory storage."""
        super().__init__(config)
        self._store: Dict[str, Any] = {}
        self._collections: Dict[str, Any] = {}

    def create_collection(self, name: str, metadata: Optional[Dict] = None) -> str:
        """Create and return collection name."""
        self._collections[name] = metadata or {}
        return name

    def get_collection(self, name: str) -> Dict:
        """Retrieve collection by name."""
        if name not in self._collections:
            raise ValueError(f"Collection not found: {name}")
        return self._collections[name]

    def delete_collection(self, name: str) -> None:
        """Delete a collection."""
        self._collections.pop(name, None)

    def list_collections(self) -> List[str]:
        """Return all collection names."""
        return list(self._collections.keys())

    def add_embeddings(
        self,
        key: str,
        embedding: Any,
        metadata: Optional[Dict] = None,
        collection_name: Optional[str] = None,
    ) -> Any:
        """Store embedding under key."""
        self._store[key] = (embedding, metadata)
        return embedding

    def get_embeddings(
        self,
        key: str,
        collection_name: Optional[str] = None,
        return_metadata: bool = False,
    ) -> Any:
        """Retrieve embedding by key."""
        if key not in self._store:
            return None
        emb, meta = self._store[key]
        if return_metadata:
            return emb, meta
        return emb

    def delete_embeddings(self, key: str, collection_name: Optional[str] = None) -> None:
        """Delete embedding by key."""
        self._store.pop(key, None)

    def query(
        self,
        embeddings: Any,
        top_k: int = 5,
        return_metadata: bool = False,
        collection_name: Optional[str] = None,
    ) -> List[Tuple]:
        """Return top_k results (stub)."""
        return []

    def count_embeddings_in_collection(self, collection_name: Optional[str] = None) -> int:
        """Return count of stored embeddings."""
        return len(self._store)


class _TextEmbedderImpl(TextEmbedder):
    """Simple text embedder returning list of char codes."""

    def get_embeddings(self, text: str) -> List[float]:
        """Return character code vector."""
        return [float(ord(c)) for c in text]


class _ImageEmbedderImpl(ImageEmbedder):
    """Simple image embedder returning flattened input."""

    def get_embeddings(self, frame: Any) -> List[float]:
        """Flatten the frame."""
        return [1.0, 2.0, 3.0]


class _FaceEmbedderImpl(FaceEmbedder):
    """Simple face embedder."""

    def get_embeddings(self, frame: Any) -> List[float]:
        """Return a fixed embedding."""
        return [0.5, 0.5, 0.5]


class _VoiceEmbedderImpl(VoiceEmbedder):
    """Simple voice embedder."""

    def get_embeddings(self, audio_data: Any) -> List[float]:
        """Return a fixed embedding."""
        return [0.1, 0.2, 0.3]


# ---------------------------------------------------------------------------
# Tests for EmbeddingsDB
# ---------------------------------------------------------------------------

class TestEmbeddingsDB(unittest.TestCase):
    """Tests for EmbeddingsDB base class methods."""

    def setUp(self) -> None:
        """Create a fresh in-memory DB."""
        self.db = _EmbeddingsDBImpl(config={"test": True})

    def test_config_stored(self) -> None:
        """Config is stored on construction."""
        self.assertEqual(self.db.config, {"test": True})

    def test_create_and_list_collections(self) -> None:
        """create_collection adds to list_collections."""
        self.db.create_collection("col1")
        self.assertIn("col1", self.db.list_collections())

    def test_get_collection_existing(self) -> None:
        """get_collection returns correct collection."""
        self.db.create_collection("col2", metadata={"info": "x"})
        col = self.db.get_collection("col2")
        self.assertEqual(col, {"info": "x"})

    def test_get_collection_missing_raises(self) -> None:
        """get_collection raises ValueError for unknown name."""
        with self.assertRaises(ValueError):
            self.db.get_collection("does_not_exist")

    def test_delete_collection(self) -> None:
        """delete_collection removes the collection."""
        self.db.create_collection("col3")
        self.db.delete_collection("col3")
        self.assertNotIn("col3", self.db.list_collections())

    def test_add_and_get_embeddings(self) -> None:
        """add_embeddings stores and get_embeddings retrieves."""
        self.db.add_embeddings("k1", [1.0, 2.0])
        result = self.db.get_embeddings("k1")
        self.assertEqual(result, [1.0, 2.0])

    def test_get_embeddings_with_metadata(self) -> None:
        """get_embeddings with return_metadata returns tuple."""
        self.db.add_embeddings("k2", [3.0], metadata={"src": "test"})
        emb, meta = self.db.get_embeddings("k2", return_metadata=True)
        self.assertEqual(emb, [3.0])
        self.assertEqual(meta, {"src": "test"})

    def test_get_missing_embedding(self) -> None:
        """get_embeddings returns None for missing key."""
        result = self.db.get_embeddings("missing")
        self.assertIsNone(result)

    def test_add_embeddings_batch(self) -> None:
        """add_embeddings_batch calls add_embeddings for each key."""
        self.db.add_embeddings_batch(["a", "b"], [[1.0], [2.0]])
        self.assertEqual(self.db.get_embeddings("a"), [1.0])
        self.assertEqual(self.db.get_embeddings("b"), [2.0])

    def test_get_embeddings_batch(self) -> None:
        """get_embeddings_batch returns list of results."""
        self.db.add_embeddings("x", [9.0])
        results = self.db.get_embeddings_batch(["x", "missing"])
        self.assertEqual(len(results), 2)
        # first result has key "x"
        self.assertEqual(results[0][0], "x")
        self.assertEqual(results[0][1], [9.0])

    def test_get_embeddings_batch_with_metadata(self) -> None:
        """get_embeddings_batch with return_metadata=True returns 3-tuples."""
        self.db.add_embeddings("m", [1.0], metadata={"q": 1})
        results = self.db.get_embeddings_batch(["m"], return_metadata=True)
        self.assertEqual(len(results[0]), 3)

    def test_delete_embeddings(self) -> None:
        """delete_embeddings removes the entry."""
        self.db.add_embeddings("del", [5.0])
        self.db.delete_embeddings("del")
        self.assertIsNone(self.db.get_embeddings("del"))

    def test_delete_embeddings_batch(self) -> None:
        """delete_embeddings_batch removes multiple entries."""
        self.db.add_embeddings("d1", [1.0])
        self.db.add_embeddings("d2", [2.0])
        self.db.delete_embeddings_batch(["d1", "d2"])
        self.assertIsNone(self.db.get_embeddings("d1"))
        self.assertIsNone(self.db.get_embeddings("d2"))

    def test_count_embeddings(self) -> None:
        """count_embeddings_in_collection returns correct count."""
        self.db.add_embeddings("cnt1", [1.0])
        self.db.add_embeddings("cnt2", [2.0])
        self.assertEqual(self.db.count_embeddings_in_collection(), 2)

    @unittest.skipUnless(HAS_NUMPY, "numpy not installed")
    def test_distance_cosine(self) -> None:
        """distance method computes cosine distance."""
        a = [1.0, 0.0]
        b = [1.0, 0.0]
        d = self.db.distance(a, b, metric="cosine")
        self.assertAlmostEqual(d, 0.0, places=5)

    @unittest.skipUnless(HAS_NUMPY, "numpy not installed")
    def test_distance_euclidean(self) -> None:
        """distance method computes euclidean distance."""
        a = [3.0, 4.0]
        b = [0.0, 0.0]
        d = self.db.distance(a, b, metric="euclidean")
        self.assertAlmostEqual(d, 5.0, places=5)

    @unittest.skipUnless(HAS_NUMPY, "numpy not installed")
    def test_distance_unsupported_metric(self) -> None:
        """distance raises ValueError for unknown metric."""
        with self.assertRaises(ValueError):
            self.db.distance([1.0], [1.0], metric="unsupported_metric")

    @unittest.skipUnless(HAS_NUMPY, "numpy not installed")
    def test_distance_zero_vectors_cosine(self) -> None:
        """distance returns 1.0 for zero vectors with cosine."""
        d = self.db.distance([0.0, 0.0], [1.0, 0.0], metric="cosine")
        self.assertEqual(d, 1.0)

    @unittest.skipUnless(HAS_NUMPY, "numpy not installed")
    def test_distance_manhattan(self) -> None:
        """distance computes manhattan distance correctly."""
        d = self.db.distance([1.0, 2.0], [4.0, 6.0], metric="manhattan")
        self.assertAlmostEqual(d, 7.0, places=5)

    @unittest.skipUnless(HAS_NUMPY, "numpy not installed")
    def test_distance_jaccard(self) -> None:
        """distance computes jaccard distance."""
        d = self.db.distance([1.0, 1.0], [1.0, 0.0], metric="jaccard")
        self.assertIsInstance(d, float)

    @unittest.skipUnless(HAS_NUMPY, "numpy not installed")
    def test_distance_hamming(self) -> None:
        """distance computes hamming distance."""
        d = self.db.distance([1.0, 0.0], [0.0, 1.0], metric="hamming")
        self.assertAlmostEqual(d, 1.0, places=5)


# ---------------------------------------------------------------------------
# Tests for TextEmbedder / ImageEmbedder / FaceEmbedder / VoiceEmbedder
# ---------------------------------------------------------------------------

class TestEmbedderClasses(unittest.TestCase):
    """Tests for concrete embedder template classes."""

    def test_text_embedder(self) -> None:
        """TextEmbedder returns a list from get_embeddings."""
        embedder = _TextEmbedderImpl()
        result = embedder.get_embeddings("hi")
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)

    def test_text_embedder_config(self) -> None:
        """TextEmbedder stores config."""
        embedder = _TextEmbedderImpl(config={"model": "test"})
        self.assertEqual(embedder.config["model"], "test")

    def test_image_embedder(self) -> None:
        """ImageEmbedder returns a list from get_embeddings."""
        embedder = _ImageEmbedderImpl()
        result = embedder.get_embeddings([[[0, 0, 0]]])
        self.assertIsInstance(result, list)

    def test_face_embedder(self) -> None:
        """FaceEmbedder returns a list from get_embeddings."""
        embedder = _FaceEmbedderImpl()
        result = embedder.get_embeddings([[[0, 0, 0]]])
        self.assertIsInstance(result, list)

    def test_voice_embedder(self) -> None:
        """VoiceEmbedder returns a list from get_embeddings."""
        embedder = _VoiceEmbedderImpl()
        result = embedder.get_embeddings([0.0, 1.0])
        self.assertIsInstance(result, list)


# ---------------------------------------------------------------------------
# Tests for embeddings.py (discovery/loading wrappers)
# ---------------------------------------------------------------------------

class TestEmbeddingsModule(unittest.TestCase):
    """Tests for ovos_plugin_manager.embeddings find/load functions."""

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_embeddings_db_plugins(self, mock_find: MagicMock) -> None:
        """find_embeddings_db_plugins calls find_plugins with EMBEDDINGS."""
        from ovos_plugin_manager.embeddings import find_embeddings_db_plugins
        mock_find.return_value = {}
        find_embeddings_db_plugins()
        mock_find.assert_called_once_with(PluginTypes.EMBEDDINGS)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_embeddings_db_plugin(self, mock_load: MagicMock) -> None:
        """load_embeddings_db_plugin calls load_plugin with EMBEDDINGS."""
        from ovos_plugin_manager.embeddings import load_embeddings_db_plugin
        mock_load.return_value = MagicMock()
        load_embeddings_db_plugin("test")
        mock_load.assert_called_once_with("test", PluginTypes.EMBEDDINGS)

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_voice_embeddings_plugins(self, mock_find: MagicMock) -> None:
        """find_voice_embeddings_plugins uses VOICE_EMBEDDINGS."""
        from ovos_plugin_manager.embeddings import find_voice_embeddings_plugins
        mock_find.return_value = {}
        find_voice_embeddings_plugins()
        mock_find.assert_called_once_with(PluginTypes.VOICE_EMBEDDINGS)

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_image_embeddings_plugins(self, mock_find: MagicMock) -> None:
        """find_image_embeddings_plugins uses IMAGE_EMBEDDINGS."""
        from ovos_plugin_manager.embeddings import find_image_embeddings_plugins
        mock_find.return_value = {}
        find_image_embeddings_plugins()
        mock_find.assert_called_once_with(PluginTypes.IMAGE_EMBEDDINGS)

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_face_embeddings_plugins(self, mock_find: MagicMock) -> None:
        """find_face_embeddings_plugins uses FACE_EMBEDDINGS."""
        from ovos_plugin_manager.embeddings import find_face_embeddings_plugins
        mock_find.return_value = {}
        find_face_embeddings_plugins()
        mock_find.assert_called_once_with(PluginTypes.FACE_EMBEDDINGS)

    @patch("ovos_plugin_manager.utils.find_plugins")
    def test_find_text_embeddings_plugins(self, mock_find: MagicMock) -> None:
        """find_text_embeddings_plugins uses TEXT_EMBEDDINGS."""
        from ovos_plugin_manager.embeddings import find_text_embeddings_plugins
        mock_find.return_value = {}
        find_text_embeddings_plugins()
        mock_find.assert_called_once_with(PluginTypes.TEXT_EMBEDDINGS)

    @patch("ovos_plugin_manager.utils.load_plugin")
    def test_load_text_embeddings_plugin(self, mock_load: MagicMock) -> None:
        """load_text_embeddings_plugin calls load_plugin with TEXT_EMBEDDINGS."""
        from ovos_plugin_manager.embeddings import load_text_embeddings_plugin
        mock_load.return_value = MagicMock()
        load_text_embeddings_plugin("text-emb")
        mock_load.assert_called_once_with("text-emb", PluginTypes.TEXT_EMBEDDINGS)


if __name__ == "__main__":
    unittest.main()
