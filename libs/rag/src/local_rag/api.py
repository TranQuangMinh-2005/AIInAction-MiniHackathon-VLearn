from __future__ import annotations

from functools import lru_cache
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .service import RAGService


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=6, ge=1, le=12)
    source: str | None = Field(default=None, max_length=500)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=6, ge=1, le=12)
    source: str | None = Field(default=None, max_length=500)


@lru_cache(maxsize=1)
def get_service() -> RAGService:
    return RAGService.from_env()


app = FastAPI(
    title="Local Paper RAG",
    version="0.1.0",
    description="Local scientific-PDF retrieval and grounded Q&A for Agents.",
)


@app.get("/health")
def health() -> dict[str, object]:
    return get_service().health()


@app.post("/search")
def search(request: SearchRequest) -> dict[str, Any]:
    try:
        results = get_service().search(
            request.query, request.top_k, source=request.source
        )
        return {"results": [result.to_dict() for result in results]}
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/ask")
def ask(request: AskRequest) -> dict[str, Any]:
    try:
        return get_service().ask(
            request.question, request.top_k, source=request.source
        ).to_dict()
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
