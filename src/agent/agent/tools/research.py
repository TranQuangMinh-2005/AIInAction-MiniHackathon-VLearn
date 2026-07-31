"""Adapters that turn scientific-paper tools into Agent-ready text."""

from __future__ import annotations

from functools import lru_cache
import re
from typing import Any

from agent.config import load_environment
from local_rag.service import RAGService

from agent.tools.paper.paper import arxiv_download_pdf, arxiv_search

load_environment()

_ARXIV_CACHE: dict[
    str, tuple[str, list[str], list[dict[str, Any]]]
] = {}
_GENERIC_RESEARCH_TERMS = {
    "about",
    "analysis",
    "approach",
    "generation",
    "language",
    "large",
    "learning",
    "method",
    "model",
    "models",
    "research",
    "study",
    "system",
    "using",
}


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


def query_relevant_local_paper(
    question: str,
    search_query: str,
) -> tuple[str, list[str], list[dict[str, Any]]] | None:
    """Reuse an indexed paper when it clearly matches the research query."""
    terms = {
        token
        for token in re.findall(r"[a-z0-9-]+", search_query.casefold())
        if len(token) >= 4 and token not in _GENERIC_RESEARCH_TERMS
    }
    if len(terms) < 2:
        return None

    service = _paper_service()
    candidates = service.keyword_search(search_query, top_k=3)
    if not candidates:
        return None
    best = candidates[0]
    searchable = f"{best.title} {best.content}".casefold()
    overlap = sum(term in searchable for term in terms)
    required = min(3, len(terms))
    if overlap < required:
        return None

    return query_local_papers(question, best.source)


def query_arxiv_full_text(
    question: str,
    search_query: str,
) -> tuple[str, list[str], list[dict[str, Any]]]:
    """Find one relevant arXiv paper, index its PDF, then query full text."""
    papers: list[dict[str, Any]] = arxiv_search(
        search_query,
        max_results=1,
    )
    if not papers:
        return "", [], []

    paper = papers[0]
    pdf_url = paper.get("pdf_url", "")
    if not pdf_url:
        return "", [], []

    raw_id = (
        paper.get("abstract_url", "").rstrip("/").split("/")[-1]
        or "paper"
    )
    safe_id = re.sub(r"[^A-Za-z0-9._-]+", "-", raw_id).strip("-")
    source = f"arxiv-{safe_id}.pdf"
    service = _paper_service()

    if not service.resolve_source(source):
        pdf = arxiv_download_pdf(pdf_url)
        if not pdf.startswith(b"%PDF"):
            raise RuntimeError("arXiv không trả về PDF hợp lệ.")
        service.settings.pdf_dir.mkdir(parents=True, exist_ok=True)
        destination = service.settings.pdf_dir / source
        temporary = destination.with_suffix(".pdf.part")
        temporary.write_bytes(pdf)
        temporary.replace(destination)
        service.ingest_directory(reset=False)

    context, citations, details = query_local_papers(question, source)
    title = " ".join(paper.get("title", "").split())
    abstract_url = paper.get("abstract_url", "")
    for detail in details:
        detail["url"] = abstract_url or pdf_url

    if context:
        context = (
            "PAPER ĐƯỢC RESEARCH TỰ ĐỘNG TRÊN ARXIV:\n"
            f"Tiêu đề: {title}\n"
            f"URL: {abstract_url or pdf_url}\n\n"
            f"{context}"
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
