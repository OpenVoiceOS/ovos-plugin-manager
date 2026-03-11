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

"""Unit tests for ovos_plugin_manager.templates.embeddings."""

import unittest
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import MagicMock

import numpy as np

from ovos_plugin_manager.templates.embeddings import (
    EmbeddingsDB,
    FaceEmbedder,
    ImageEmbedder,
    TextEmbedder,
    VoiceEmbedder,
)


# ---------------------------------------------------------------------------
# Concrete helpers
# ---------------------------------------------------------------------------

class _ConcreteEmbeddingsDB(EmbeddingsDB):
    """Minimal concrete EmbeddingsDB for testing."""

    def __init__(self, config: Dict[str, Any] = None) -> None:
        """Initialize with an in-memory store."""
        super().__init__(config)
        self._store: Dict[str, Any] = {}
        self._collections: Dict[str, Any] = {}

    def create_collection(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> Any:
        """Create a named collection."""
        self._collections[name] = metadata or {}
        return self._collections[name]

    def get_collection(self, name: str) -> Any:
        """Return a collection by name."""
        return self._collections[name]

    def delete_collection(self, name: str) -> None:
        """Delete a collection by name."""
        del self._collections[name]

    def list_collections(self) -> List[Any]:
        """List all collection names."""
        return list(self._collections.keys())

    def add_embeddings(self, key: str, embedding: Any,
                       metadata: Optional[Dict[str, Any]] = None,
                       collection_name: Optional[str] = None) -> Any:
        """Store an embedding."""
        self._store[key] = (embedding, metadata)
        return embedding

    def get_embeddings(self, key: str, collection_name: Optional[str] = None,
                       return_metadata: bool = False) -> Any:
        """Retrieve an embedding."""
        if key not in self._store:
            return None
        embedding, metadata = self._store[key]
        if return_metadata:
            return embedding, metadata
        return embedding

    def delete_embeddings(self, key: str, collection_name: Optional[str] = None) -> None:
        """Delete an embedding."""
        self._store.pop(key, None)

    def query(self, embeddings: Any, top_k: int = 5,
              return_metadata: bool = False, collection_name: Optional[str] = None) -> List[Tuple]:
        """Return empty query results."""
        return []

    def count_embeddings_in_collection(self, collection_name: Optional[str] = None) -> int:
        """Return count of stored embeddings."""
        return len(self._store)


class _ConcreteTextEmbedder(TextEmbedder):
    """Minimal TextEmbedder."""

    def get_embeddings(self, text: str) -> List[float]:
        """Return a fixed embedding."""
        return [0.1, 0.2, 0.3]


class _ConcreteImageEmbedder(ImageEmbedder):
    """Minimal ImageEmbedder."""

    def get_embeddings(self, frame: Any) -> List[float]:
        """Return a fixed embedding."""
        return [0.4, 0.5, 0.6]


class _ConcreteFaceEmbedder(FaceEmbedder):
    """Minimal FaceEmbedder."""

    def get_embeddings(self, frame: Any) -> List[float]:
        """Return a fixed embedding."""
        return [0.7, 0.8, 0.9]


class _ConcreteVoiceEmbedder(VoiceEmbedder):
    """Minimal VoiceEmbedder."""

    def get_embeddings(self, audio_data: Any) -> List[float]:
        """Return a fixed embedding."""
        return [0.1, 0.0, 0.1]


# ---------------------------------------------------------------------------
# Tests for EmbeddingsDB
# ---------------------------------------------------------------------------

class TestEmbeddingsDBInit(unittest.TestCase):
    """Tests for EmbeddingsDB initialisation."""

    def test_default_config(self) -> None:
        """EmbeddingsDB defaults config to empty dict."""
        db = _ConcreteEmbeddingsDB()
        self.assertEqual(db.config, {})

    def test_custom_config(self) -> None:
        """EmbeddingsDB stores provided config."""
        db = _ConcreteEmbeddingsDB(config={"dim": 128})
        self.assertEqual(db.config["dim"], 128)


class TestEmbeddingsDBCollections(unittest.TestCase):
    """Tests for collection management methods."""

    def setUp(self) -> None:
        """Create a fresh DB."""
        self.db: _ConcreteEmbeddingsDB = _ConcreteEmbeddingsDB()

    def test_create_and_list_collections(self) -> None:
        """create_collection / list_collections round-trip."""
        self.db.create_collection("col1")
        self.assertIn("col1", self.db.list_collections())

    def test_get_collection(self) -> None:
        """get_collection returns the created collection."""
        self.db.create_collection("col2", metadata={"info": "test"})
        col = self.db.get_collection("col2")
        self.assertEqual(col["info"], "test")

    def test_delete_collection(self) -> None:
        """delete_collection removes the collection."""
        self.db.create_collection("col3")
        self.db.delete_collection("col3")
        self.assertNotIn("col3", self.db.list_collections())


class TestEmbeddingsDBEmbeddings(unittest.TestCase):
    """Tests for embedding storage and retrieval methods."""

    def setUp(self) -> None:
        """Create a fresh DB."""
        self.db: _ConcreteEmbeddingsDB = _ConcreteEmbeddingsDB()
        self.vec: np.ndarray = np.array([1.0, 0.0, 0.0])

    def test_add_and_get_embeddings(self) -> None:
        """add_embeddings / get_embeddings round-trip."""
        self.db.add_embeddings("k1", self.vec)
        result = self.db.get_embeddings("k1")
        self.assertIsNotNone(result)

    def test_get_embeddings_with_metadata(self) -> None:
        """get_embeddings with return_metadata=True returns tuple."""
        self.db.add_embeddings("k2", self.vec, metadata={"tag": "test"})
        result = self.db.get_embeddings("k2", return_metadata=True)
        self.assertIsInstance(result, tuple)
        embedding, meta = result
        self.assertEqual(meta["tag"], "test")

    def test_get_embeddings_missing_key(self) -> None:
        """get_embeddings returns None for missing key."""
        result = self.db.get_embeddings("missing_key")
        self.assertIsNone(result)

    def test_delete_embeddings(self) -> None:
        """delete_embeddings removes the entry."""
        self.db.add_embeddings("k3", self.vec)
        self.db.delete_embeddings("k3")
        self.assertIsNone(self.db.get_embeddings("k3"))

    def test_count_embeddings(self) -> None:
        """count_embeddings_in_collection returns correct count."""
        self.db.add_embeddings("k4", self.vec)
        self.db.add_embeddings("k5", self.vec)
        self.assertGreaterEqual(self.db.count_embeddings_in_collection(), 2)

    def test_add_embeddings_batch(self) -> None:
        """add_embeddings_batch stores multiple embeddings."""
        keys = ["b1", "b2", "b3"]
        vecs = [self.vec, self.vec * 2, self.vec * 3]
        self.db.add_embeddings_batch(keys, vecs)
        for k in keys:
            self.assertIsNotNone(self.db.get_embeddings(k))

    def test_add_embeddings_batch_with_metadata(self) -> None:
        """add_embeddings_batch handles metadata list."""
        keys = ["bm1", "bm2"]
        vecs = [self.vec, self.vec]
        metas = [{"a": 1}, {"b": 2}]
        self.db.add_embeddings_batch(keys, vecs, metadata=metas)
        emb, meta = self.db.get_embeddings("bm1", return_metadata=True)
        self.assertEqual(meta["a"], 1)

    def test_get_embeddings_batch(self) -> None:
        """get_embeddings_batch returns list of tuples."""
        self.db.add_embeddings("g1", self.vec)
        self.db.add_embeddings("g2", self.vec * 2)
        results = self.db.get_embeddings_batch(["g1", "g2"])
        self.assertEqual(len(results), 2)
        for key, emb in results:
            self.assertIsNotNone(emb)

    def test_get_embeddings_batch_with_metadata(self) -> None:
        """get_embeddings_batch with return_metadata=True returns 3-tuples."""
        self.db.add_embeddings("gm1", self.vec, metadata={"x": 1})
        results = self.db.get_embeddings_batch(["gm1"], return_metadata=True)
        self.assertEqual(len(results[0]), 3)

    def test_get_embeddings_batch_missing(self) -> None:
        """get_embeddings_batch handles missing keys gracefully."""
        results = self.db.get_embeddings_batch(["no_such_key"])
        self.assertEqual(len(results), 1)
        key, emb = results[0]
        self.assertIsNone(emb)

    def test_delete_embeddings_batch(self) -> None:
        """delete_embeddings_batch removes multiple entries."""
        self.db.add_embeddings("d1", self.vec)
        self.db.add_embeddings("d2", self.vec)
        self.db.delete_embeddings_batch(["d1", "d2"])
        self.assertIsNone(self.db.get_embeddings("d1"))
        self.assertIsNone(self.db.get_embeddings("d2"))

    def test_query_returns_list(self) -> None:
        """query returns a list."""
        result = self.db.query(self.vec)
        self.assertIsInstance(result, list)


# ---------------------------------------------------------------------------
# Tests for EmbeddingsDB.distance()
# ---------------------------------------------------------------------------

class TestEmbeddingsDBDistance(unittest.TestCase):
    """Tests for EmbeddingsDB.distance metric computations."""

    def setUp(self) -> None:
        """Create a DB and reference vectors."""
        self.db: _ConcreteEmbeddingsDB = _ConcreteEmbeddingsDB()
        self.a: np.ndarray = np.array([1.0, 0.0, 0.0])
        self.b: np.ndarray = np.array([0.0, 1.0, 0.0])
        # Probability-like vectors for divergence metrics
        self.pa: np.ndarray = np.array([0.5, 0.3, 0.2])
        self.pb: np.ndarray = np.array([0.2, 0.4, 0.4])

    def _dist(self, metric: str, **kwargs) -> float:
        """Compute distance helper."""
        return self.db.distance(self.a, self.b, metric=metric, **kwargs)

    def test_cosine(self) -> None:
        """cosine metric returns float in [0, 2]."""
        d = self._dist("cosine")
        self.assertIsInstance(d, float)
        self.assertGreaterEqual(d, 0.0)

    def test_cosine_zero_vector(self) -> None:
        """cosine with zero vector returns 1.0."""
        d = self.db.distance(np.array([0.0, 0.0]), np.array([1.0, 0.0]), metric="cosine")
        self.assertEqual(d, 1.0)

    def test_euclidean(self) -> None:
        """euclidean metric returns non-negative float."""
        d = self._dist("euclidean")
        self.assertGreaterEqual(d, 0.0)

    def test_manhattan(self) -> None:
        """manhattan metric returns non-negative float."""
        d = self._dist("manhattan")
        self.assertGreaterEqual(d, 0.0)

    def test_chebyshev(self) -> None:
        """chebyshev metric returns non-negative float."""
        d = self._dist("chebyshev")
        self.assertGreaterEqual(d, 0.0)

    def test_minkowski(self) -> None:
        """minkowski metric returns non-negative float."""
        d = self._dist("minkowski")
        self.assertGreaterEqual(d, 0.0)

    def test_weighted_minkowski(self) -> None:
        """weighted_minkowski metric returns non-negative float with weights."""
        w = np.array([1.0, 1.0, 1.0])
        d = self.db.distance(self.a, self.b, metric="weighted_minkowski", euclidean_weights=w)
        self.assertGreaterEqual(d, 0.0)

    def test_weighted_minkowski_no_weights_raises(self) -> None:
        """weighted_minkowski without weights raises ValueError."""
        with self.assertRaises(ValueError):
            self._dist("weighted_minkowski")

    def test_hamming(self) -> None:
        """hamming metric returns float in [0, 1]."""
        d = self._dist("hamming")
        self.assertGreaterEqual(d, 0.0)

    def test_jaccard(self) -> None:
        """jaccard metric returns non-negative float."""
        a = np.array([1.0, 0.0, 1.0])
        b = np.array([1.0, 1.0, 0.0])
        d = self.db.distance(a, b, metric="jaccard")
        self.assertGreaterEqual(d, 0.0)

    def test_canberra(self) -> None:
        """canberra metric returns non-negative float."""
        d = self._dist("canberra")
        self.assertGreaterEqual(d, 0.0)

    def test_braycurtis(self) -> None:
        """braycurtis metric returns non-negative float."""
        d = self._dist("braycurtis")
        self.assertGreaterEqual(d, 0.0)

    def test_pearson_correlation(self) -> None:
        """pearson_correlation metric returns float."""
        d = self.db.distance(self.pa, self.pb, metric="pearson_correlation")
        self.assertIsInstance(d, float)

    def test_cosine_squared(self) -> None:
        """cosine_squared metric returns float in [0, 1]."""
        d = self._dist("cosine_squared")
        self.assertGreaterEqual(d, 0.0)

    def test_cosine_squared_zero_vector(self) -> None:
        """cosine_squared with zero vector returns 1.0."""
        d = self.db.distance(np.array([0.0, 0.0]), np.array([1.0, 0.0]), metric="cosine_squared")
        self.assertEqual(d, 1.0)

    def test_kl_divergence(self) -> None:
        """kl_divergence metric returns float."""
        d = self.db.distance(self.pa, self.pb, metric="kl_divergence")
        self.assertIsInstance(d, float)

    def test_bhattacharyya(self) -> None:
        """bhattacharyya metric returns non-negative float."""
        d = self.db.distance(self.pa, self.pb, metric="bhattacharyya")
        self.assertGreaterEqual(d, 0.0)

    def test_hellinger(self) -> None:
        """hellinger metric returns non-negative float."""
        d = self.db.distance(self.pa, self.pb, metric="hellinger")
        self.assertGreaterEqual(d, 0.0)

    def test_ruzicka(self) -> None:
        """ruzicka metric returns float in [0, 1]."""
        a = np.array([1.0, 2.0, 3.0])
        b = np.array([1.0, 2.0, 3.0])
        d = self.db.distance(a, b, metric="ruzicka")
        self.assertAlmostEqual(d, 0.0)

    def test_kulczynski(self) -> None:
        """kulczynski metric returns non-negative float."""
        d = self.db.distance(self.pa, self.pb, metric="kulczynski")
        self.assertGreaterEqual(d, 0.0)

    def test_sorensen(self) -> None:
        """sorensen metric returns float."""
        d = self.db.distance(self.pa, self.pb, metric="sorensen")
        self.assertIsInstance(d, float)

    def test_chi_squared(self) -> None:
        """chi_squared metric returns non-negative float."""
        d = self.db.distance(self.pa, self.pb, metric="chi_squared")
        self.assertGreaterEqual(d, 0.0)

    def test_jensen_shannon(self) -> None:
        """jensen_shannon metric returns non-negative float."""
        d = self.db.distance(self.pa, self.pb, metric="jensen_shannon")
        self.assertGreaterEqual(d, 0.0)

    def test_squared_euclidean(self) -> None:
        """squared_euclidean metric returns non-negative float."""
        d = self._dist("squared_euclidean")
        self.assertGreaterEqual(d, 0.0)

    def test_weighted_euclidean(self) -> None:
        """weighted_euclidean metric returns non-negative float."""
        w = np.array([1.0, 1.0, 1.0])
        d = self.db.distance(self.a, self.b, metric="weighted_euclidean", euclidean_weights=w)
        self.assertGreaterEqual(d, 0.0)

    def test_weighted_euclidean_no_weights_raises(self) -> None:
        """weighted_euclidean without weights raises ValueError."""
        with self.assertRaises(ValueError):
            self._dist("weighted_euclidean")

    def test_log_cosh(self) -> None:
        """log_cosh metric returns float."""
        d = self._dist("log_cosh")
        self.assertIsInstance(d, float)

    def test_tanimoto(self) -> None:
        """tanimoto metric returns float in [0, 1]."""
        d = self.db.distance(self.pa, self.pb, metric="tanimoto")
        self.assertGreaterEqual(d, 0.0)

    def test_rao(self) -> None:
        """rao metric returns non-negative float."""
        d = self.db.distance(self.pa, self.pb, metric="rao")
        self.assertGreaterEqual(d, 0.0)

    def test_gower(self) -> None:
        """gower metric returns non-negative float."""
        d = self._dist("gower")
        self.assertGreaterEqual(d, 0.0)

    def test_gower_identical(self) -> None:
        """gower returns 0 for identical vectors."""
        d = self.db.distance(self.a, self.a, metric="gower")
        self.assertEqual(d, 0.0)

    def test_tversky(self) -> None:
        """tversky metric returns float in [0, 1]."""
        d = self.db.distance(self.pa, self.pb, metric="tversky")
        self.assertGreaterEqual(d, 0.0)

    def test_alpha_divergence_alpha1(self) -> None:
        """alpha_divergence with alpha=1 behaves like KL divergence."""
        d = self.db.distance(self.pa, self.pb, metric="alpha_divergence", alpha=1)
        self.assertIsInstance(d, float)

    def test_alpha_divergence_alpha0(self) -> None:
        """alpha_divergence with alpha=0 behaves like reverse KL divergence."""
        d = self.db.distance(self.pa, self.pb, metric="alpha_divergence", alpha=0)
        self.assertIsInstance(d, float)

    def test_alpha_divergence_general(self) -> None:
        """alpha_divergence with other alpha returns float."""
        d = self.db.distance(self.pa, self.pb, metric="alpha_divergence", alpha=0.5)
        self.assertIsInstance(d, float)

    def test_renyi_divergence_alpha1(self) -> None:
        """renyi_divergence with alpha=1 returns float."""
        d = self.db.distance(self.pa, self.pb, metric="renyi_divergence", alpha=1)
        self.assertIsInstance(d, float)

    def test_renyi_divergence_general(self) -> None:
        """renyi_divergence with alpha!=1 returns float."""
        d = self.db.distance(self.pa, self.pb, metric="renyi_divergence", alpha=2)
        self.assertIsInstance(d, float)

    def test_total_variation(self) -> None:
        """total_variation metric returns float in [0, 1]."""
        d = self.db.distance(self.pa, self.pb, metric="total_variation")
        self.assertGreaterEqual(d, 0.0)
        self.assertLessEqual(d, 1.0)

    def test_unsupported_metric_raises(self) -> None:
        """Unsupported metric raises ValueError."""
        with self.assertRaises(ValueError):
            self._dist("not_a_real_metric")

    def test_mahalanobis_with_cov(self) -> None:
        """mahalanobis with explicit covariance matrix returns non-negative float."""
        cov = np.eye(3)
        d = self.db.distance(self.a, self.b, metric="mahalanobis", covariance_matrix=cov)
        self.assertGreaterEqual(d, 0.0)

    def test_jaccard_zero_union(self) -> None:
        """jaccard with zero-valued union returns 0.0."""
        z = np.array([0.0, 0.0])
        d = self.db.distance(z, z, metric="jaccard")
        self.assertEqual(d, 0.0)

    def test_braycurtis_zero_denominator(self) -> None:
        """braycurtis with zero denominator returns 0.0."""
        z = np.array([0.0, 0.0])
        d = self.db.distance(z, z, metric="braycurtis")
        self.assertEqual(d, 0.0)


# ---------------------------------------------------------------------------
# Tests for TextEmbedder, ImageEmbedder, FaceEmbedder, VoiceEmbedder
# ---------------------------------------------------------------------------

class TestTextEmbedder(unittest.TestCase):
    """Tests for TextEmbedder base class."""

    def test_init_default_config(self) -> None:
        """TextEmbedder defaults config to empty dict."""
        emb = _ConcreteTextEmbedder()
        self.assertEqual(emb.config, {})

    def test_init_custom_config(self) -> None:
        """TextEmbedder stores provided config."""
        emb = _ConcreteTextEmbedder(config={"model": "bert"})
        self.assertEqual(emb.config["model"], "bert")

    def test_get_embeddings(self) -> None:
        """get_embeddings returns a list."""
        emb = _ConcreteTextEmbedder()
        result = emb.get_embeddings("hello world")
        self.assertIsInstance(result, list)


class TestImageEmbedder(unittest.TestCase):
    """Tests for ImageEmbedder base class."""

    def test_init_default_config(self) -> None:
        """ImageEmbedder defaults config to empty dict."""
        emb = _ConcreteImageEmbedder()
        self.assertEqual(emb.config, {})

    def test_get_embeddings(self) -> None:
        """get_embeddings returns a list."""
        emb = _ConcreteImageEmbedder()
        frame = np.zeros((64, 64, 3))
        result = emb.get_embeddings(frame)
        self.assertIsInstance(result, list)


class TestFaceEmbedder(unittest.TestCase):
    """Tests for FaceEmbedder base class."""

    def test_init_default_config(self) -> None:
        """FaceEmbedder defaults config to empty dict."""
        emb = _ConcreteFaceEmbedder()
        self.assertEqual(emb.config, {})

    def test_get_embeddings(self) -> None:
        """get_embeddings returns a list."""
        emb = _ConcreteFaceEmbedder()
        frame = np.zeros((64, 64, 3))
        result = emb.get_embeddings(frame)
        self.assertIsInstance(result, list)


class TestVoiceEmbedder(unittest.TestCase):
    """Tests for VoiceEmbedder base class."""

    def test_init_default_config(self) -> None:
        """VoiceEmbedder defaults config to empty dict."""
        emb = _ConcreteVoiceEmbedder()
        self.assertEqual(emb.config, {})

    def test_get_embeddings(self) -> None:
        """get_embeddings returns a list."""
        emb = _ConcreteVoiceEmbedder()
        audio = np.zeros(16000)
        result = emb.get_embeddings(audio)
        self.assertIsInstance(result, list)


if __name__ == "__main__":
    unittest.main()
