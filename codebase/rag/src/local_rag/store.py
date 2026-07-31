from __future__ import annotations

import json
import math
import sqlite3
import struct
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Iterator

from .models import Chunk, Document


def _pack_vector(vector: tuple[float, ...]) -> bytes:
    return struct.pack(f"<{len(vector)}f", *vector)


def _unpack_vector(blob: bytes, dimensions: int) -> tuple[float, ...]:
    if dimensions <= 0:
        return ()
    return struct.unpack(f"<{dimensions}f", blob)


def _vector_norm(vector: tuple[float, ...]) -> float:
    return math.sqrt(sum(value * value for value in vector))


class SQLiteStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    source TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    file_sha256 TEXT NOT NULL,
                    page_count INTEGER NOT NULL,
                    indexed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    title TEXT NOT NULL,
                    page INTEGER NOT NULL,
                    section TEXT NOT NULL DEFAULT 'Unknown',
                    content TEXT NOT NULL,
                    word_count INTEGER NOT NULL,
                    line_start INTEGER NOT NULL DEFAULT 0,
                    line_end INTEGER NOT NULL DEFAULT 0,
                    embedding BLOB NOT NULL,
                    dimensions INTEGER NOT NULL,
                    norm REAL NOT NULL,
                    FOREIGN KEY(document_id) REFERENCES documents(id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_chunks_document
                    ON chunks(document_id);
                """
            )
            columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(chunks)"
                ).fetchall()
            }
            if "section" not in columns:
                connection.execute(
                    "ALTER TABLE chunks ADD COLUMN section TEXT NOT NULL "
                    "DEFAULT 'Unknown'"
                )
            if "line_start" not in columns:
                connection.execute(
                    "ALTER TABLE chunks ADD COLUMN line_start INTEGER "
                    "NOT NULL DEFAULT 0"
                )
            if "line_end" not in columns:
                connection.execute(
                    "ALTER TABLE chunks ADD COLUMN line_end INTEGER "
                    "NOT NULL DEFAULT 0"
                )

    def reset(self) -> None:
        self.initialize()
        with self._connect() as connection:
            connection.execute("DELETE FROM chunks")
            connection.execute("DELETE FROM documents")
            connection.execute("DELETE FROM metadata")

    def document_hash(self, source: str) -> str | None:
        self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT file_sha256 FROM documents WHERE source = ?", (source,)
            ).fetchone()
        return str(row["file_sha256"]) if row else None

    def save_document(
        self,
        document: Document,
        chunks: Iterable[Chunk],
        embedding_model: str,
    ) -> int:
        chunk_list = list(chunks)
        if any(not chunk.embedding for chunk in chunk_list):
            raise ValueError("Every chunk must contain an embedding")
        dimensions = {len(chunk.embedding) for chunk in chunk_list}
        if len(dimensions) > 1:
            raise ValueError("All embeddings in a document must share dimensions")

        self.initialize()
        with self._connect() as connection:
            previous = connection.execute(
                "SELECT id FROM documents WHERE source = ?", (document.source,)
            ).fetchone()
            if previous:
                connection.execute(
                    "DELETE FROM documents WHERE source = ?", (document.source,)
                )
            connection.execute(
                """
                INSERT INTO documents
                    (id, source, title, file_sha256, page_count)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    document.id,
                    document.source,
                    document.title,
                    document.file_sha256,
                    document.page_count,
                ),
            )
            connection.executemany(
                """
                INSERT INTO chunks
                    (id, document_id, source, title, page, section, content,
                     word_count, line_start, line_end, embedding, dimensions,
                     norm)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        chunk.id,
                        chunk.document_id,
                        chunk.source,
                        chunk.title,
                        chunk.page,
                        chunk.section,
                        chunk.content,
                        chunk.word_count,
                        chunk.line_start,
                        chunk.line_end,
                        _pack_vector(chunk.embedding),
                        len(chunk.embedding),
                        _vector_norm(chunk.embedding),
                    )
                    for chunk in chunk_list
                ],
            )
            connection.execute(
                """
                INSERT INTO metadata (key, value) VALUES ('embedding_model', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (embedding_model,),
            )
        return len(chunk_list)

    def load_chunks(self) -> list[Chunk]:
        self.initialize()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, document_id, source, title, page, section, content,
                       word_count, line_start, line_end, embedding, dimensions
                FROM chunks
                ORDER BY source, page, id
                """
            ).fetchall()
        return [
            Chunk(
                id=row["id"],
                document_id=row["document_id"],
                source=row["source"],
                title=row["title"],
                page=row["page"],
                section=row["section"],
                content=row["content"],
                word_count=row["word_count"],
                embedding=_unpack_vector(row["embedding"], row["dimensions"]),
                line_start=row["line_start"],
                line_end=row["line_end"],
            )
            for row in rows
        ]

    def embedding_model(self) -> str | None:
        self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT value FROM metadata WHERE key = 'embedding_model'"
            ).fetchone()
        return str(row["value"]) if row else None

    def stats(self) -> dict[str, int | str | None]:
        self.initialize()
        with self._connect() as connection:
            documents = connection.execute(
                "SELECT COUNT(*) AS count FROM documents"
            ).fetchone()["count"]
            chunks = connection.execute(
                "SELECT COUNT(*) AS count FROM chunks"
            ).fetchone()["count"]
        return {
            "documents": int(documents),
            "chunks": int(chunks),
            "embedding_model": self.embedding_model(),
        }

    def list_documents(self) -> list[dict[str, int | str]]:
        self.initialize()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT source, title, page_count, indexed_at
                FROM documents
                ORDER BY indexed_at, source
                """
            ).fetchall()
        return [
            {
                "source": str(row["source"]),
                "title": str(row["title"]),
                "page_count": int(row["page_count"]),
                "indexed_at": str(row["indexed_at"]),
            }
            for row in rows
        ]
