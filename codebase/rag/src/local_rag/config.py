from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from exc
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value


def _select_provider() -> str:
    requested = os.getenv("RAG_PROVIDER", "auto").strip().casefold()
    if requested not in {"auto", "openai", "gemini"}:
        raise ValueError(
            "RAG_PROVIDER must be one of: auto, openai, gemini"
        )
    if requested != "auto":
        return requested
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        return "gemini"
    # Keep health/config commands usable without credentials. API-backed
    # operations will emit a precise missing-Gemini-key error.
    return "gemini"


@dataclass(frozen=True)
class Settings:
    index_path: Path
    pdf_dir: Path
    provider: str
    chat_model: str
    embedding_model: str
    reasoning_effort: str
    gemini_embedding_dimensions: int
    top_k: int
    chunk_words: int
    chunk_overlap_words: int
    embedding_batch_size: int
    dense_weight: float = 0.76
    mmr_lambda: float = 0.78

    @classmethod
    def from_env(cls) -> "Settings":
        provider = _select_provider()
        default_chat_model = (
            "gpt-5.6-terra"
            if provider == "openai"
            else "gemini-3.6-flash"
        )
        default_embedding_model = (
            "text-embedding-3-large"
            if provider == "openai"
            else "gemini-embedding-2"
        )
        settings = cls(
            index_path=Path(os.getenv("RAG_INDEX_PATH", ".rag/index.sqlite3")),
            pdf_dir=Path(os.getenv("RAG_PDF_DIR", "data/papers")),
            provider=provider,
            chat_model=os.getenv("RAG_CHAT_MODEL", default_chat_model),
            embedding_model=os.getenv(
                "RAG_EMBEDDING_MODEL", default_embedding_model
            ),
            reasoning_effort=os.getenv("RAG_REASONING_EFFORT", "low"),
            gemini_embedding_dimensions=_positive_int(
                "RAG_GEMINI_EMBEDDING_DIMENSIONS", 768
            ),
            top_k=_positive_int("RAG_TOP_K", 6),
            chunk_words=_positive_int("RAG_CHUNK_WORDS", 360),
            chunk_overlap_words=_positive_int(
                "RAG_CHUNK_OVERLAP_WORDS", 70
            ),
            embedding_batch_size=_positive_int(
                "RAG_EMBEDDING_BATCH_SIZE", 64
            ),
        )
        if settings.chunk_overlap_words >= settings.chunk_words:
            raise ValueError(
                "RAG_CHUNK_OVERLAP_WORDS must be smaller than RAG_CHUNK_WORDS"
            )
        if settings.gemini_embedding_dimensions not in {128, 256, 512, 768, 1536, 3072}:
            raise ValueError(
                "RAG_GEMINI_EMBEDDING_DIMENSIONS must be one of "
                "128, 256, 512, 768, 1536, 3072"
            )
        return settings
