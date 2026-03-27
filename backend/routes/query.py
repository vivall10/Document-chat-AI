from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from backend.schemas import QueryResponse, QueryRequest, SummarizeRequest, SummarizeResponse, SourceChunk
from backend.db.vector_store import RetrievedChunk, VectorStoreManager
from backend.services.embedding import EmbeddingService
from backend.services.generator import AnswerGenerator
from backend.services.retriever import Retriever


router = APIRouter()


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


def get_answer_generator(request: Request) -> AnswerGenerator:
    gen = getattr(request.app.state, "answer_generator", None)
    if gen is None:
        raise HTTPException(status_code=500, detail="Server not initialized.")
    return gen


def get_retriever(request: Request, embedding_service: EmbeddingService = None, vector_store: VectorStoreManager = None) -> Retriever:  # type: ignore[assignment]
    if embedding_service is None:
        embedding_service = get_embedding_service(request)
    if vector_store is None:
        vector_store = get_vector_store(request)
    return Retriever(embedding_service=embedding_service, vector_store=vector_store)


def _to_source_chunk(r: RetrievedChunk) -> SourceChunk:
    return SourceChunk(
        doc_id=r.doc_id,
        chunk_id=r.chunk_id,
        text=r.text,
        score=r.score,
        page=r.page,
    )


def _sse_format(event: str, data: Any) -> str:
    # SSE spec: each event ends with a blank line.
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/api/query", response_model=QueryResponse)
async def query_document(
    payload: QueryRequest,
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    vector_store: VectorStoreManager = Depends(get_vector_store),
    answer_generator: AnswerGenerator = Depends(get_answer_generator),
):
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Query is empty.")

    retriever = Retriever(embedding_service=embedding_service, vector_store=vector_store)
    retrieved = retriever.retrieve(question=payload.question, top_k=3, doc_id=payload.doc_id)
    answer = answer_generator.generate_answer(question=payload.question, chunks=retrieved)
    sources = [_to_source_chunk(r) for r in retrieved[:3]]

    return QueryResponse(answer=answer, sources=sources)


@router.get("/api/query/stream")
async def stream_query(
    question: str = Query(..., min_length=1),
    doc_id: Optional[str] = Query(None),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    vector_store: VectorStoreManager = Depends(get_vector_store),
    answer_generator: AnswerGenerator = Depends(get_answer_generator),
):
    """
    Stream SSE events:
      - `sources`: one-time payload with top chunks
      - `answer_delta`: incremental token deltas
      - `done`: end-of-stream
    """
    if not question.strip():
        raise HTTPException(status_code=400, detail="Query is empty.")

    retriever = Retriever(embedding_service=embedding_service, vector_store=vector_store)
    retrieved = retriever.retrieve(question=question, top_k=3, doc_id=doc_id)
    sources_payload = [_to_source_chunk(r).model_dump() for r in retrieved[:3]]

    async def event_gen() -> AsyncGenerator[str, None]:
        try:
            yield _sse_format("sources", sources_payload)

            # `stream_answer` is sync; iterate and yield tokens.
            for token in answer_generator.stream_answer(question=question, chunks=retrieved):
                yield _sse_format("answer_delta", {"delta": token})
                # Let the event loop breathe; helps responsiveness.
                await asyncio.sleep(0)

            yield _sse_format("done", {"ok": True})
        except Exception as e:
            yield _sse_format("error", {"message": str(e)})
            yield _sse_format("done", {"ok": False})

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/api/summarize", response_model=SummarizeResponse)
async def summarize_document(
    payload: SummarizeRequest,
    vector_store: VectorStoreManager = Depends(get_vector_store),
    answer_generator: AnswerGenerator = Depends(get_answer_generator),
):
    """
    Bonus endpoint: summarize a document using its stored chunks.
    """
    doc_meta = vector_store.get_doc_metadata(payload.doc_id)
    filename = doc_meta.get("__filename__", payload.doc_id)
    chunk_entries = vector_store.get_chunks_for_doc(payload.doc_id)

    if not chunk_entries:
        raise HTTPException(status_code=404, detail="Document has no chunks.")

    # Convert stored chunk metadata into RetrievedChunk-like objects.
    chunks: List[RetrievedChunk] = []
    for entry in chunk_entries[: payload.max_chunks]:
        chunks.append(
            RetrievedChunk(
                doc_id=payload.doc_id,
                chunk_id=str(entry.get("chunk_id", "")),
                text=str(entry.get("text", "")),
                score=0.0,
                page=entry.get("page"),
            )
        )

    summary = answer_generator.generate_summary(doc_title=filename, chunks=chunks)
    sources = [_to_source_chunk(c) for c in chunks[:3]]
    return SummarizeResponse(summary=summary, sources=sources)

