from __future__ import annotations

from typing import List, Optional

import numpy as np

from backend.db.vector_store import RetrievedChunk, VectorStoreManager
from backend.services.embedding import EmbeddingService


class Retriever:
    """
    Retrieval component: embed question -> similarity search -> top-k chunks.
    """

    def __init__(self, *, embedding_service: EmbeddingService, vector_store: VectorStoreManager) -> None:
        self.embedding_service = embedding_service
        self.vector_store = vector_store

    def retrieve(
        self,
        *,
        question: str,
        top_k: int = 3,
        doc_id: Optional[str] = None,
    ) -> List[RetrievedChunk]:
        if not question.strip():
            return []

        query_vector: np.ndarray = self.embedding_service.embed_query(question)
        return self.vector_store.search(query_vector=query_vector, top_k=top_k, doc_id=doc_id)

