"""Adapters that turn scientific-paper tools into Agent-ready text."""

from __future__ import annotations

from functools import lru_cache
import re
from typing import Any

from agent.config import load_environment
from local_rag.service import RAGService

from agent.tools.paper.paper import arxiv_search

load_environment()

_ARXIV_CACHE: dict[str, tuple[str, list[str]]] = {}


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


def query_local_papers(question: str) -> tuple[str, list[str]]:
    """Fast path: retrieve evidence only when the user names an indexed PDF."""
    service = _paper_service()
    source = service.resolve_source(question)
    if not source:
        return "", []

    try:
        results = service.search(question, top_k=4, source=source)
    except Exception:
        # The demo remains usable even if the embedding API is rate-limited:
        # the index still supports local BM25 retrieval without a network call.
        results = service.keyword_search(
            question,
            top_k=4,
            source=source,
        )
    if not results:
        return "", []

    evidence: list[str] = []
    citations: list[str] = []
    for index, result in enumerate(results, 1):
        label = f"PAPER-{index}"
        # Bound prompt size so the first streamed token arrives quickly.
        excerpt = result.content[:1800].strip()
        evidence.append(
            f"[{label}] {result.title}, trang {result.page}, "
            f"mục {result.section}\n{excerpt}"
        )
        citations.append(
            f"{result.source} - Trang {result.page} [{label}]"
        )

    context = (
        "BẰNG CHỨNG RETRIEVE TỪ LOCAL PAPER RAG:\n"
        + "\n\n".join(evidence)
    )
    return context, citations


def query_arxiv(question: str, max_results: int = 2) -> tuple[str, list[str]]:
    query = build_arxiv_query(question)
    cache_key = f"{query.casefold()}:{max_results}"
    if cache_key in _ARXIV_CACHE:
        return _ARXIV_CACHE[cache_key]

    papers: list[dict[str, Any]] = arxiv_search(
        query,
        max_results=max_results,
    )
    if not papers:
        return "", []

    blocks: list[str] = []
    citations: list[str] = []
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

    result = (
        "KẾT QUẢ TÌM TRÊN ARXIV:\n" + "\n\n".join(blocks),
        citations,
    )
    _ARXIV_CACHE[cache_key] = result
    return result
