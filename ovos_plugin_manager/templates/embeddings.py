import abc
from typing import List, Optional, Tuple, Dict, Union, Iterable, Any

# Typing helpers for readability
try:
    import numpy as np

    EmbeddingsArray = Array = np.ndarray
except ImportError:
    EmbeddingsArray = Array = Iterable[Union[int, float]]

# EmbeddingsTuple is specifically for query results (key, distance, optional metadata)
EmbeddingsTuple = Union[Tuple[str, float], Tuple[str, float, Dict]]

# RetrievedEmbeddingResult is for getting embeddings (key, embedding, optional metadata)
RetrievedEmbeddingResult = Union[Tuple[str, EmbeddingsArray], Tuple[str, EmbeddingsArray, Dict[str, Any]]]


class EmbeddingsDB:
    """
    Base class for an embeddings database that supports storage, retrieval, and querying of embeddings.
    This extended version includes abstractions for collections (vector stores) and batch handling.
    Batch methods provide a default implementation that processes inputs one at a time,
    allowing downstream plugins to override for optimized batch processing.
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

    @abc.abstractmethod
    def create_collection(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> Any:
        """
        Create a new collection (vector store).

        Args:
            name (str): The name of the collection (vector store ID).
            metadata (Optional[Dict[str, Any]]): Optional metadata for the collection.

        Returns:
            Any: A handle or object representing the created collection.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_collection(self, name: str) -> Any:
        """
        Retrieve an existing collection by name.

        Args:
            name (str): The name of the collection.

        Returns:
            Any: A handle or object representing the retrieved collection.

        Raises:
            ValueError: If the collection is not found.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete_collection(self, name: str) -> None:
        """
        Delete a collection by name.

        Args:
            name (str): The name of the collection to delete.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def list_collections(self) -> List[Any]:
        """
        List all available collections.

        Returns:
            List[Any]: A list of handles or objects representing the collections.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def add_embeddings(self, key: str, embedding: EmbeddingsArray,
                       metadata: Optional[Dict[str, Any]] = None,
                       collection_name: Optional[str] = None) -> EmbeddingsArray:
        """Store 'embedding' under 'key' with associated metadata.

        Args:
            key (str): The unique key for the embedding.
            embedding (np.ndarray): The embedding vector to store.
            metadata (Optional[Dict[str, Any]]): Optional metadata associated with the embedding.
            collection_name (Optional[str]): The name of the collection to add the embedding to.
                                             If None, a default collection should be used.

        Returns:
            np.ndarray: The stored embedding.
        """
        raise NotImplementedError

    def add_embeddings_batch(self, keys: List[str], embeddings: List[EmbeddingsArray],
                             metadata: Optional[List[Dict[str, Any]]] = None,
                             collection_name: Optional[str] = None) -> None:
        """
        Add or update multiple embeddings in a batch to a specific collection.
        Default implementation processes inputs one at a time. Plugins can override for optimization.

        Args:
            keys (List[str]): List of unique keys for the embeddings.
            embeddings (List[EmbeddingsArray]): List of embedding vectors to store.
            metadata (Optional[List[Dict[str, Any]]]): Optional list of metadata dictionaries.
            collection_name (Optional[str]): The name of the collection to add the embeddings to.
        """
        if metadata is None:
            metadata = [None] * len(keys)
        for i, key in enumerate(keys):
            self.add_embeddings(key, embeddings[i], metadata[i], collection_name=collection_name)

    @abc.abstractmethod
    def get_embeddings(self, key: str, collection_name: Optional[str] = None,
                       return_metadata: bool = False) -> Union[Optional[EmbeddingsArray],
                                                               Tuple[Optional[EmbeddingsArray], Optional[Dict[str, Any]]]]:
        """
        Retrieve embeddings stored under 'key' from the specified or default collection.

        Args:
            key (str): The unique key for the embedding.
            collection_name (Optional[str]): The name of the collection to retrieve from.
            return_metadata (bool, optional): Whether to include metadata in the results. Defaults to False.

        Returns:
            Union[Optional[np.ndarray], Tuple[Optional[np.ndarray], Optional[Dict[str, Any]]]] :
            If `return_metadata` is False, returns the retrieved embedding (np.ndarray) or None if not found.
            If `return_metadata` is True, returns a tuple (embedding, metadata_dict) or (None, None) if not found.
        """
        raise NotImplementedError

    def get_embeddings_batch(self, keys: List[str], collection_name: Optional[str] = None,
                             return_metadata: bool = False) -> List[RetrievedEmbeddingResult]:
        """
        Retrieve multiple embeddings and their metadata from a specific collection.
        Default implementation processes inputs one at a time. Plugins can override for optimization.

        Args:
            keys (List[str]): List of keys for the embeddings to retrieve.
            collection_name (Optional[str]): The name of the collection to retrieve from.
            return_metadata (bool, optional): Whether to include metadata in the results. Defaults to False.

        Returns:
            List[RetrievedEmbeddingResult]: A list of tuples, where each tuple is
            (key, embedding) if `return_metadata` is False, or (key, embedding, metadata)
            if `return_metadata` is True.
        """
        results = []
        for key in keys:
            # Call the single get_embeddings method with return_metadata
            retrieved_data = self.get_embeddings(key, collection_name=collection_name, return_metadata=return_metadata)
            if retrieved_data is not None:
                if return_metadata:
                    embedding, metadata = retrieved_data
                    if embedding is not None: # Ensure embedding is not None before appending
                        results.append((key, embedding, metadata))
                else:
                    embedding = retrieved_data
                    if embedding is not None: # Ensure embedding is not None before appending
                        results.append((key, embedding))
        return results

    @abc.abstractmethod
    def delete_embeddings(self, key: str, collection_name: Optional[str] = None) -> None:
        """Delete embeddings stored under 'key'.

        Args:
            key (str): The unique key for the embedding.
            collection_name (Optional[str]): The name of the collection to delete from.
        """
        raise NotImplementedError

    def delete_embeddings_batch(self, keys: List[str], collection_name: Optional[str] = None) -> None:
        """
        Delete multiple embeddings in a batch from a specific collection.
        Default implementation processes inputs one at a time. Plugins can override for optimization.

        Args:
            keys (List[str]): List of keys for the embeddings to delete.
            collection_name (Optional[str]): The name of the collection to delete from.
        """
        for key in keys:
            self.delete_embeddings(key, collection_name=collection_name)

    @abc.abstractmethod
    def query(self, embeddings: EmbeddingsArray, top_k: int = 5,
              return_metadata: bool = False, collection_name: Optional[str] = None) -> List[EmbeddingsTuple]:
        """Return the top_k embeddings closest to the given 'embeddings'.

        Args:
            embeddings (np.ndarray): The embedding vector to query.
            top_k (int, optional): The number of top results to return. Defaults to 5.
            return_metadata (bool, optional): Whether to include metadata in the results. Defaults to False.
            collection_name (Optional[str]): The name of the collection to query.

        Returns:
            List[EmbeddingsTuple]: List of tuples containing the key and distance, and optionally metadata.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def count_embeddings_in_collection(self, collection_name: Optional[str] = None) -> int:
        """
        Count the number of embeddings in a specific collection.

        Args:
            collection_name (Optional[str]): The name of the collection.

        Returns:
            int: The number of embeddings in the collection.
        """
        raise NotImplementedError

    def distance(self, embeddings_a: EmbeddingsArray, embeddings_b: EmbeddingsArray, metric: str = "cosine",
                 alpha: float = 0.5,  # for alpha_divergence and tversky metrics
                 beta: float = 0.5,  # for tversky metric
                 p: float = 3,  # for minkowski and weighted_minkowski metrics
                 euclidean_weights: Optional[EmbeddingsArray] = None,
                 # required for weighted_euclidean and weighted_minkowski metrics
                 covariance_matrix: Optional[EmbeddingsArray] = None
                 # required for mahalanobis distance with user-defined covariance
                 ) -> float:
        """
        Calculate the distance between two embeddings vectors using the specified distance metric.

        Args:
            embeddings_a (np.ndarray): The first embedding vector.
            embeddings_b (np.ndarray): The second embedding vector.
            metric (str, optional): The distance metric to use. Defaults to "cosine".
                Supported metrics include:
                - "cosine": Cosine distance, 1 - cosine similarity. Useful for text similarity and high-dimensional data.
                - "euclidean": Euclidean distance, L2 norm of the difference. Commonly used in clustering and geometric distance.
                - "manhattan": Manhattan distance, L1 norm of the difference. Suitable for grid-based maps and robotics.
                - "chebyshev": Chebyshev distance, maximum absolute difference. Used for chessboard distance and pathfinding.
                - "minkowski": Minkowski distance, generalization of Euclidean and Manhattan distances. Parameterized by p, flexible use case.
                - "weighted_minkowski": Weighted Minkowski distance, a generalization of Minkowski with weights. Parameterized by `p`, uses `euclidean_weights`.
                - "hamming": Hamming distance, proportion of differing elements. Ideal for error detection and binary data.
                - "jaccard": Jaccard distance, 1 - Jaccard similarity (intersection over union). Used for set similarity and binary attributes.
                - "canberra": Canberra distance, weighted version of Manhattan distance. Sensitive to small changes, used in environmental data.
                - "braycurtis": Bray-Curtis distance, dissimilarity between non-negative vectors. Common in ecology and species abundance studies.
                - "mahalanobis": Mahalanobis distance, considering correlations (requires covariance matrix). Useful for multivariate outlier detection.
                - "pearson_correlation": Pearson correlation distance, 1 - Pearson correlation coefficient. Used in time series analysis and signal processing.
                - "spearman_rank": Spearman rank correlation distance, 1 - Spearman rank correlation coefficient. Measures rank correlation for non-linear monotonic relationships.
                - "wasserstein": Earth Mover's Distance (Wasserstein distance). Compares probability distributions or histograms.
                - "cosine_squared": Cosine squared distance, 1 - cosine similarity squared. For squared similarity in high-dimensional data.
                - "kl_divergence": Kullback-Leibler divergence, asymmetric measure of difference between distributions. Applied in information theory and probability distributions.
                - "bhattacharyya": Bhattacharyya distance, measure of overlap between statistical samples. Useful in classification and image processing.
                - "hellinger": Hellinger distance, measure of similarity between two probability distributions. Applied in statistical inference.
                - "ruzicka": Ruzicka distance, similarity measure for non-negative vectors. Used in ecology and species abundance.
                - "kulczynski": Kulczynski distance, used in ecology to compare similarity. Suitable for ecological studies and species distribution.
                - "sorensen": Sørensen distance, another name for Dice distance. Applied in binary data comparison and text similarity.
                - "chi_squared": Chi-squared distance, used for comparing categorical data distributions. Suitable for categorical data analysis and distribution comparison.
                - "jensen_shannon": Jensen-Shannon divergence, symmetrized and smoothed version of KL divergence. Used in information theory and probability distributions.
                - "squared_euclidean": Squared Euclidean distance, square of the Euclidean distance. Useful for clustering algorithms and geometric distance.
                - "weighted_euclidean": Weighted Euclidean distance, L2 norm with weights. Applied when features have different scales or importance.
                - "log_cosh": Log-Cosh distance, log of the hyperbolic cosine of the difference. Robust to outliers.
                - "tanimoto": Tanimoto coefficient, similarity measure for binary vectors. Used for binary data comparison.
                - "rao": Rao's Quadratic Entropy, measure of divergence between distributions. Useful for comparing probability distributions.
                - "gower": Gower distance, handles mixed types of data. Applied in cases with numerical and categorical data.
                - "tversky": Tversky index, generalization of Jaccard and Dice for asymmetrical comparison. Parameterized by alpha and beta.
                - "alpha_divergence": Alpha divergence, generalized divergence measure. Parameterized by alpha, used for comparing distributions.
                - "kendall_tau": Kendall's Tau distance: 1 - Kendall Tau correlation coefficient. Use case: Rank correlation for ordinal data
                - "renyi_divergence": Generalized divergence measure. Use case: Comparing probability distributions
                - "total_variation":  Measure of divergence between distributions. Use case: Probability distributions, statistical inference

            alpha (float, optional): Parameter for `tversky` and `alpha_divergence` metrics. Default is 0.5.
            beta (float, optional): Parameter for `tversky` metric. Default is 0.5.
            p (float, optional): Parameter for `minkowski` and `weighted_minkowski` metrics. Default is 3.
            euclidean_weights (Optional[np.ndarray], optional): Weights for `weighted_euclidean` and `weighted_minkowski` metrics. Must be provided if using these metrics. Default is None.
            covariance_matrix (Optional[np.ndarray], optional): Covariance matrix for `mahalanobis` distance. Must be provided if using this metric. Default is None.

        Returns:
            float: The calculated distance between the two embedding vectors.

        Raises:
            ValueError: If the specified metric is unsupported or requires parameters not provided.
        """
        # Ensure embeddings are numpy arrays for consistent calculations
        embeddings_a = np.asarray(embeddings_a)
        embeddings_b = np.asarray(embeddings_b)

        if metric == "cosine":
            # Cosine distance: 1 - cosine similarity
            # Use case: Text similarity, high-dimensional data
            dot = np.dot(embeddings_a, embeddings_b)
            norma = np.linalg.norm(embeddings_a)
            normb = np.linalg.norm(embeddings_b)
            if norma == 0 or normb == 0:
                return 1.0 # Or raise an error, depending on desired behavior for zero vectors
            cos = dot / (norma * normb)
            return 1 - cos
        elif metric == "euclidean":
            # Euclidean distance: L2 norm of the difference
            # Use case: Geometric distance, clustering
            return np.linalg.norm(embeddings_a - embeddings_b)
        elif metric == "manhattan":
            # Manhattan distance: L1 norm of the difference
            # Use case: Grid-based maps, robotics
            return np.sum(np.abs(embeddings_a - embeddings_b))
        elif metric == "chebyshev":
            # Chebyshev distance: Maximum absolute difference
            # Use case: Chessboard distance, pathfinding
            return np.max(np.abs(embeddings_a - embeddings_b))
        elif metric == "minkowski":
            # Minkowski distance: Generalization of Euclidean and Manhattan distances
            # Use case: Flexible distance metric, parameterized by p
            return np.sum(np.abs(embeddings_a - embeddings_b) ** p) ** (1 / p)
        elif metric == "weighted_minkowski":
            # Weighted Minkowski distance: Generalization of Minkowski distance with weights
            # Use case: Flexible distance metric with weighted dimensions
            if euclidean_weights is None:
                raise ValueError("euclidean_weights must be provided for weighted_minkowski metric")
            if not isinstance(euclidean_weights, np.ndarray):
                euclidean_weights = np.asarray(euclidean_weights)
            return np.sum(euclidean_weights * np.abs(embeddings_a - embeddings_b) ** p) ** (1 / p)
        elif metric == "hamming":
            # Hamming distance: Proportion of differing elements
            # Use case: Error detection, binary data
            return np.mean(embeddings_a != embeddings_b)
        elif metric == "jaccard":
            # Jaccard distance: 1 - Jaccard similarity (intersection over union)
            # Use case: Set similarity, binary attributes
            intersection = np.sum(np.minimum(embeddings_a, embeddings_b))
            union = np.sum(np.maximum(embeddings_a, embeddings_b))
            if union == 0:
                return 0.0 # Both sets are empty, considered perfectly similar
            return 1 - intersection / union
        elif metric == "canberra":
            # Canberra distance: Weighted version of Manhattan distance.
            # Use case: Environmental data, sensitive to small changes.
            numerator = np.abs(embeddings_a - embeddings_b)
            denominator = np.abs(embeddings_a) + np.abs(embeddings_b)
            # Avoid division by zero: if denominator is zero, that term is 0
            safe_division = np.divide(numerator, denominator, out=np.zeros_like(numerator), where=denominator!=0)
            return np.sum(safe_division)
        elif metric == "braycurtis":
            # Bray-Curtis distance: Dissimilarity between non-negative vectors
            # Use case: Ecology, species abundance
            numerator = np.sum(np.abs(embeddings_a - embeddings_b))
            denominator = np.sum(np.abs(embeddings_a + embeddings_b))
            if denominator == 0:
                return 0.0 # Or raise error if both vectors are zero
            return numerator / denominator
        elif metric == "mahalanobis":
            # Mahalanobis distance: Distance considering correlations (requires covariance matrix)
            # Use case: Multivariate outlier detection
            if covariance_matrix is None:
                # If no covariance matrix is provided, calculate from the data
                # This assumes embeddings_a and embeddings_b are samples, not single points
                # For single points, a pre-computed covariance matrix is needed.
                # For simplicity, we'll assume a diagonal covariance if not provided for two points.
                if embeddings_a.shape != embeddings_b.shape:
                    raise ValueError("Embeddings must have the same shape for Mahalanobis distance.")
                combined_data = np.vstack([embeddings_a, embeddings_b])
                covariance_matrix = np.cov(combined_data, rowvar=False)
                if np.linalg.det(covariance_matrix) == 0:
                    raise ValueError("Singular covariance matrix. Cannot compute Mahalanobis distance.")

            inv_cov_matrix = np.linalg.inv(covariance_matrix)
            delta = embeddings_a - embeddings_b
            return np.sqrt(np.dot(np.dot(delta.T, inv_cov_matrix), delta))
        elif metric == "pearson_correlation":
            # Correlation distance: 1 - Pearson correlation coefficient
            # Use case: Time series analysis, signal processing
            if np.std(embeddings_a) == 0 or np.std(embeddings_b) == 0:
                return 1.0 # Cannot compute correlation if one array is constant
            return 1 - np.corrcoef(embeddings_a, embeddings_b)[0, 1]
        elif metric == "spearman_rank":
            # Spearman rank correlation distance: 1 - Spearman rank correlation coefficient.
            # Use case: Measures the rank correlation between two vectors. Useful for non-linear monotonic relationships.
            from scipy.stats import spearmanr
            correlation, _ = spearmanr(embeddings_a, embeddings_b)
            return 1 - correlation
        elif metric == "wasserstein":
            # Earth Mover's Distance (Wasserstein distance)
            # Use case: Comparing probability distributions or histograms
            from scipy.stats import wasserstein_distance
            return wasserstein_distance(embeddings_a, embeddings_b)
        elif metric == "cosine_squared":
            # Cosine squared distance: 1 - cosine similarity squared.
            # Use case: Squared similarity, high-dimensional data.
            dot = np.dot(embeddings_a, embeddings_b)
            norma = np.linalg.norm(embeddings_a)
            normb = np.linalg.norm(embeddings_b)
            if norma == 0 or normb == 0:
                return 1.0
            cos = dot / (norma * normb)
            return 1 - cos ** 2
        elif metric == "kl_divergence":
            # Kullback-Leibler divergence: Asymmetric measure of difference between distributions
            # Use case: Information theory, probability distributions
            # Add a small epsilon to avoid log(0)
            epsilon = 1e-10
            p_norm = embeddings_a / np.sum(embeddings_a)
            q_norm = embeddings_b / np.sum(embeddings_b)
            return np.sum(p_norm * np.log((p_norm + epsilon) / (q_norm + epsilon)))
        elif metric == "bhattacharyya":
            # Bhattacharyya distance: Measure of overlap between statistical samples
            # Use case: Classification, image processing
            # Ensure non-negative and normalized for probability distributions
            p_norm = embeddings_a / np.sum(embeddings_a)
            q_norm = embeddings_b / np.sum(embeddings_b)
            bc = np.sum(np.sqrt(p_norm * q_norm))
            if bc == 0:
                return float('inf') # Distributions are completely disjoint
            return -np.log(bc)
        elif metric == "hellinger":
            # Hellinger distance: Measure of similarity between two probability distributions
            # Use case: Probability distributions, statistical inference
            p_norm = embeddings_a / np.sum(embeddings_a)
            q_norm = embeddings_b / np.sum(embeddings_b)
            return np.sqrt(0.5 * np.sum((np.sqrt(p_norm) - np.sqrt(q_norm)) ** 2))
        elif metric == "ruzicka":
            # Ruzicka distance: Similarity measure for non-negative vectors
            # Use case: Ecology, species abundance
            numerator = np.sum(np.minimum(embeddings_a, embeddings_b))
            denominator = np.sum(np.maximum(embeddings_a, embeddings_b))
            if denominator == 0:
                return 0.0
            return 1 - numerator / denominator
        elif metric == "kulczynski":
            # Kulczynski distance: Measure used in ecology to compare similarity
            # Use case: Ecological studies, species distribution
            numerator = np.sum(np.abs(embeddings_a - embeddings_b))
            denominator = np.sum(np.minimum(embeddings_a, embeddings_b))
            if denominator == 0:
                return float('inf') # No common elements
            return numerator / denominator
        elif metric == "sorensen":
            # Sørensen distance: Another name for Dice distance
            # Use case: Binary data comparison, text similarity
            intersection = np.sum(np.minimum(embeddings_a, embeddings_b)) # For non-binary, this is sum of mins
            denominator = np.sum(embeddings_a) + np.sum(embeddings_b)
            if denominator == 0:
                return 0.0
            return 1 - (2 * intersection) / denominator
        elif metric == "chi_squared":
            # Chi-squared distance: Used for comparing categorical data distributions
            # Use case: Categorical data analysis, distribution comparison
            epsilon = 1e-10
            return np.sum((embeddings_a - embeddings_b) ** 2 / (embeddings_a + embeddings_b + epsilon))
        elif metric == "jensen_shannon":
            # Jensen-Shannon divergence: Symmetrized and smoothed version of KL divergence
            # Use case: Information theory, probability distributions
            epsilon = 1e-10
            p_norm = embeddings_a / np.sum(embeddings_a)
            q_norm = embeddings_b / np.sum(embeddings_b)
            m = 0.5 * (p_norm + q_norm)
            return 0.5 * (np.sum(p_norm * np.log((p_norm + epsilon) / (m + epsilon))) +
                          np.sum(q_norm * np.log((q_norm + epsilon) / (m + epsilon))))
        elif metric == "squared_euclidean":
            # Squared Euclidean distance: Square of the Euclidean distance
            # Use case: Clustering algorithms, geometric distance
            return np.sum((embeddings_a - embeddings_b) ** 2)
        elif metric == "weighted_euclidean":
            # Weighted Euclidean distance: L2 norm with weights
            # Use case: Features with different scales or importance
            if euclidean_weights is None:
                raise ValueError("euclidean_weights must be provided for weighted_euclidean metric")
            if not isinstance(euclidean_weights, np.ndarray):
                euclidean_weights = np.asarray(euclidean_weights)
            return np.sqrt(np.sum(euclidean_weights * (embeddings_a - embeddings_b) ** 2))
        elif metric == "log_cosh":
            # Log-Cosh distance: Log of the hyperbolic cosine of the difference
            # Use case: Robustness to outliers
            return np.sum(np.log(np.cosh(embeddings_a - embeddings_b)))
        elif metric == "tanimoto":
            # Tanimoto coefficient: Similarity measure for binary vectors
            # Use case: Binary data comparison
            intersection = np.sum(np.minimum(embeddings_a, embeddings_b))
            union = np.sum(np.maximum(embeddings_a, embeddings_b))
            if union == 0:
                return 0.0
            return 1 - intersection / union
        elif metric == "rao":
            # Rao's Quadratic Entropy: Measure of divergence between distributions
            # Use case: Comparing probability distributions
            p_norm = embeddings_a / np.sum(embeddings_a)
            q_norm = embeddings_b / np.sum(embeddings_b)
            # This is a simplified version, true Rao's involves a dissimilarity matrix
            return np.sum((p_norm - q_norm) ** 2 / (p_norm + q_norm + 1e-10))
        elif metric == "gower":
            # Gower distance: Handles mixed types of data.
            # Use case: Mixed data types (numerical and categorical).
            # This is a highly simplified example. A full Gower implementation is complex
            # and depends on knowing which dimensions are numerical/categorical.
            # For purely numerical, it's often scaled Manhattan or Euclidean.
            # Here, we'll just use a simple average of scaled absolute differences.
            max_diff = np.max(np.abs(embeddings_a - embeddings_b))
            if max_diff == 0: return 0.0
            return np.mean(np.abs(embeddings_a - embeddings_b) / max_diff)
        elif metric == "tversky":
            # Tversky index: Generalization of Jaccard and Dice for asymmetrical comparison
            intersection = np.sum(np.minimum(embeddings_a, embeddings_b))
            fp = np.sum(np.maximum(0, embeddings_a - embeddings_b)) # False positives from A
            fn = np.sum(np.maximum(0, embeddings_b - embeddings_a)) # False negatives from A
            denominator = intersection + alpha * fp + beta * fn
            if denominator == 0:
                return 1.0 # No common elements, maximum dissimilarity
            return 1 - intersection / denominator
        elif metric == "alpha_divergence":
            # Alpha divergence: Generalized divergence measure
            epsilon = 1e-10
            p_norm = embeddings_a / np.sum(embeddings_a)
            q_norm = embeddings_b / np.sum(embeddings_b)
            if alpha == 1: # KL divergence
                return np.sum(p_norm * np.log((p_norm + epsilon) / (q_norm + epsilon)))
            elif alpha == 0: # Reverse KL divergence
                return np.sum(q_norm * np.log((q_norm + epsilon) / (p_norm + epsilon)))
            else:
                return (1 / (alpha * (alpha - 1))) * np.sum(alpha * p_norm + (1 - alpha) * q_norm -
                                                              p_norm**alpha * q_norm**(1-alpha))
        elif metric == "kendall_tau":
            # Kendall's Tau distance: 1 - Kendall Tau correlation coefficient
            # Use case: Rank correlation for ordinal data
            from scipy.stats import kendalltau
            correlation, _ = kendalltau(embeddings_a, embeddings_b)
            return 1 - correlation
        elif metric == "renyi_divergence":
            # Renyi Divergence: Generalized divergence measure
            # Use case: Comparing probability distributions
            epsilon = 1e-10
            p_norm = embeddings_a / np.sum(embeddings_a)
            q_norm = embeddings_b / np.sum(embeddings_b)
            if alpha == 1: # Limit as alpha -> 1 is KL divergence
                return np.sum(p_norm * np.log((p_norm + epsilon) / (q_norm + epsilon)))
            else:
                return (1 / (alpha - 1)) * np.log(np.sum((p_norm**alpha) / (q_norm**(alpha - 1) + epsilon)))
        elif metric == "total_variation":
            # Total Variation distance: Measure of divergence between distributions
            # Use case: Probability distributions, statistical inference
            p_norm = embeddings_a / np.sum(embeddings_a)
            q_norm = embeddings_b / np.sum(embeddings_b)
            return 0.5 * np.sum(np.abs(p_norm - q_norm))
        else:
            raise ValueError(f"Unsupported metric: {metric}")


