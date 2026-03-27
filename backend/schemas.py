from __future__ import annotations

from typing import Optional, List

from pydantic import BaseModel, Field


class SourceChunk(BaseModel):
    doc_id: str
    chunk_id: str
    text: str
    score: float = Field(..., description="Cosine similarity score")
    page: Optional[int] = Field(None, description="Page number within the PDF if available")


class UploadResponse(BaseModel):
    doc_id: str
    filename: str
    chunks_added: int


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="User question")
    doc_id: Optional[str] = Field(None, description="Optional document to restrict search to")


class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceChunk]


class SummarizeRequest(BaseModel):
    doc_id: str
    max_chunks: int = Field(20, ge=1, le=200, description="Maximum chunks to include in the prompt")


class SummarizeResponse(BaseModel):
    summary: str
    sources: List[SourceChunk] = []

