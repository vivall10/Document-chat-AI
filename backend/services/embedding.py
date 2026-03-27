from __future__ import annotations

from typing import List, Optional

import numpy as np
from sentence_transformers import SentenceTransformer


class EmbeddingService:
    """
    SentenceTransformers embedding wrapper.
    """

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._model = SentenceTransformer(model_name)

    def embed_texts(self, texts: List[str], *, batch_size: int = 32) -> np.ndarray:
        """
        Embed a list of texts into a float32 matrix of shape (n, dim).
        """
        if not texts:
            return np.zeros((0, 0), dtype="float32")

        vectors = self._model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=False,
            show_progress_bar=False,
        )
        # SentenceTransformers can return list or ndarray depending on backend.
        vectors_np = np.asarray(vectors, dtype="float32")
        return vectors_np

    def embed_query(self, question: str) -> np.ndarray:
        """
        Embed a single query. Returns shape (1, dim).
        """
        vectors = self.embed_texts([question])
        if vectors.shape[0] != 1:
            raise RuntimeError("Unexpected embedding output shape for query.")
        return vectors