class TextEmbedder:

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

    @abc.abstractmethod
    def get_embeddings(self, text: str) -> EmbeddingsArray:
        """Convert text to its corresponding embeddings.

        Args:
            text (str): The input text to be converted.

        Returns:
            np.ndarray: The resulting embeddings.
        """
        raise NotImplementedError


class ImageEmbedder:

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

    @abc.abstractmethod
    def get_embeddings(self, frame: Array) -> EmbeddingsArray:
        """Convert an image frame to its corresponding image embeddings.

        Args:
            frame (np.ndarray): The input image frame containing a image.

        Returns:
            np.ndarray: The resulting image embeddings.
        """
        raise NotImplementedError


class FaceEmbedder:

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

    @abc.abstractmethod
    def get_embeddings(self, frame: Array) -> EmbeddingsArray:
        """Convert an image frame to its corresponding face embeddings.

        Args:
            frame (np.ndarray): The input image frame containing a face.

        Returns:
            np.ndarray: The resulting face embeddings.
        """
        raise NotImplementedError


class VoiceEmbedder:

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

    @abc.abstractmethod
    def get_embeddings(self, audio_data: Array) -> EmbeddingsArray:
        """Convert audio data to its corresponding voice embeddings.

        Args:
            audio_data (np.ndarray): The input audio data.

        Returns:
            np.ndarray: The resulting voice embeddings.
        """
        raise NotImplementedError
