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

"""Tests for EmbeddingsDB.distance() covering all metric branches."""

import unittest
from typing import Any, Dict, List, Optional, Tuple

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

from ovos_plugin_manager.templates.embeddings import EmbeddingsDB


class _MinimalDB(EmbeddingsDB):
    """Minimal EmbeddingsDB subclass to exercise the distance() method."""

    def create_collection(self, name: str, metadata: Optional[Dict] = None) -> Any:
        """Stub."""
        return name

    def get_collection(self, name: str) -> Any:
        """Stub."""
        return {}

    def delete_collection(self, name: str) -> None:
        """Stub."""

    def list_collections(self) -> List[Any]:
        """Stub."""
        return []

    def add_embeddings(self, key: str, embedding: Any, metadata: Optional[Dict] = None,
                       collection_name: Optional[str] = None) -> Any:
        """Stub."""
        return embedding

    def get_embeddings(self, key: str, collection_name: Optional[str] = None,
                       return_metadata: bool = False) -> Any:
        """Stub."""
        return None

    def delete_embeddings(self, key: str, collection_name: Optional[str] = None) -> None:
        """Stub."""

    def query(self, embeddings: Any, top_k: int = 5, return_metadata: bool = False,
              collection_name: Optional[str] = None) -> List[Tuple]:
        """Stub."""
        return []

    def count_embeddings_in_collection(self, collection_name: Optional[str] = None) -> int:
        """Stub."""
        return 0


