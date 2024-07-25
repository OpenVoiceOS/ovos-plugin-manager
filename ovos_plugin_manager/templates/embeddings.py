import abc
from typing import List, Optional, Tuple, Dict, Union, Iterable

# Typing helpers for readability
try:
    import numpy as np
    EmbeddingsArray = np.ndarray
except ImportError:
    EmbeddingsArray = Iterable[Union[int, float]]
EmbeddingsTuple = Union[Tuple[str, float], Tuple[str, float, Dict]]


class EmbeddingsDB:
    """Base class for an embeddings database that supports storage, retrieval, and querying of embeddings."""

    @abc.abstractmethod
    def add_embeddings(self, key: str, embedding: EmbeddingsArray,
                       metadata: Optional[Dict[str, any]] = None) -> EmbeddingsArray:
        """Store 'embedding' under 'key' with associated metadata.

        Args:
            key (str): The unique key for the embedding.
            embedding (np.ndarray): The embedding vector to store.
            metadata (Optional[Dict[str, any]]): Optional metadata associated with the embedding.

        Returns:
            np.ndarray: The stored embedding.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_embeddings(self, key: str) -> EmbeddingsArray:
        """Retrieve embeddings stored under 'key'.

        Args:
            key (str): The unique key for the embedding.

        Returns:
            np.ndarray: The retrieved embedding.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete_embeddings(self, key: str) -> EmbeddingsArray:
        """Delete embeddings stored under 'key'.

        Args:
            key (str): The unique key for the embedding.

        Returns:
            np.ndarray: The deleted embedding.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def query(self, embeddings: EmbeddingsArray, top_k: int = 5,
              return_metadata: bool = False) -> List[EmbeddingsTuple]:
        """Return the top_k embeddings closest to the given 'embeddings'.

        Args:
            embeddings (np.ndarray): The embedding vector to query.
            top_k (int, optional): The number of top results to return. Defaults to 5.
            return_metadata (bool, optional): Whether to include metadata in the results. Defaults to False.

        Returns:
            List[EmbeddingsTuple]: List of tuples containing the key and distance, and optionally metadata.
        """
        raise NotImplementedError

    def distance(self, embeddings_a: EmbeddingsArray, embeddings_b: EmbeddingsArray, metric: str = "cosine",
                 alpha: float = 0.5,  # for alpha_divergence and tversky metrics
                 beta: float = 0.5,  # for tversky metric
                 p: float = 3,  # for minkowski and weighted_minkowski metrics
                 euclidean_weights: Optional[EmbeddingsArray] = None,  # required for weighted_euclidean and weighted_minkowski metrics
                 covariance_matrix: Optional[EmbeddingsArray] = None  # required for mahalanobis distance with user-defined covariance
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
        if metric == "cosine":
            # Cosine distance: 1 - cosine similarity
            # Use case: Text similarity, high-dimensional data
            dot = np.dot(embeddings_a, embeddings_b)
            norma = np.linalg.norm(embeddings_a)
            normb = np.linalg.norm(embeddings_b)
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
            return 1 - intersection / union
        elif metric == "canberra":
            # Canberra distance: Weighted version of Manhattan distance
            # Use case: Environmental data, sensitive to small changes
            return np.sum(np.abs(embeddings_a - embeddings_b) / (np.abs(embeddings_a) + np.abs(embeddings_b)))
        elif metric == "braycurtis":
            # Bray-Curtis distance: Dissimilarity between non-negative vectors
            # Use case: Ecology, species abundance
            return np.sum(np.abs(embeddings_a - embeddings_b)) / np.sum(np.abs(embeddings_a + embeddings_b))
        elif metric == "mahalanobis":
            # Mahalanobis distance: Distance considering correlations (requires covariance matrix)
            # Use case: Multivariate outlier detection
            if covariance_matrix is None:
                covariance_matrix = np.cov(embeddings_a, embeddings_b, rowvar=False)
            inv_cov_matrix = np.linalg.inv(covariance_matrix)
            delta = embeddings_a - embeddings_b
            return np.sqrt(np.dot(np.dot(delta.T, inv_cov_matrix), delta))
        elif metric == "pearson_correlation":
            # Correlation distance: 1 - Pearson correlation coefficient
            # Use case: Time series analysis, signal processing
            mean_a = np.mean(embeddings_a)
            mean_b = np.mean(embeddings_b)
            centered_a = embeddings_a - mean_a
            centered_b = embeddings_b - mean_b
            norm_a = np.linalg.norm(centered_a)
            norm_b = np.linalg.norm(centered_b)
            correlation = np.dot(centered_a, centered_b) / (norm_a * norm_b)
            return 1 - correlation
        elif metric == "spearman_rank":
            # Spearman rank correlation distance: 1 - Spearman rank correlation coefficient.
            # Use case: Measures the rank correlation between two vectors. Useful for non-linear monotonic relationships.
            rank_a = np.argsort(np.argsort(embeddings_a))
            rank_b = np.argsort(np.argsort(embeddings_b))
            return 1 - np.corrcoef(rank_a, rank_b)[0, 1]
        elif metric == "wasserstein":
            # Earth Mover's Distance (Wasserstein distance)
            # Use case: Comparing probability distributions or histograms
            arr1_sorted = np.sort(embeddings_a)
            arr2_sorted = np.sort(embeddings_b)
            cdf1 = np.cumsum(arr1_sorted) / np.sum(arr1_sorted)
            cdf2 = np.cumsum(arr2_sorted) / np.sum(arr2_sorted)
            return np.sum(np.abs(cdf1 - cdf2))
        elif metric == "cosine_squared":
            # Cosine squared distance: 1 - cosine similarity squared
            # Use case: Squared similarity, high-dimensional data
            dot = np.dot(embeddings_a, embeddings_b)
            norma = np.linalg.norm(embeddings_a)
            normb = np.linalg.norm(embeddings_b)
            cos = dot / (norma * normb)
            return 1 - cos ** 2
        elif metric == "kl_divergence":
            # Kullback-Leibler divergence: Asymmetric measure of difference between distributions
            # Use case: Information theory, probability distributions
            return np.sum(embeddings_a * np.log(embeddings_a / embeddings_b))
        elif metric == "bhattacharyya":
            # Bhattacharyya distance: Measure of overlap between statistical samples
            # Use case: Classification, image processing
            bc = np.sum(np.sqrt(embeddings_a * embeddings_b))
            return -np.log(bc)
        elif metric == "hellinger":
            # Hellinger distance: Measure of similarity between two probability distributions
            # Use case: Probability distributions, statistical inference
            return np.sqrt(0.5 * np.sum((np.sqrt(embeddings_a) - np.sqrt(embeddings_b)) ** 2))
        elif metric == "ruzicka":
            # Ruzicka distance: Similarity measure for non-negative vectors
            # Use case: Ecology, species abundance
            return 1 - np.sum(np.minimum(embeddings_a, embeddings_b)) / np.sum(np.maximum(embeddings_a, embeddings_b))
        elif metric == "kulczynski":
            # Kulczynski distance: Measure used in ecology to compare similarity
            # Use case: Ecological studies, species distribution
            return np.sum(np.abs(embeddings_a - embeddings_b)) / np.sum(np.minimum(embeddings_a, embeddings_b))
        elif metric == "sorensen":
            # Sørensen distance: Another name for Dice distance
            # Use case: Binary data comparison, text similarity
            intersection = np.sum(embeddings_a * embeddings_b)
            return 1 - (2 * intersection) / (np.sum(embeddings_a) + np.sum(embeddings_b))
        elif metric == "chi_squared":
            # Chi-squared distance: Used for comparing categorical data distributions
            # Use case: Categorical data analysis, distribution comparison
            return np.sum((embeddings_a - embeddings_b) ** 2 / (embeddings_a + embeddings_b))
        elif metric == "jensen_shannon":
            # Jensen-Shannon divergence: Symmetrized and smoothed version of KL divergence
            # Use case: Information theory, probability distributions
            m = 0.5 * (embeddings_a + embeddings_b)
            return 0.5 * (np.sum(embeddings_a * np.log(embeddings_a / m)) + np.sum(embeddings_b * np.log(embeddings_b / m)))
        elif metric == "squared_euclidean":
            # Squared Euclidean distance: Square of the Euclidean distance
            # Use case: Clustering algorithms, geometric distance
            return np.sum((embeddings_a - embeddings_b) ** 2)
        elif metric == "weighted_euclidean":
            # Weighted Euclidean distance: L2 norm with weights
            # Use case: Features with different scales or importance
            if euclidean_weights is None:
                raise ValueError("euclidean_weights must be provided for weighted_euclidean metric")
            return np.sqrt(np.sum(euclidean_weights * (embeddings_a - embeddings_b) ** 2))
        elif metric == "log_cosh":
            # Log-Cosh distance: Log of the hyperbolic cosine of the difference
            # Use case: Robustness to outliers
            return np.sum(np.log(np.cosh(embeddings_a - embeddings_b)))
        elif metric == "tanimoto":
            # Tanimoto coefficient: Similarity measure for binary vectors
            # Use case: Binary data comparison
            intersection = np.sum(embeddings_a * embeddings_b)
            return 1 - intersection / (np.sum(embeddings_a) + np.sum(embeddings_b) - intersection)
        elif metric == "rao":
            # Rao's Quadratic Entropy: Measure of divergence between distributions
            # Use case: Comparing probability distributions
            p = embeddings_a / np.sum(embeddings_a)
            q = embeddings_b / np.sum(embeddings_b)
            return np.sum((p - q) ** 2 / (p + q))
        elif metric == "gower":
            # Gower distance: Handles mixed types of data
            # Use case: Mixed data types (numerical and categorical)
            numerical_part = np.sum(np.abs(embeddings_a - embeddings_b)) / len(embeddings_a)
            categorical_part = np.mean(embeddings_a != embeddings_b)
            return numerical_part + categorical_part
        elif metric == "tversky":
            # Tversky index: Generalization of Jaccard and Dice for asymmetrical comparison
            intersection = np.sum(np.minimum(embeddings_a, embeddings_b))
            return 1 - intersection / (intersection + alpha * np.sum(embeddings_a - embeddings_b) + beta * np.sum(embeddings_b - embeddings_a))
        elif metric == "alpha_divergence":
            # Alpha divergence: Generalized divergence measure
            p = embeddings_a / np.sum(embeddings_a)
            q = embeddings_b / np.sum(embeddings_b)
            return np.sum((p ** alpha - q ** alpha) / (alpha * (p + q) ** alpha))
        elif metric == "kendall_tau":
            # Kendall's Tau distance: 1 - Kendall Tau correlation coefficient
            # Use case: Rank correlation for ordinal data
            concordant = np.sum((embeddings_a > embeddings_b) == (embeddings_b > embeddings_a))
            discordant = np.sum((embeddings_a > embeddings_b) != (embeddings_b > embeddings_a))
            return 1 - (concordant - discordant) / (concordant + discordant)
        elif metric == "renyi_divergence":
            # Renyi Divergence: Generalized divergence measure
            # Use case: Comparing probability distributions
            p = embeddings_a / np.sum(embeddings_a)
            q = embeddings_b / np.sum(embeddings_b)
            return 1 / (1 - alpha) * np.log(np.sum((p ** alpha + q ** alpha) / 2))
        elif metric == "total_variation":
            # Total Variation distance: Measure of divergence between distributions
            # Use case: Probability distributions, statistical inference
            p = embeddings_a / np.sum(embeddings_a)
            q = embeddings_b / np.sum(embeddings_b)
            return 0.5 * np.sum(np.abs(p - q))
        else:
            raise ValueError("Unsupported metric")


class TextEmbeddingsStore:
    """A store for text embeddings interfacing with the embeddings database."""

    def __init__(self, db: EmbeddingsDB):
        """Initialize the text embeddings store.

        Args:
            db (EmbeddingsDB): The embeddings database instance.
        """
        self.db = db

    @abc.abstractmethod
    def get_text_embeddings(self, text: str) -> EmbeddingsArray:
        """Convert text to its corresponding embeddings.

        Args:
            text (str): The input text to be converted.

        Returns:
            np.ndarray: The resulting embeddings.
        """
        raise NotImplementedError

    def add_document(self, document: str, metadata: Optional[Dict[str, any]] = None) -> None:
        """Add a document and its embeddings to the database.

        Args:
            document (str): The document to add.
            metadata (Optional[Dict[str, any]]): Optional metadata associated with the document.
        """
        embeddings = self.get_text_embeddings(document)
        self.db.add_embeddings(document, embeddings, metadata)

    def delete_document(self, document: str) -> None:
        """Delete a document and its embeddings from the database.

        Args:
            document (str): The document to delete.
        """
        self.db.delete_embeddings(document)

    def query(self, document: str, top_k: int = 5,
              return_metadata: bool = False) -> List[Tuple[str, float]]:
        """Query the database for the top_k closest embeddings to the document.

        Args:
            document (str): The document to query.
            top_k (int, optional): The number of top results to return. Defaults to 5.
            return_metadata (bool, optional): Whether to include metadata in the results. Defaults to False.

        Returns:
            List[Tuple[str, float]]: List of tuples containing the document and distance.
        """
        embeddings = self.get_text_embeddings(document)
        return self.db.query(embeddings, top_k,
                             return_metadata=return_metadata)

    def distance(self, text_a: str, text_b: str, metric: str = "cosine") -> float:
        """Calculate the distance between embeddings of two texts.

        Args:
            text_a (str): The first text.
            text_b (str): The second text.
            metric (str, optional): The distance metric to use. Defaults to "cosine".

        Returns:
            float: The calculated distance.
        """
        emb_a = self.get_text_embeddings(text_a)
        emb_b = self.get_text_embeddings(text_b)
        return self.db.distance(emb_a, emb_b, metric)


class FaceEmbeddingsStore:
    """A store for face embeddings interfacing with the embeddings database."""

    def __init__(self, db: EmbeddingsDB):
        """Initialize the face embeddings store.

        Args:
            db (EmbeddingsDB): The embeddings database instance.
        """
        self.db = db

    @abc.abstractmethod
    def get_face_embeddings(self, frame: EmbeddingsArray) -> EmbeddingsArray:
        """Convert an image frame to its corresponding face embeddings.

        Args:
            frame (np.ndarray): The input image frame containing a face.

        Returns:
            np.ndarray: The resulting face embeddings.
        """
        raise NotImplementedError

    def add_face(self, user_id: str, frame: EmbeddingsArray, metadata: Optional[Dict[str, any]] = None) -> EmbeddingsArray:
        """Add a face and its embeddings to the database.

        Args:
            user_id (str): The unique user ID.
            frame (np.ndarray): The image frame containing the face.
            metadata (Optional[Dict[str, any]]): Optional metadata associated with the face.

        Returns:
            np.ndarray: The stored face embeddings.
        """
        embeddings = self.get_face_embeddings(frame)
        return self.db.add_embeddings(user_id, embeddings, metadata)

    def delete_face(self, user_id: str) -> EmbeddingsArray:
        """Delete a face and its embeddings from the database.

        Args:
            user_id (str): The unique user ID.

        Returns:
            np.ndarray: The deleted face embeddings.
        """
        return self.db.delete_embeddings(user_id)

    def predict(self, frame: EmbeddingsArray, top_k: int = 3, thresh: float = 0.15) -> Optional[str]:
        """Return the top predicted face closest to the given frame.

        Args:
            frame (np.ndarray): The input image frame containing a face.
            top_k (int, optional): The number of top results to return. Defaults to 3.
            thresh (float, optional): The threshold for prediction. Defaults to 0.15.

        Returns:
            Optional[str]: The predicted user ID or None if the best match exceeds the threshold.
        """
        matches = self.query(frame, top_k)
        if not matches:
            return None
        best_match = min(matches, key=lambda k: k[1])
        if best_match[1] > thresh:
            return None
        return best_match[0]

    def query(self, frame: EmbeddingsArray, top_k: int = 5,
                return_metadata: bool = False) -> List[Tuple[str, float]]:
        """Query the database for the top_k closest face embeddings to the frame.

        Args:
            frame (np.ndarray): The input image frame containing a face.
            top_k (int, optional): The number of top results to return. Defaults to 5.
            return_metadata (bool, optional): Whether to include metadata in the results. Defaults to False.

        Returns:
            List[Tuple[str, float]]: List of tuples containing the user ID and distance.
        """
        embeddings = self.get_face_embeddings(frame)
        return self.db.query(embeddings, top_k,
                             return_metadata=return_metadata)

    def distance(self, face_a: EmbeddingsArray, face_b: EmbeddingsArray, metric: str = "cosine") -> float:
        """Calculate the distance between embeddings of two faces.

        Args:
            face_a (np.ndarray): The first face embedding.
            face_b (np.ndarray): The second face embedding.
            metric (str, optional): The distance metric to use. Defaults to "cosine".

        Returns:
            float: The calculated distance.
        """
        emb_a = self.get_face_embeddings(face_a)
        emb_b = self.get_face_embeddings(face_b)
        return self.db.distance(emb_a, emb_b, metric)


class VoiceEmbeddingsStore:
    """A store for voice embeddings interfacing with the embeddings database."""

    def __init__(self, db: EmbeddingsDB):
        """Initialize the voice embeddings store.

        Args:
            db (EmbeddingsDB): The embeddings database instance.
        """
        self.db = db

    @staticmethod
    def audiochunk2array(audio_bytes: bytes) -> EmbeddingsArray:
        """Convert audio buffer to a normalized float32 NumPy array.

        Args:
            audio_bytes (bytes): The audio data buffer.

        Returns:
            np.ndarray: The normalized float32 audio array.
        """
        audio_as_np_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
        audio_as_np_float32 = audio_as_np_int16.astype(np.float32)
        # Normalise float32 array so that values are between -1.0 and +1.0
        max_int16 = 2 ** 15
        return audio_as_np_float32 / max_int16

    @abc.abstractmethod
    def get_voice_embeddings(self, audio_data: EmbeddingsArray) -> EmbeddingsArray:
        """Convert audio data to its corresponding voice embeddings.

        Args:
            audio_data (np.ndarray): The input audio data.

        Returns:
            np.ndarray: The resulting voice embeddings.
        """
        raise NotImplementedError

    def add_voice(self, user_id: str, audio_data: EmbeddingsArray, metadata: Optional[Dict[str, any]] = None) -> EmbeddingsArray:
        """Add a voice and its embeddings to the database.

        Args:
            user_id (str): The unique user ID.
            audio_data (np.ndarray): The input audio data.
            metadata (Optional[Dict[str, any]]): Optional metadata associated with the voice.

        Returns:
            np.ndarray: The stored voice embeddings.
        """
        embeddings = self.get_voice_embeddings(audio_data)
        return self.db.add_embeddings(user_id, embeddings, metadata)

    def delete_voice(self, user_id: str) -> EmbeddingsArray:
        """Delete a voice and its embeddings from the database.

        Args:
            user_id (str): The unique user ID.

        Returns:
            np.ndarray: The deleted voice embeddings.
        """
        return self.db.delete_embeddings(user_id)

    def predict(self, audio_data: EmbeddingsArray, top_k: int = 3, thresh: float = 0.75) -> Optional[str]:
        """Return the top predicted voice closest to the given audio_data.

        Args:
            audio_data (np.ndarray): The input audio data.
            top_k (int, optional): The number of top results to return. Defaults to 3.
            thresh (float, optional): The threshold for prediction. Defaults to 0.75.

        Returns:
            Optional[str]: The predicted user ID or None if the best match exceeds the threshold.
        """
        matches = self.query(audio_data, top_k)
        if not matches:
            return None
        best_match = min(matches, key=lambda k: k[1])
        if best_match[1] > thresh:
            return None
        return best_match[0]

    def query(self, audio_data: EmbeddingsArray, top_k: int = 5,
                return_metadata: bool = False) -> List[Tuple[str, float]]:
        """Query the database for the top_k closest voice embeddings to the audio_data.

        Args:
            audio_data (np.ndarray): The input audio data.
            top_k (int, optional): The number of top results to return. Defaults to 5.
            return_metadata (bool, optional): Whether to include metadata in the results. Defaults to False.

        Returns:
            List[Tuple[str, float]]: List of tuples containing the user ID and distance.
        """
        embeddings = self.get_voice_embeddings(audio_data)
        return self.db.query(embeddings, top_k,
                             return_metadata=return_metadata)

    def distance(self, voice_a: EmbeddingsArray, voice_b: EmbeddingsArray, metric: str = "cosine") -> float:
        """Calculate the distance between embeddings of two voices.

        Args:
            voice_a (np.ndarray): The first voice embedding.
            voice_b (np.ndarray): The second voice embedding.
            metric (str, optional): The distance metric to use. Defaults to "cosine".

        Returns:
            float: The calculated distance.
        """
        emb_a = self.get_voice_embeddings(voice_a)
        emb_b = self.get_voice_embeddings(voice_b)
        return self.db.distance(emb_a, emb_b, metric)
