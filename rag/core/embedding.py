import hashlib
import math
from abc import ABC, abstractmethod
from typing import List


class Embedder(ABC):
    """Interfaz de embeddings intercambiable (OpenAI, local o mock)."""

    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Retorna un vector de embedding por cada texto."""

    def embed_query(self, text: str) -> List[float]:
        return self.embed([text])[0]


class HashingEmbedder(Embedder):
    """Embedder deterministico sin dependencias, util para desarrollo y pruebas."""

    def __init__(self, vector_size: int = 128):
        if vector_size <= 0:
            raise ValueError("vector_size debe ser mayor que 0")
        self.vector_size = vector_size

    def embed(self, texts: List[str]) -> List[List[float]]:
        return [self._embed_one(text or "") for text in texts]

    def _embed_one(self, text: str) -> List[float]:
        vector = [0.0] * self.vector_size

        if not text:
            return vector

        tokens = text.lower().split()
        if not tokens:
            tokens = [text.lower()]

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for i, byte in enumerate(digest):
                bucket = (i + byte) % self.vector_size
                vector[bucket] += byte / 255.0

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector

        return [value / norm for value in vector]


class SentenceTransformerEmbedder(Embedder):
    """Embedder para produccion basado en sentence-transformers."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers es requerido para SentenceTransformerEmbedder"
            ) from exc

        self._model = SentenceTransformer(model_name)

    def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        vectors = self._model.encode(texts, show_progress_bar=False)
        return [vector.tolist() for vector in vectors]
