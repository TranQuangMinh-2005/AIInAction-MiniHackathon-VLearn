"""Adapters that turn scientific-paper tools into Agent-ready text."""

from __future__ import annotations

from functools import lru_cache
import re
from typing import Any

from agent.config import load_environment
from local_rag.service import RAGService

from agent.tools.paper.paper import arxiv_search

load_environment()

_ARXIV_CACHE: dict[
    str, tuple[str, list[str], list[dict[str, Any]]]
] = {}


@lru_cache(maxsize=1)
def _paper_service() -> RAGService:
    return RAGService.from_env()


def build_arxiv_query(question: str) -> str:
    """Strip Vietnamese/English UI instructions from the research topic."""
    query = " ".join(question.split())
    query = re.sub(
        r"^(?:hãy\s+)?(?:tìm|find|search)\s+",
        "",
        query,
        flags=re.IGNORECASE,
    )
    query = re.sub(
        r"^(?:các\s+)?(?:paper|papers|bài\s+báo|nghiên\s+cứu)"
        r"(?:\s+mới)?(?:\s+về|\s+about|\s+on)?\s+",
        "",
        query,
        flags=re.IGNORECASE,
    )
    query = re.sub(
        r"\s+(?:và|and)\s+(?:tóm\s+tắt|tổng\s+hợp|summarize|summary)"
        r".*$",
        "",
        query,
        flags=re.IGNORECASE,
    )
    return query.strip(" .?!,") or question


def query_local_papers(
    question: str,
    source: str,
) -> tuple[str, list[str], list[dict[str, Any]]]:
    """Retrieve from exactly one explicitly selected indexed PDF."""
    service = _paper_service()
    resolved_source = service.resolve_source(source)
    if not resolved_source:
        raise ValueError(f"Paper chưa được index: {source}")

    try:
        results = service.search(
            question,
            top_k=4,
            source=resolved_source,
        )
    except Exception:
        # The demo remains usable even if the embedding API is rate-limited:
        # the index still supports local BM25 retrieval without a network call.
        results = service.keyword_search(
            question,
            top_k=4,
            source=resolved_source,
        )
    if not results:
        return "", [], []

    evidence: list[str] = []
    citations: list[str] = []
    details: list[dict[str, Any]] = []
    for index, result in enumerate(results, 1):
        label = f"PAPER-{index}"
        # A chunk is already bounded during ingest. Keep it complete so a
        # numeric claim near the end cannot be paired with a truncated quote.
        excerpt = result.content.strip()
        evidence.append(
            f"[{label}] {result.title}, trang {result.page}, "
            f"dòng {result.line_start}-{result.line_end}, "
            f"mục {result.section}\n{excerpt}"
        )
        citations.append(
            f"{result.source} - Trang {result.page}, "
            f"dòng {result.line_start}-{result.line_end} [{label}]"
        )
        details.append(
            {
                "label": label,
                "title": result.title,
                "source": result.source,
                "page": result.page,
                "line_start": result.line_start,
                "line_end": result.line_end,
                "quote": excerpt,
            }
        )

    context = (
        "BẰNG CHỨNG RETRIEVE TỪ LOCAL PAPER RAG:\n"
        + "\n\n".join(evidence)
    )
    return context, citations, details


def query_arxiv(
    question: str,
    max_results: int = 2,
) -> tuple[str, list[str], list[dict[str, Any]]]:
    query = build_arxiv_query(question)
    cache_key = f"{query.casefold()}:{max_results}"
    if cache_key in _ARXIV_CACHE:
        return _ARXIV_CACHE[cache_key]

    papers: list[dict[str, Any]] = arxiv_search(
        query,
        max_results=max_results,
    )
    if not papers:
        return "", [], []

    blocks: list[str] = []
    citations: list[str] = []
    details: list[dict[str, Any]] = []
    for index, paper in enumerate(papers, 1):
        title = " ".join(paper.get("title", "").split())
        summary = " ".join(paper.get("summary", "").split())[:1200]
        authors = ", ".join(paper.get("authors", [])[:4])
        url = paper.get("abstract_url") or paper.get("pdf_url", "")
        blocks.append(
            f"[ARXIV-{index}] {title}\n"
            f"Tác giả: {authors}\n"
            f"Tóm tắt: {summary}\n"
            f"URL: {url}"
        )
        citations.append(f"arXiv [ARXIV-{index}]: {title} - {url}")
        details.append(
            {
                "label": f"ARXIV-{index}",
                "title": title,
                "source": "arXiv",
                "page": None,
                "line_start": None,
                "line_end": None,
                "quote": summary,
                "url": url,
            }
        )

    result = (
        "KẾT QUẢ TÌM TRÊN ARXIV:\n" + "\n\n".join(blocks),
        citations,
        details,
    )
    _ARXIV_CACHE[cache_key] = result
    return result
