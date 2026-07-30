from __future__ import annotations

import hashlib
import re
from dataclasses import replace
from pathlib import Path

from .chunking import chunk_document
from .config import Settings
from .gemini_clients import GeminiAnswerProvider, GeminiEmbeddingProvider
from .models import (
    AnswerResult,
    Document,
    IngestReport,
    SearchResult,
)
from .openai_clients import (
    AnswerProvider,
    EmbeddingProvider,
    OpenAIAnswerProvider,
    OpenAIEmbeddingProvider,
)
from .pdf_reader import parse_pdf, sha256_file
from .retrieval import HybridRetriever, bm25_scores
from .store import SQLiteStore


class RAGService:
    def __init__(
        self,
        settings: Settings,
        embedder: EmbeddingProvider | None = None,
        answerer: AnswerProvider | None = None,
        store: SQLiteStore | None = None,
    ) -> None:
        self.settings = settings
        self.store = store or SQLiteStore(settings.index_path)
        self.store.initialize()
        self._embedder = embedder
        self._answerer = answerer

    @classmethod
    def from_env(cls) -> "RAGService":
        return cls(Settings.from_env())

    @property
    def embedder(self) -> EmbeddingProvider:
        if self._embedder is None:
            if self.settings.provider == "openai":
                self._embedder = OpenAIEmbeddingProvider(
                    model=self.settings.embedding_model,
                    batch_size=self.settings.embedding_batch_size,
                )
            else:
                self._embedder = GeminiEmbeddingProvider(
                    model=self.settings.embedding_model,
                    batch_size=self.settings.embedding_batch_size,
                    dimensions=self.settings.gemini_embedding_dimensions,
                )
        return self._embedder

    @property
    def answerer(self) -> AnswerProvider:
        if self._answerer is None:
            if self.settings.provider == "openai":
                self._answerer = OpenAIAnswerProvider(
                    model=self.settings.chat_model,
                    reasoning_effort=self.settings.reasoning_effort,
                )
            else:
                self._answerer = GeminiAnswerProvider(
                    model=self.settings.chat_model
                )
        return self._answerer

    @property
    def embedding_signature(self) -> str:
        dimensions = (
            f":{self.settings.gemini_embedding_dimensions}"
            if self.settings.provider == "gemini"
            else ""
        )
        return (
            f"{self.settings.provider}:{self.settings.embedding_model}"
            f"{dimensions}"
        )

    def ingest_directory(
        self, pdf_dir: Path | None = None, reset: bool = False
    ) -> IngestReport:
        root = (pdf_dir or self.settings.pdf_dir).expanduser().resolve()
        if not root.exists():
            raise FileNotFoundError(f"PDF directory does not exist: {root}")
        if not root.is_dir():
            raise NotADirectoryError(f"Not a directory: {root}")
        if reset:
            self.store.reset()

        paths = sorted(
            path for path in root.rglob("*") if path.suffix.casefold() == ".pdf"
        )
        indexed_files = skipped_files = indexed_chunks = 0
        for path in paths:
            source = path.relative_to(root).as_posix()
            file_hash = sha256_file(path)
            if self.store.document_hash(source) == file_hash:
                skipped_files += 1
                continue

            parsed = parse_pdf(path, source=source)
            document_id = hashlib.sha256(
                f"{source}:{parsed.file_sha256}".encode("utf-8")
            ).hexdigest()[:24]
            document = Document(
                id=document_id,
                source=source,
                title=parsed.title,
                file_sha256=parsed.file_sha256,
                page_count=len(parsed.pages),
            )
            chunks = chunk_document(
                document=document,
                pages=parsed.pages,
                chunk_words=self.settings.chunk_words,
                overlap_words=self.settings.chunk_overlap_words,
            )
            vectors = self.embedder.embed_documents(
                [chunk.content for chunk in chunks]
            )
            embedded_chunks = [
                replace(chunk, embedding=tuple(vector))
                for chunk, vector in zip(chunks, vectors)
            ]
            indexed_chunks += self.store.save_document(
                document,
                embedded_chunks,
                embedding_model=self.embedding_signature,
            )
            indexed_files += 1

        return IngestReport(
            discovered_files=len(paths),
            indexed_files=indexed_files,
            skipped_files=skipped_files,
            indexed_chunks=indexed_chunks,
        )

    def _validate_index_model(self) -> None:
        indexed_model = self.store.embedding_model()
        if indexed_model and indexed_model != self.embedding_signature:
            raise RuntimeError(
                "Embedding model mismatch: index uses "
                f"{indexed_model!r}, config uses "
                f"{self.embedding_signature!r}. Re-ingest with --reset "
                "or restore the original model setting."
            )

    @staticmethod
    def _normalise_source_name(value: str) -> str:
        return " ".join(re.findall(r"[^\W_]+", value.casefold()))

    def _resolve_source(
        self,
        value: str,
        chunks,
        *,
        required: bool,
    ) -> str | None:
        normalized_value = self._normalise_source_name(value)
        candidates: dict[str, tuple[str, str]] = {}
        for chunk in chunks:
            candidates[chunk.source] = (
                self._normalise_source_name(
                    Path(chunk.source).stem
                ),
                self._normalise_source_name(chunk.title),
            )
        matches: list[tuple[int, str]] = []
        for source, identifiers in candidates.items():
            for identifier in identifiers:
                if len(identifier) >= 4 and identifier in normalized_value:
                    matches.append((len(identifier), source))
        if matches:
            return max(matches)[1]
        if required:
            available = ", ".join(sorted(candidates)) or "(none)"
            raise ValueError(
                f"Unknown source {value!r}. Available sources: {available}"
            )
        return None

    def search(
        self,
        query: str,
        top_k: int | None = None,
        source: str | None = None,
    ) -> list[SearchResult]:
        self._validate_index_model()
        chunks = self.store.load_chunks()
        resolved_source = self._resolve_source(
            source or query,
            chunks,
            required=source is not None,
        )
        if resolved_source:
            chunks = [
                chunk for chunk in chunks
                if chunk.source == resolved_source
            ]
        retriever = HybridRetriever(
            embedder=self.embedder,
            dense_weight=self.settings.dense_weight,
            mmr_lambda=self.settings.mmr_lambda,
        )
        return retriever.search(query, chunks, top_k or self.settings.top_k)

    def resolve_source(self, value: str) -> str | None:
        """Return the indexed PDF selected by a filename/title in user text."""
        return self._resolve_source(
            value,
            self.store.load_chunks(),
            required=False,
        )

    def keyword_search(
        self,
        query: str,
        top_k: int = 4,
        source: str | None = None,
    ) -> list[SearchResult]:
        """No-network retrieval fallback for quota/network failures."""
        chunks = self.store.load_chunks()
        if source:
            resolved_source = self._resolve_source(
                source,
                chunks,
                required=True,
            )
            chunks = [
                chunk
                for chunk in chunks
                if chunk.source == resolved_source
            ]
        scores = bm25_scores(query, chunks)
        ranked = sorted(
            zip(chunks, scores),
            key=lambda item: item[1],
            reverse=True,
        )[:top_k]
        return [
            SearchResult(
                chunk_id=chunk.id,
                source=chunk.source,
                title=chunk.title,
                page=chunk.page,
                content=chunk.content,
                score=round(score, 6),
                dense_score=0.0,
                keyword_score=round(score, 6),
                section=chunk.section,
            )
            for chunk, score in ranked
        ]

    def ask(
        self,
        question: str,
        top_k: int | None = None,
        source: str | None = None,
    ) -> AnswerResult:
        sources = self.search(question, top_k=top_k, source=source)
        answer, citations, grounded = self.answerer.answer(question, sources)
        return AnswerResult(
            answer=answer,
            grounded=grounded,
            citations=citations,
            retrieval=tuple(sources),
        )

    def health(self) -> dict[str, object]:
        stats = self.store.stats()
        return {
            "status": "ok",
            **stats,
            "configured_provider": self.settings.provider,
            "configured_chat_model": self.settings.chat_model,
            "configured_embedding_model": self.settings.embedding_model,
        }
