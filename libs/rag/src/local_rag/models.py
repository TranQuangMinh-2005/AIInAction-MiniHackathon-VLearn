from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class PDFPage:
    number: int
    text: str


@dataclass(frozen=True)
class Document:
    id: str
    source: str
    title: str
    file_sha256: str
    page_count: int


@dataclass(frozen=True)
class Chunk:
    id: str
    document_id: str
    source: str
    title: str
    page: int
    content: str
    word_count: int
    embedding: tuple[float, ...] = field(default_factory=tuple)
    section: str = "Unknown"
    line_start: int = 0
    line_end: int = 0


@dataclass(frozen=True)
class SearchResult:
    chunk_id: str
    source: str
    title: str
    page: int
    content: str
    score: float
    dense_score: float
    keyword_score: float
    section: str = "Unknown"
    line_start: int = 0
    line_end: int = 0

    def to_dict(self, include_content: bool = True) -> dict[str, Any]:
        value = asdict(self)
        if not include_content:
            value.pop("content")
        return value


@dataclass(frozen=True)
class Citation:
    label: str
    title: str
    source: str
    page: int
    quote: str
    claim: str = ""
    entailed: bool = False
    entailment_reason: str = ""
    line_start: int = 0
    line_end: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AnswerResult:
    answer: str
    grounded: bool
    citations: tuple[Citation, ...]
    retrieval: tuple[SearchResult, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "grounded": self.grounded,
            "citations": [item.to_dict() for item in self.citations],
            "retrieval": [
                item.to_dict(include_content=False) for item in self.retrieval
            ],
        }


@dataclass(frozen=True)
class IngestReport:
    discovered_files: int
    indexed_files: int
    skipped_files: int
    indexed_chunks: int

    def to_dict(self) -> dict[str, int]:
        return asdict(self)
