from __future__ import annotations

from typing import List


def chunk_words(text: str, *, chunk_size: int, overlap: int) -> List[str]:
    """
    Split `text` into overlapping word-based chunks.

    chunk_size / overlap are in words (as requested: chunk_size=500, overlap=50).
    """
    words = (text or "").split()
    if not words:
        return []

    chunk_size = max(1, int(chunk_size))
    overlap = max(0, int(overlap))

    # Ensure overlap < chunk_size to avoid infinite loops.
    overlap = min(overlap, chunk_size - 1)

    chunks: List[str] = []
    start = 0
    while start < len(words):
        end = min(len(words), start + chunk_size)
        chunk = " ".join(words[start:end]).strip()
        if chunk:
            chunks.append(chunk)

        if end >= len(words):
            break

        # Move window forward with overlap.
        start = end - overlap
    return chunks