@unittest.skipUnless(HAS_NUMPY, "numpy not installed")
class TestEmbeddingsDistanceMetrics(unittest.TestCase):
    """Tests for each distance metric branch of EmbeddingsDB.distance()."""

    def setUp(self) -> None:
        """Create DB and simple test vectors."""
        self.db = _MinimalDB()
        # Positive probability-like vectors for distribution metrics
        self.a = [0.4, 0.3, 0.2, 0.1]
        self.b = [0.1, 0.2, 0.3, 0.4]
        # General vectors
        self.x = [1.0, 2.0, 3.0, 4.0]
        self.y = [4.0, 3.0, 2.0, 1.0]

    def _dist(self, metric: str, **kwargs) -> float:
        """Helper to call distance() with consistent inputs."""
        return self.db.distance(self.a, self.b, metric=metric, **kwargs)

    def test_chebyshev(self) -> None:
        """chebyshev metric returns float."""
        d = self.db.distance([1.0, 2.0], [4.0, 2.0], metric="chebyshev")
        self.assertAlmostEqual(d, 3.0, places=5)

    def test_minkowski(self) -> None:
        """minkowski metric returns float."""
        d = self._dist("minkowski", p=3)
        self.assertIsInstance(d, float)

    def test_weighted_minkowski(self) -> None:
        """weighted_minkowski metric with weights."""
        weights = [1.0, 1.0, 1.0, 1.0]
        d = self.db.distance(self.a, self.b, metric="weighted_minkowski",
                             p=2, euclidean_weights=weights)
        self.assertIsInstance(d, float)

    def test_weighted_minkowski_no_weights_raises(self) -> None:
        """weighted_minkowski without weights raises ValueError."""
        with self.assertRaises(ValueError):
            self.db.distance(self.a, self.b, metric="weighted_minkowski")

    def test_hamming(self) -> None:
        """hamming metric returns value between 0 and 1."""
        d = self._dist("hamming")
        self.assertGreaterEqual(d, 0.0)
        self.assertLessEqual(d, 1.0)

    def test_jaccard(self) -> None:
        """jaccard metric returns float."""
        d = self._dist("jaccard")
        self.assertIsInstance(d, float)

    def test_canberra(self) -> None:
        """canberra metric returns float."""
        d = self._dist("canberra")
        self.assertIsInstance(d, float)

    def test_braycurtis(self) -> None:
        """braycurtis metric returns float."""
        d = self._dist("braycurtis")
        self.assertIsInstance(d, float)

    def test_braycurtis_zero_vectors(self) -> None:
        """braycurtis returns 0.0 for zero vectors."""
        d = self.db.distance([0.0, 0.0], [0.0, 0.0], metric="braycurtis")
        self.assertEqual(d, 0.0)

    def test_pearson_correlation(self) -> None:
        """pearson_correlation metric returns float."""
        d = self.db.distance(self.x, self.y, metric="pearson_correlation")
        self.assertIsInstance(d, float)

    def test_pearson_correlation_constant(self) -> None:
        """pearson_correlation returns 1.0 for constant array."""
        d = self.db.distance([1.0, 1.0, 1.0], [1.0, 2.0, 3.0],
                             metric="pearson_correlation")
        self.assertEqual(d, 1.0)

    def test_cosine_squared(self) -> None:
        """cosine_squared metric returns float."""
        d = self._dist("cosine_squared")
        self.assertIsInstance(d, float)

    def test_cosine_squared_zero_vector(self) -> None:
        """cosine_squared returns 1.0 for zero vector."""
        d = self.db.distance([0.0, 0.0], [1.0, 0.0], metric="cosine_squared")
        self.assertEqual(d, 1.0)

    def test_kl_divergence(self) -> None:
        """kl_divergence metric returns float."""
        d = self._dist("kl_divergence")
        self.assertIsInstance(d, float)

    def test_bhattacharyya(self) -> None:
        """bhattacharyya metric returns float."""
        d = self._dist("bhattacharyya")
        self.assertIsInstance(d, float)

    def test_hellinger(self) -> None:
        """hellinger metric returns float."""
        d = self._dist("hellinger")
        self.assertIsInstance(d, float)

    def test_ruzicka(self) -> None:
        """ruzicka metric returns float."""
        d = self._dist("ruzicka")
        self.assertIsInstance(d, float)

    def test_ruzicka_zero(self) -> None:
        """ruzicka returns 0.0 for zero vectors."""
        d = self.db.distance([0.0, 0.0], [0.0, 0.0], metric="ruzicka")
        self.assertEqual(d, 0.0)

    def test_kulczynski(self) -> None:
        """kulczynski metric returns float."""
        d = self._dist("kulczynski")
        self.assertIsInstance(d, float)

    def test_sorensen(self) -> None:
        """sorensen metric returns float."""
        d = self._dist("sorensen")
        self.assertIsInstance(d, float)

    def test_sorensen_zero(self) -> None:
        """sorensen returns 0.0 for zero vectors."""
        d = self.db.distance([0.0, 0.0], [0.0, 0.0], metric="sorensen")
        self.assertEqual(d, 0.0)

    def test_chi_squared(self) -> None:
        """chi_squared metric returns float."""
        d = self._dist("chi_squared")
        self.assertIsInstance(d, float)

    def test_jensen_shannon(self) -> None:
        """jensen_shannon metric returns float."""
        d = self._dist("jensen_shannon")
        self.assertIsInstance(d, float)

    def test_squared_euclidean(self) -> None:
        """squared_euclidean metric returns float."""
        d = self.db.distance([0.0, 0.0], [3.0, 4.0], metric="squared_euclidean")
        self.assertAlmostEqual(d, 25.0, places=5)

    def test_weighted_euclidean(self) -> None:
        """weighted_euclidean metric with weights."""
        weights = [1.0, 1.0, 1.0, 1.0]
        d = self.db.distance(self.a, self.b, metric="weighted_euclidean",
                             euclidean_weights=weights)
        self.assertIsInstance(d, float)

    def test_weighted_euclidean_no_weights_raises(self) -> None:
        """weighted_euclidean without weights raises ValueError."""
        with self.assertRaises(ValueError):
            self.db.distance(self.a, self.b, metric="weighted_euclidean")

    def test_log_cosh(self) -> None:
        """log_cosh metric returns float."""
        d = self._dist("log_cosh")
        self.assertIsInstance(d, float)

    def test_tanimoto(self) -> None:
        """tanimoto metric returns float."""
        d = self._dist("tanimoto")
        self.assertIsInstance(d, float)

    def test_rao(self) -> None:
        """rao metric returns float."""
        d = self._dist("rao")
        self.assertIsInstance(d, float)

    def test_gower(self) -> None:
        """gower metric returns float."""
        d = self._dist("gower")
        self.assertIsInstance(d, float)

    def test_gower_zero(self) -> None:
        """gower returns 0.0 for identical vectors."""
        d = self.db.distance([1.0, 2.0], [1.0, 2.0], metric="gower")
        self.assertEqual(d, 0.0)

    def test_tversky(self) -> None:
        """tversky metric returns float."""
        d = self._dist("tversky", alpha=0.5, beta=0.5)
        self.assertIsInstance(d, float)

    def test_alpha_divergence(self) -> None:
        """alpha_divergence with alpha=0.5 returns float."""
        d = self._dist("alpha_divergence", alpha=0.5)
        self.assertIsInstance(d, float)

    def test_alpha_divergence_kl(self) -> None:
        """alpha_divergence with alpha=1 behaves like KL divergence."""
        d = self._dist("alpha_divergence", alpha=1)
        self.assertIsInstance(d, float)

    def test_alpha_divergence_reverse_kl(self) -> None:
        """alpha_divergence with alpha=0 is reverse KL."""
        d = self._dist("alpha_divergence", alpha=0)
        self.assertIsInstance(d, float)

    def test_renyi_divergence(self) -> None:
        """renyi_divergence metric returns float."""
        d = self._dist("renyi_divergence", alpha=0.5)
        self.assertIsInstance(d, float)

    def test_renyi_divergence_kl_limit(self) -> None:
        """renyi_divergence with alpha=1 returns float."""
        d = self._dist("renyi_divergence", alpha=1)
        self.assertIsInstance(d, float)

    def test_total_variation(self) -> None:
        """total_variation metric returns float."""
        d = self._dist("total_variation")
        self.assertIsInstance(d, float)

    def test_mahalanobis(self) -> None:
        """mahalanobis with provided covariance matrix returns float."""
        cov = np.eye(4)
        d = self.db.distance(self.a, self.b, metric="mahalanobis",
                             covariance_matrix=cov)
        self.assertIsInstance(d, float)

    def test_jaccard_zero_union(self) -> None:
        """jaccard returns 0.0 for both-zero inputs."""
        d = self.db.distance([0.0, 0.0], [0.0, 0.0], metric="jaccard")
        self.assertEqual(d, 0.0)

    def test_tanimoto_zero_union(self) -> None:
        """tanimoto returns 0.0 for both-zero inputs."""
        d = self.db.distance([0.0, 0.0], [0.0, 0.0], metric="tanimoto")
        self.assertEqual(d, 0.0)


if __name__ == "__main__":
    unittest.main()
