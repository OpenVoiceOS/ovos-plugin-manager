import abc
from typing import List, Optional, Tuple

import numpy as np


class EmbeddingsDB:
    """Base plugin for embeddings database"""

    @abc.abstractmethod
    def add_embeddings(self, key: str, embedding: np.ndarray) -> np.ndarray:
        """Store 'embedding' under 'key' with associated metadata.

        Args:
            key (str): The unique key for the embedding.
            embedding (np.ndarray): The embedding vector to store.

        Returns:
            np.ndarray: The stored embedding.
        """
        return NotImplemented

    @abc.abstractmethod
    def get_embeddings(self, key: str) -> np.ndarray:
        """Retrieve embeddings stored under 'key'.

        Args:
            key (str): The unique key for the embedding.

        Returns:
            np.ndarray: The retrieved embedding.
        """
        return NotImplemented

    @abc.abstractmethod
    def delete_embeddings(self, key: str) -> np.ndarray:
        """Delete embeddings stored under 'key'.

        Args:
            key (str): The unique key for the embedding.

        Returns:
            np.ndarray: The deleted embedding.
        """
        return NotImplemented

    @abc.abstractmethod
    def query(self, embeddings: np.ndarray, top_k: int = 5) -> List[Tuple[str, float]]:
        """Return top_k embeddings closest to the given 'embeddings'.

        Args:
            embeddings (np.ndarray): The embedding vector to query.
            top_k (int, optional): The number of top results to return. Defaults to 5.

        Returns:
            List[Tuple[str, float]]: List of tuples containing the key and distance.
        """
        return NotImplemented

    def distance(self, embeddings_a: np.ndarray, embeddings_b: np.ndarray, metric: str = "cosine") -> float:
        """Calculate the distance between two embeddings.

        Args:
            embeddings_a (np.ndarray): The first embedding vector.
            embeddings_b (np.ndarray): The second embedding vector.
            metric (str, optional): The distance metric to use. Defaults to "cosine".

        Returns:
            float: The calculated distance.
        """
        if metric == "cosine":
            dot = np.dot(embeddings_a, embeddings_b)
            norma = np.linalg.norm(embeddings_a)
            normb = np.linalg.norm(embeddings_b)
            cos = dot / (norma * normb)
            return 1 - cos
        elif metric == "euclidean":
            return np.linalg.norm(embeddings_a - embeddings_b)
        elif metric == "manhattan":
            return np.sum(np.abs(embeddings_a - embeddings_b))
        else:
            raise ValueError("Unsupported metric")


