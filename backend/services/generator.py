from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from openai import OpenAI

from backend.db.vector_store import RetrievedChunk


QUESTION_SYSTEM_PROMPT = (
    "Answer the question using ONLY the provided context. "
    "If the answer is not found, say 'I don't know'."
)


@dataclass(frozen=True)
class LLMConfig:
    api_key: str
    model: str


class LLMClient:
    """
    OpenAI API abstraction to allow swapping LLM providers later.
    """

    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self._client = OpenAI(api_key=config.api_key)

    def generate_chat_completion(self, *, messages: List[Dict[str, str]]) -> str:
        resp = self._client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=0,
        )
        return resp.choices[0].message.content or ""

    def stream_chat_completion(self, *, messages: List[Dict[str, str]]) -> Iterable[str]:
        stream = self._client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=0,
            stream=True,
        )
        for event in stream:
            try:
                delta = event.choices[0].delta
                token = getattr(delta, "content", None)
            except Exception:
                token = None
            if token:
                yield token


class AnswerGenerator:
    def __init__(self, *, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def build_context(self, chunks: List[RetrievedChunk]) -> str:
        """
        Build a deterministic context string for the prompt.
        """
        parts: List[str] = []
        for i, ch in enumerate(chunks, start=1):
            label = f"[Source {i} | doc_id={ch.doc_id} | page={ch.page}]"
            parts.append(f"{label}\n{ch.text}")
        return "\n\n---\n\n".join(parts)

    def _messages_for_answer(self, *, question: str, context: str) -> List[Dict[str, str]]:
        prompt = (
            f"Question:\n{question}\n\n"
            f"Context:\n{context}\n\n"
            "Answer:"
        )
        return [
            {"role": "system", "content": QUESTION_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

    def generate_answer(self, *, question: str, chunks: List[RetrievedChunk]) -> str:
        context = self.build_context(chunks)
        messages = self._messages_for_answer(question=question, context=context)
        return self.llm_client.generate_chat_completion(messages=messages).strip()

    def stream_answer(self, *, question: str, chunks: List[RetrievedChunk]) -> Iterable[str]:
        context = self.build_context(chunks)
        messages = self._messages_for_answer(question=question, context=context)
        return self.llm_client.stream_chat_completion(messages=messages)

    def generate_summary(
        self,
        *,
        doc_title: str,
        chunks: List[RetrievedChunk],
        max_input_chars: int = 12000,
    ) -> str:
        """
        Summarize a document from retrieved chunks.

        Note: this endpoint is best-effort and uses a limited prompt size.
        """
        context_parts: List[str] = []
        total = 0
        used = 0
        for ch in chunks:
            addition = ch.text
            if total + len(addition) > max_input_chars and used > 0:
                break
            context_parts.append(addition)
            total += len(addition)
            used += 1
        context = "\n\n".join(context_parts)

        system = (
            "You are a helpful assistant that summarizes documents accurately. "
            "If the context is insufficient, say 'I don't know'."
        )
        prompt = f"Document title: {doc_title}\n\nContext:\n{context}\n\nWrite a concise summary."
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]
        return self.llm_client.generate_chat_completion(messages=messages).strip()

