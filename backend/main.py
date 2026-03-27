from __future__ import annotations

import os
from typing import List

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.db.vector_store import VectorStoreManager
from backend.routes.query import router as query_router
from backend.routes.upload import router as upload_router
from backend.services.embedding import EmbeddingService
from backend.services.generator import AnswerGenerator, LLMClient, LLMConfig


def _parse_frontend_origins(value: str) -> List[str]:
    if not value.strip():
        return ["http://localhost:5173", "http://localhost:3000"]
    return [v.strip() for v in value.split(",") if v.strip()]


load_dotenv()

app = FastAPI(title="AI Document Assistant (RAG)")

frontend_origins = _parse_frontend_origins(os.getenv("FRONTEND_ORIGINS", ""))

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    embedding_model = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    vector_store_dir = os.getenv("VECTOR_STORE_DIR", "backend/db/data")

    # Initialize embedding + FAISS store once.
    app.state.embedding_service = EmbeddingService(embedding_model)
    app.state.vector_store = VectorStoreManager(vector_store_dir)

    # Initialize LLM only if API key is available.
    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
    openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
    if openai_api_key:
        llm_client = LLMClient(LLMConfig(api_key=openai_api_key, model=openai_model))
        app.state.answer_generator = AnswerGenerator(llm_client=llm_client)
    else:
        app.state.answer_generator = None


@app.get("/health")
async def health():
    docs = []
    try:
        store: VectorStoreManager = app.state.vector_store
        docs = store.list_documents()
    except Exception:
        docs = []
    return {"status": "ok", "documents": docs}


app.include_router(upload_router)
app.include_router(query_router)

