from __future__ import annotations

import os
import tempfile
import uuid
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

from backend.schemas import UploadResponse
from backend.services.embedding import EmbeddingService
from backend.db.vector_store import VectorStoreManager
from backend.utils.pdf_loader import extract_and_chunk_pdf


router = APIRouter()

CHUNK_SIZE_WORDS = 500
CHUNK_OVERLAP_WORDS = 50


def _require_pdf(file: UploadFile) -> None:
    content_type = (file.content_type or "").lower()
    filename = (file.filename or "").lower()
    if "pdf" in content_type:
        return
    if filename.endswith(".pdf"):
        return
    raise HTTPException(status_code=400, detail="Please upload a PDF file.")


def get_embedding_service(request: Request) -> EmbeddingService:
    svc = getattr(request.app.state, "embedding_service", None)
    if svc is None:
        raise HTTPException(status_code=500, detail="Server not initialized.")
    return svc


def get_vector_store(request: Request) -> VectorStoreManager:
    store = getattr(request.app.state, "vector_store", None)
    if store is None:
        raise HTTPException(status_code=500, detail="Server not initialized.")
    return store


@router.post("/api/upload", response_model=UploadResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    vector_store: VectorStoreManager = Depends(get_vector_store),
):
    """
    Upload a PDF, extract text, chunk it, embed chunks, and store vectors in FAISS.
    """
    if embedding_service is None or vector_store is None:
        # Defensive: dependencies should have already verified initialization.
        raise HTTPException(status_code=500, detail="Server not initialized.")

    _require_pdf(file)

    doc_id = str(uuid.uuid4())
    filename = file.filename or "document.pdf"

    # Save to a temporary location for PDF parsing.
    suffix = ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        temp_path = tmp.name
        content = await file.read()
        tmp.write(content)

    try:
        chunk_dicts = extract_and_chunk_pdf(
            temp_path,
            chunk_size=CHUNK_SIZE_WORDS,
            overlap=CHUNK_OVERLAP_WORDS,
        )

        if not chunk_dicts:
            raise HTTPException(status_code=400, detail="No text found in the PDF.")

        texts: List[str] = [c["text"] for c in chunk_dicts]
        embeddings = embedding_service.embed_texts(texts)

        chunks_added = vector_store.add_document(
            doc_id,
            filename=filename,
            embeddings=embeddings,
            chunks=chunk_dicts,
        )

        return UploadResponse(doc_id=doc_id, filename=filename, chunks_added=chunks_added)
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass

