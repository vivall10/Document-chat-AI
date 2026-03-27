from __future__ import annotations

from typing import List, Dict, Any


def extract_pdf_text_by_page(pdf_path: str) -> List[str]:
    """
    Extract plain text from each page of a PDF using PyMuPDF.
    """
    import fitz  # PyMuPDF

    doc = fitz.open(pdf_path)
    pages: List[str] = []
    try:
        for i in range(len(doc)):
            page = doc.load_page(i)
            text = page.get_text("text") or ""
            pages.append(text.strip())
    finally:
        doc.close()
    return pages


def extract_and_chunk_pdf(
    pdf_path: str,
    *,
    chunk_size: int,
    overlap: int,
) -> List[Dict[str, Any]]:
    """
    Extract text page-by-page and chunk within each page.

    Returns a list of dicts:
      - text: chunk text
      - page: 0-based page index
    """
    from .chunking import chunk_words

    pages = extract_pdf_text_by_page(pdf_path)
    results: List[Dict[str, Any]] = []
    for page_idx, page_text in enumerate(pages):
        if not page_text.strip():
            continue

        chunks = chunk_words(page_text, chunk_size=chunk_size, overlap=overlap)
        for chunk_idx, chunk in enumerate(chunks):
            results.append(
                {
                    "text": chunk,
                    "page": page_idx,
                    "chunk_idx_in_page": chunk_idx,
                }
            )
    return results

