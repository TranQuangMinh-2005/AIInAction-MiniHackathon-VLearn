from __future__ import annotations

import os
import sys
import time
from typing import Sequence

from .models import Citation, SearchResult
from .grounding import (
    apply_verification,
    build_verification_prompt,
    claim_references,
    parse_json_object,
)
from .openai_clients import (
    GROUNDING_SYSTEM_PROMPT,
    build_grounded_prompt,
)


def _gemini_client():
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing. Export it in the current terminal; "
            "never put a real key in source control. Alternatively set "
            "RAG_PROVIDER=openai and OPENAI_API_KEY."
        )
    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError(
            "google-genai is required. Install the project with: "
            'python -m pip install -e ".[dev]"'
        ) from exc
    return genai.Client(api_key=api_key)


def _request_with_retry(
    request,
    *,
    operation: str,
    initial_delay_seconds: int,
):
    delay_seconds = initial_delay_seconds
    max_attempts = 5
    retryable_codes = {429, 500, 503, 504}
    for attempt in range(1, max_attempts + 1):
        try:
            return request()
        except Exception as exc:
            error_code = getattr(
                exc, "code", getattr(exc, "status_code", None)
            )
            if error_code not in retryable_codes or attempt == max_attempts:
                raise
            print(
                f"Gemini {operation} temporarily unavailable "
                f"(HTTP {error_code}); retrying in {delay_seconds}s "
                f"(attempt {attempt + 1}/{max_attempts})...",
                file=sys.stderr,
            )
            time.sleep(delay_seconds)
            delay_seconds = min(delay_seconds * 2, 60)
    raise RuntimeError("Unreachable Gemini retry state")


class GeminiEmbeddingProvider:
    def __init__(
        self,
        model: str,
        batch_size: int = 64,
        dimensions: int = 768,
    ) -> None:
        self.model = model
        self.batch_size = batch_size
        self.dimensions = dimensions
        self.client = _gemini_client()

    def _request_batch(self, contents, task_type: str):
        return _request_with_retry(
            lambda: self.client.models.embed_content(
                    model=self.model,
                    contents=contents,
                    config={
                        "task_type": task_type,
                        "output_dimensionality": self.dimensions,
                    },
                ),
            operation="embedding",
            initial_delay_seconds=20,
        )

    def _embed(
        self, texts: Sequence[str], task_type: str
    ) -> list[list[float]]:
        if not texts:
            return []
        all_vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = list(texts[start : start + self.batch_size])
            # A list[str] is treated as parts of one multimodal content by
            # gemini-embedding-2. Explicit Content objects request one vector
            # per chunk, which is what a vector index needs.
            from google.genai import types

            contents = [
                types.Content(parts=[types.Part(text=text)])
                for text in batch
            ]
            response = self._request_batch(contents, task_type)
            all_vectors.extend(
                [list(item.values or []) for item in response.embeddings]
            )
        if len(all_vectors) != len(texts) or any(
            not vector for vector in all_vectors
        ):
            raise RuntimeError(
                "Gemini Embedding API returned an unexpected result"
            )
        return all_vectors

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return self._embed(texts, "RETRIEVAL_DOCUMENT")

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], "RETRIEVAL_QUERY")[0]


class GeminiAnswerProvider:
    def __init__(self, model: str) -> None:
        self.model = model
        self.client = _gemini_client()

    def answer(
        self, question: str, sources: Sequence[SearchResult]
    ) -> tuple[str, tuple[Citation, ...], bool]:
        if not sources:
            text = (
                "Không tìm thấy bằng chứng phù hợp trong các tài liệu đã nạp."
            )
            return text, (), False

        response = _request_with_retry(
            lambda: self.client.models.generate_content(
                model=self.model,
                contents=build_grounded_prompt(question, sources),
                config={"system_instruction": GROUNDING_SYSTEM_PROMPT},
            ),
            operation="answer generation",
            initial_delay_seconds=10,
        )
        text = (response.text or "").strip()
        if not text:
            raise RuntimeError("Gemini returned an empty answer")
        references = claim_references(text, sources)
        if not references:
            return text, (), False
        audit = _request_with_retry(
            lambda: self.client.models.generate_content(
                model=self.model,
                contents=build_verification_prompt(
                    text, references, sources
                ),
                config={
                    "system_instruction": (
                        "You are a strict factual-grounding auditor."
                    ),
                    "response_mime_type": "application/json",
                },
            ),
            operation="grounding audit",
            initial_delay_seconds=10,
        )
        return apply_verification(
            text,
            sources,
            parse_json_object(audit.text or ""),
        )