class TextEmbeddingsStore:
    """A store for text embeddings interfacing with the embeddings database"""

    def __init__(self, db: EmbeddingsDB):
        """Initialize the text embeddings store.

        Args:
            db (EmbeddingsDB): The embeddings database instance.
        """
        self.db = db

    @abc.abstractmethod
    def get_text_embeddings(self, text: str) -> np.ndarray:
        """Convert text to its corresponding embeddings.

        Args:
            text (str): The input text to be converted.

        Returns:
            np.ndarray: The resulting embeddings.
        """
        return NotImplemented

    def add_document(self, document: str) -> None:
        """Add a document and its embeddings to the database.

        Args:
            document (str): The document to add.
        """
        embeddings = self.get_text_embeddings(document)
        self.db.add_embeddings(document, embeddings)

    def delete_document(self, document: str) -> None:
        """Delete a document and its embeddings from the database.

        Args:
            document (str): The document to delete.
        """
        self.db.delete_embeddings(document)

    def query(self, document: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """Query the database for the top_k closest embeddings to the document.

        Args:
            document (str): The document to query.
            top_k (int, optional): The number of top results to return. Defaults to 5.

        Returns:
            List[Tuple[str, float]]: List of tuples containing the document and distance.
        """
        embeddings = self.get_text_embeddings(document)
        return self.db.query(embeddings, top_k)

    def distance(self, text_a: str, text_b: str, metric: str = "cosine") -> float:
        """Calculate the distance between embeddings of two texts.

        Args:
            text_a (str): The first text.
            text_b (str): The second text.
            metric (str, optional): The distance metric to use. Defaults to "cosine".

        Returns:
            float: The calculated distance.
        """
        emb: np.ndarray = self.get_text_embeddings(text_a)
        emb2: np.ndarray = self.get_text_embeddings(text_b)
        return self.db.distance(emb, emb2, metric)


class FaceEmbeddingsStore:
    """A store for face embeddings interfacing with the embeddings database"""

    def __init__(self, db: EmbeddingsDB):
        """Initialize the face embeddings store.

        Args:
            db (EmbeddingsDB): The embeddings database instance.
        """
        self.db = db

    @abc.abstractmethod
    def get_face_embeddings(self, frame: np.ndarray) -> np.ndarray:
        """Convert an image frame to its corresponding face embeddings.

        Args:
            frame (np.ndarray): The input image frame containing a face.

        Returns:
            np.ndarray: The resulting face embeddings.
        """
        return NotImplemented

    def add_face(self, user_id: str, frame: np.ndarray):
        """Add a face and its embeddings to the database.

        Args:
            user_id (str): The unique user ID.
            frame (np.ndarray): The image frame containing the face.

        Returns:
            np.ndarray: The stored face embeddings.
        """
        emb: np.ndarray = self.get_face_embeddings(frame)
        return self.db.add_embeddings(user_id, emb)

    def delete_face(self, user_id: str):
        """Delete a face and its embeddings from the database.

        Args:
            user_id (str): The unique user ID.

        Returns:
            np.ndarray: The deleted face embeddings.
        """
        return self.db.delete_embeddings(user_id)

    def predict(self, frame: np.ndarray, top_k: int = 3, thresh: float = 0.15) -> Optional[str]:
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
        best = min(matches, key=lambda k: k[1])
        if best[1] > thresh:
            return None
        return best[0]

    def query(self, frame: np.ndarray, top_k: int = 5) -> List[Tuple[str, float]]:
        """Query the database for the top_k closest face embeddings to the frame.

        Args:
            frame (np.ndarray): The input image frame containing a face.
            top_k (int, optional): The number of top results to return. Defaults to 5.

        Returns:
            List[Tuple[str, float]]: List of tuples containing the user ID and distance.
        """
        emb = self.get_face_embeddings(frame)
        return self.db.query(emb, top_k)

    def distance(self, face_a: np.ndarray, face_b: np.ndarray, metric: str = "cosine") -> float:
        """Calculate the distance between embeddings of two faces.

        Args:
            face_a (np.ndarray): The first face embedding.
            face_b (np.ndarray): The second face embedding.
            metric (str, optional): The distance metric to use. Defaults to "cosine".

        Returns:
            float: The calculated distance.
        """
        emb: np.ndarray = self.get_face_embeddings(face_a)
        emb2: np.ndarray = self.get_face_embeddings(face_b)
        return self.db.distance(emb, emb2, metric)


class VoiceEmbeddingsStore:
    """A store for voice embeddings interfacing with the embeddings database"""

    def __init__(self, db: EmbeddingsDB):
        """Initialize the voice embeddings store.

        Args:
            db (EmbeddingsDB): The embeddings database instance.
        """
        self.db = db

    @staticmethod
    def audiochunk2array(audio_bytes: bytes) -> np.ndarray:
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
        data = audio_as_np_float32 / max_int16
        return data

    @abc.abstractmethod
    def get_voice_embeddings(self, audio_data: np.ndarray) -> np.ndarray:
        """Convert audio data to its corresponding voice embeddings.

        Args:
            audio_data (np.ndarray): The input audio data.

        Returns:
            np.ndarray: The resulting voice embeddings.
        """
        return NotImplemented

    def add_voice(self, user_id: str, audio_data: np.ndarray):
        """Add a voice and its embeddings to the database.

        Args:
            user_id (str): The unique user ID.
            audio_data (np.ndarray): The input audio data.

        Returns:
            np.ndarray: The stored voice embeddings.
        """
        emb: np.ndarray = self.get_voice_embeddings(audio_data)
        return self.db.add_embeddings(user_id, emb)

    def delete_voice(self, user_id: str):
        """Delete a voice and its embeddings from the database.

        Args:
            user_id (str): The unique user ID.

        Returns:
            np.ndarray: The deleted voice embeddings.
        """
        return self.db.delete_embeddings(user_id)

    def predict(self, audio_data: np.ndarray, top_k: int = 3, thresh: float = 0.75) -> Optional[str]:
        """Return the top predicted voice closest to the given audio_data.

        Args:
            audio_data (np.ndarray): The input audio data.
            top_k (int, optional): The number of top results to return. Defaults to 3.
            thresh (float, optional): The threshold for prediction. Defaults to 0.75.

        Returns:
            Optional[str]: The predicted user ID or None if the best match exceeds the threshold.
        """
        matches = self.query(audio_data, top_k)
        best = min(matches, key=lambda k: k[1])
        if best[1] > thresh:
            return None
        return best[0]

    def query(self, audio_data: np.ndarray, top_k: int = 5) -> List[Tuple[str, float]]:
        """Query the database for the top_k closest voice embeddings to the audio_data.

        Args:
            audio_data (np.ndarray): The input audio data.
            top_k (int, optional): The number of top results to return. Defaults to 5.

        Returns:
            List[Tuple[str, float]]: List of tuples containing the user ID and distance.
        """
        emb = self.get_voice_embeddings(audio_data)
        return self.db.query(emb, top_k)

    def distance(self, voice_a: np.ndarray, voice_b: np.ndarray, metric: str = "cosine") -> float:
        """Calculate the distance between embeddings of two voices.

        Args:
            voice_a (np.ndarray): The first voice embedding.
            voice_b (np.ndarray): The second voice embedding.
            metric (str, optional): The distance metric to use. Defaults to "cosine".

        Returns:
            float: The calculated distance.
        """
        emb = self.get_voice_embeddings(voice_a)
        emb2 = self.get_voice_embeddings(voice_b)
        return self.db.distance(emb, emb2, metric)
