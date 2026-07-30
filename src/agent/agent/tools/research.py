"""Adapters that turn scientific-paper tools into Agent-ready text."""

from __future__ import annotations

from typing import Any

from agent.config import load_environment
from local_rag.agent_tool import ask_research_papers

from agent.tools.paper.paper import arxiv_search

load_environment()


def query_local_papers(question: str) -> tuple[str, list[str]]:
    """Call the standalone local RAG through its stable tool boundary."""
    result = ask_research_papers(question=question, top_k=6)
    verified = [
        citation
        for citation in result.get("citations", [])
        if citation.get("entailed") is True
    ]
    if not verified:
        return "", []

    evidence: list[str] = []
    citations: list[str] = []
    for citation in verified:
        label = citation.get("label", "")
        source = citation.get("source", "paper")
        page = citation.get("page", "?")
        quote = citation.get("quote", "")
        claim = citation.get("claim", "")
        evidence.append(
            f"[{label}] Claim đã kiểm chứng: {claim}\n"
            f"Nguồn: {source}, trang {page}: \"{quote}\""
        )
        citations.append(f"{source} - Trang {page} [{label}]")

    context = (
        "BẰNG CHỨNG TỪ LOCAL PAPER RAG "
        "(chỉ gồm claim đã qua entailment):\n"
        + "\n".join(evidence)
    )
    return context, citations


def query_arxiv(question: str, max_results: int = 3) -> tuple[str, list[str]]:
    papers: list[dict[str, Any]] = arxiv_search(
        question,
        max_results=max_results,
    )
    if not papers:
        return "", []

    blocks: list[str] = []
    citations: list[str] = []
    for index, paper in enumerate(papers, 1):
        title = " ".join(paper.get("title", "").split())
        summary = " ".join(paper.get("summary", "").split())
        authors = ", ".join(paper.get("authors", [])[:4])
        url = paper.get("abstract_url") or paper.get("pdf_url", "")
        blocks.append(
            f"[ARXIV-{index}] {title}\n"
            f"Tác giả: {authors}\n"
            f"Tóm tắt: {summary}\n"
            f"URL: {url}"
        )
        citations.append(f"arXiv: {title} - {url}")

    return "KẾT QUẢ TÌM TRÊN ARXIV:\n" + "\n\n".join(blocks), citations
