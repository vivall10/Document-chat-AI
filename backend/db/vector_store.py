from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import faiss
import numpy as np


@dataclass(frozen=True)
class RetrievedChunk:
    doc_id: str
    chunk_id: str
    text: str
    score: float
    page: Optional[int] = None


class VectorStoreManager:
    """
    Local FAISS vector store with per-document indices.

    Each document is stored under:
      {base_dir}/docs/{doc_id}/index.faiss
      {base_dir}/docs/{doc_id}/metadata.json
    """

    def __init__(self, base_dir: str) -> None:
        self.base_dir = Path(base_dir)
        self.docs_dir = self.base_dir / "docs"
        self.docs_dir.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()

    def _doc_dir(self, doc_id: str) -> Path:
        return self.docs_dir / doc_id

    def _index_path(self, doc_id: str) -> Path:
        return self._doc_dir(doc_id) / "index.faiss"

    def _metadata_path(self, doc_id: str) -> Path:
        return self._doc_dir(doc_id) / "metadata.json"

    @staticmethod
    def _normalize(vectors: np.ndarray) -> np.ndarray:
        # Cosine similarity via inner product: normalize to unit length.
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-12)
        return vectors / norms

    def list_documents(self) -> List[Dict[str, Any]]:
        docs: List[Dict[str, Any]] = []
        if not self.docs_dir.exists():
            return docs

        for doc_dir in sorted(self.docs_dir.iterdir()):
            if not doc_dir.is_dir():
                continue
            doc_id = doc_dir.name
            meta_path = self._metadata_path(doc_id)
            if not meta_path.exists():
                continue
            try:
                with meta_path.open("r", encoding="utf-8") as f:
                    meta = json.load(f)
                docs.append(
                    {
                        "doc_id": doc_id,
                        "filename": meta.get("__filename__", ""),
                        "chunks_added": meta.get("__chunks_added__", len(meta.get("chunks", []))),
                    }
                )
            except Exception:
                # If metadata is corrupted, skip this document.
                continue
        return docs

    def add_document(
        self,
        doc_id: str,
        *,
        filename: str,
        embeddings: np.ndarray,
        chunks: List[Dict[str, Any]],
    ) -> int:
        """
        Add a document worth of embeddings and chunk metadata.

        embeddings: shape (n_chunks, dim)
        chunks: list of dicts with at least {"text": str, "page": Optional[int]}
        """
        if embeddings.ndim != 2:
            raise ValueError("Embeddings must be a 2D array (n, dim).")
        if embeddings.shape[0] != len(chunks):
            raise ValueError("Embeddings row count must match chunks length.")

        vectors = embeddings.astype("float32", copy=False)
        vectors = self._normalize(vectors)

        new_chunks_added = 0
        with self._lock:
            doc_dir = self._doc_dir(doc_id)
            doc_dir.mkdir(parents=True, exist_ok=True)

            index_path = self._index_path(doc_id)
            metadata_path = self._metadata_path(doc_id)

            if index_path.exists() and metadata_path.exists():
                index = faiss.read_index(str(index_path))
                with metadata_path.open("r", encoding="utf-8") as f:
                    metadata_blob = json.load(f)
                existing_chunks: List[Dict[str, Any]] = metadata_blob.get("chunks", [])
                if index.d != vectors.shape[1]:
                    raise ValueError("Embedding dimension mismatch for existing index.")
            else:
                index = faiss.IndexFlatIP(vectors.shape[1])
                existing_chunks = []
                metadata_blob = {}

            start_idx = len(existing_chunks)
            # Append metadata entries in the same order as embeddings.
            appended: List[Dict[str, Any]] = []
            for i, chunk in enumerate(chunks):
                chunk_text = chunk.get("text", "")
                if not chunk_text:
                    continue
                entry = {
                    "chunk_id": f"{doc_id}_chunk_{start_idx + i}",
                    "text": chunk_text,
                    "page": chunk.get("page"),
                }
                appended.append(entry)

            if not appended:
                return 0

            # If we skipped empty chunk texts, keep embeddings aligned.
            # Rebuild vectors for appended chunk count.
            # (We assume empty chunks were not embedded, so this is mainly defensive.)
            if len(appended) != vectors.shape[0]:
                # Defensive fallback: require strict alignment.
                raise ValueError("Vector count must match non-empty chunks.")

            index.add(vectors)
            existing_chunks.extend(appended)
            new_chunks_added = len(appended)

            metadata_blob = {
                "__filename__": filename,
                "__chunks_added__": len(existing_chunks),
                "chunks": existing_chunks,
            }

            faiss.write_index(index, str(index_path))
            with metadata_path.open("w", encoding="utf-8") as f:
                json.dump(metadata_blob, f, ensure_ascii=False)

        return new_chunks_added

    def _search_one_doc(
        self, *, doc_id: str, query_vector: np.ndarray, top_k: int
    ) -> List[RetrievedChunk]:
        index_path = self._index_path(doc_id)
        metadata_path = self._metadata_path(doc_id)
        if not index_path.exists() or not metadata_path.exists():
            return []

        index = faiss.read_index(str(index_path))
        with metadata_path.open("r", encoding="utf-8") as f:
            metadata_blob = json.load(f)
        chunks = metadata_blob.get("chunks", [])

        # Normalize query for cosine similarity.
        q = self._normalize(query_vector.astype("float32", copy=False))
        if q.ndim == 1:
            q = q.reshape(1, -1)

        top_k = max(1, int(top_k))
        top_k = min(top_k, index.ntotal)
        if top_k <= 0:
            return []

        distances, indices = index.search(q, top_k)

        results: List[RetrievedChunk] = []
        for score, idx in zip(distances[0].tolist(), indices[0].tolist()):
            if idx < 0:
                continue
            if idx >= len(chunks):
                continue
            entry = chunks[idx]
            results.append(
                RetrievedChunk(
                    doc_id=doc_id,
                    chunk_id=entry["chunk_id"],
                    text=entry["text"],
                    score=float(score),
                    page=entry.get("page"),
                )
            )
        return results

    def search(
        self,
        *,
        query_vector: np.ndarray,
        top_k: int,
        doc_id: Optional[str] = None,
    ) -> List[RetrievedChunk]:
        """
        Similarity search across one or all documents.
        """
        top_k = max(1, int(top_k))
        if doc_id:
            return self._search_one_doc(doc_id=doc_id, query_vector=query_vector, top_k=top_k)

        all_results: List[RetrievedChunk] = []
        for doc_dir in sorted(self.docs_dir.iterdir()):
            if not doc_dir.is_dir():
                continue
            candidate_doc_id = doc_dir.name
            all_results.extend(
                self._search_one_doc(
                    doc_id=candidate_doc_id, query_vector=query_vector, top_k=top_k
                )
            )

        all_results.sort(key=lambda r: r.score, reverse=True)
        return all_results[:top_k]

    def get_doc_metadata(self, doc_id: str) -> Dict[str, Any]:
        metadata_path = self._metadata_path(doc_id)
        if not metadata_path.exists():
            raise FileNotFoundError(f"Document {doc_id} not found.")
        with metadata_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def get_chunks_for_doc(self, doc_id: str) -> List[Dict[str, Any]]:
        """
        Returns the stored metadata chunk entries for a document.
        """
        meta = self.get_doc_metadata(doc_id)
        return meta.get("chunks", [])

