from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Sequence

from .models import Chunk, SearchResult
from .openai_clients import EmbeddingProvider


_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)
_SUMMARY_CUES = {
    "summary",
    "summarize",
    "overview",
    "main content",
    "main contribution",
    "main result",
    "proposed",
    "nội dung chính",
    "tổng hợp",
    "tóm tắt",
    "đóng góp chính",
    "kết quả chính",
    "đề xuất",
}


def tokenize(text: str) -> list[str]:
    return [token.casefold() for token in _TOKEN_RE.findall(text)]


def _is_summary_query(query: str) -> bool:
    lowered = query.casefold()
    return any(cue in lowered for cue in _SUMMARY_CUES)


def section_adjustment(query: str, section: str) -> float:
    normalized = section.casefold()
    if "reference" in normalized or "bibliograph" in normalized:
        return -0.30
    if any(
        marker in normalized
        for marker in (
            "acknowledg",
            "abbreviation",
            "author contribution",
            "funding",
            "data availability",
            "availability of data",
            "declaration",
            "ethics approval",
            "consent for publication",
            "competing interest",
            "publisher",
        )
    ):
        return -0.28
    if normalized in {"front matter", "unknown"}:
        return -0.18
    if not _is_summary_query(query):
        return 0.0
    if "abstract" in normalized:
        return 0.24
    if "conclusion" in normalized:
        return 0.18
    if "result" in normalized or "discussion" in normalized:
        return 0.12
    if "method" in normalized or "model" in normalized:
        return 0.10
    if "introduction" in normalized:
        return 0.08
    return 0.0


def cosine_similarity(
    left: Sequence[float], right: Sequence[float]
) -> float:
    if len(left) != len(right):
        raise ValueError(
            f"Embedding dimension mismatch: {len(left)} != {len(right)}"
        )
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def bm25_scores(query: str, chunks: Sequence[Chunk]) -> list[float]:
    if not chunks:
        return []
    query_terms = tokenize(query)
    if not query_terms:
        return [0.0] * len(chunks)

    documents = [tokenize(chunk.content) for chunk in chunks]
    frequencies = [Counter(document) for document in documents]
    average_length = sum(map(len, documents)) / len(documents) or 1.0
    document_frequency = Counter()
    for document in documents:
        document_frequency.update(set(document))

    k1, b = 1.5, 0.75
    raw_scores: list[float] = []
    for document, frequency in zip(documents, frequencies):
        score = 0.0
        for term in query_terms:
            matches = frequency[term]
            if not matches:
                continue
            df = document_frequency[term]
            idf = math.log(
                1.0 + (len(documents) - df + 0.5) / (df + 0.5)
            )
            denominator = matches + k1 * (
                1.0 - b + b * len(document) / average_length
            )
            score += idf * matches * (k1 + 1.0) / denominator
        raw_scores.append(score)

    maximum = max(raw_scores, default=0.0)
    return (
        [score / maximum for score in raw_scores]
        if maximum > 0
        else raw_scores
    )


@dataclass(frozen=True)
class _Candidate:
    chunk: Chunk
    combined: float
    dense: float
    keyword: float


class HybridRetriever:
    def __init__(
        self,
        embedder: EmbeddingProvider,
        dense_weight: float = 0.76,
        mmr_lambda: float = 0.78,
    ) -> None:
        if not 0 <= dense_weight <= 1:
            raise ValueError("dense_weight must be between 0 and 1")
        if not 0 <= mmr_lambda <= 1:
            raise ValueError("mmr_lambda must be between 0 and 1")
        self.embedder = embedder
        self.dense_weight = dense_weight
        self.mmr_lambda = mmr_lambda

    def search(
        self, query: str, chunks: Sequence[Chunk], top_k: int
    ) -> list[SearchResult]:
        if not query.strip():
            raise ValueError("query cannot be empty")
        if top_k <= 0:
            raise ValueError("top_k must be greater than zero")
        if not chunks:
            return []

        query_vector = self.embedder.embed_query(query)
        keyword_scores = bm25_scores(query, chunks)
        candidates = []
        for chunk, keyword_score in zip(chunks, keyword_scores):
            dense_score = cosine_similarity(query_vector, chunk.embedding)
            dense_unit = (dense_score + 1.0) / 2.0
            combined = (
                self.dense_weight * dense_unit
                + (1.0 - self.dense_weight) * keyword_score
                + section_adjustment(query, chunk.section)
            )
            if chunk.word_count < 20:
                combined -= 0.25
            elif chunk.word_count < 60:
                combined -= 0.12
            candidates.append(
                _Candidate(
                    chunk=chunk,
                    combined=combined,
                    dense=dense_score,
                    keyword=keyword_score,
                )
            )

        pool_size = min(len(candidates), max(top_k * 5, 20))
        pool = sorted(
            candidates, key=lambda item: item.combined, reverse=True
        )[:pool_size]
        selected: list[_Candidate] = []
        section_counts: Counter[str] = Counter()
        per_section_limit = 2 if _is_summary_query(query) else 3
        while pool and len(selected) < min(top_k, len(candidates)):
            eligible = [
                candidate
                for candidate in pool
                if section_counts[candidate.chunk.section] < per_section_limit
            ]
            if not eligible:
                eligible = pool
            if not selected:
                choice = eligible[0]
            else:
                choice = max(
                    eligible,
                    key=lambda candidate: (
                        self.mmr_lambda * candidate.combined
                        - (1.0 - self.mmr_lambda)
                        * max(
                            cosine_similarity(
                                candidate.chunk.embedding,
                                selected_item.chunk.embedding,
                            )
                            for selected_item in selected
                        )
                    ),
                )
            selected.append(choice)
            section_counts[choice.chunk.section] += 1
            pool.remove(choice)

        return [
            SearchResult(
                chunk_id=item.chunk.id,
                source=item.chunk.source,
                title=item.chunk.title,
                page=item.chunk.page,
                content=item.chunk.content,
                score=round(item.combined, 6),
                dense_score=round(item.dense, 6),
                keyword_score=round(item.keyword, 6),
                section=item.chunk.section,
                line_start=item.chunk.line_start,
                line_end=item.chunk.line_end,
            )
            for item in selected
        ]
