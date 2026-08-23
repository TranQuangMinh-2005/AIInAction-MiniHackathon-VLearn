"""A-07 observability + A-08 research upgrade tests (offline)."""

import json
from types import SimpleNamespace

import pytest

import server
from agent.observability import (
    estimate_tokens,
    golden_tool_alias,
    new_trace_id,
    record_feedback,
    record_trace,
)
from agent.observability import trace as trace_module
from agent.tools import research
from agent.tools.paper import paper as paper_module
from agent.tools.research import (
    _choice_cache_get,
    _choice_cache_put,
    query_arxiv_full_text,
)


# ── A-08 query cascade ───────────────────────────────────────────────────────

def test_query_variants_short_query_single():
    assert paper_module._query_variants("deep learning") == ["deep learning"]


def test_query_variants_long_query_cascade():
    variants = paper_module._query_variants(
        "retrieval augmented generation survey foundations"
    )
    assert variants[0] == "retrieval augmented generation survey foundations"
    assert any("AND" in variant and "all:" in variant for variant in variants[1:])
    assert len(variants) <= 3


def test_arxiv_search_cascades_to_second_variant(monkeypatch):
    """Variant 1 rỗng (phrase dài) → variant 2 (AND) ra paper."""
    calls = []

    def fake_api(query, max_results, sort_by):
        calls.append(query)
        if "AND" in query:
            return [{"title": "Found", "abstract_url": "https://arxiv.org/abs/1"}]
        return []

    monkeypatch.setattr(paper_module, "_arxiv_api_search", fake_api)
    papers = paper_module.arxiv_search(
        "retrieval augmented generation survey foundations", 3
    )
    assert papers[0]["title"] == "Found"
    assert len(calls) == 2


def test_arxiv_search_all_empty_falls_to_ddg(monkeypatch):
    def fake_api(_query, _max_results, _sort_by):
        return []

    monkeypatch.setattr(paper_module, "_arxiv_api_search", fake_api)
    monkeypatch.setattr(
        paper_module,
        "_search_duckduckgo_arxiv",
        lambda _q, _m: [{"title": "DDG paper"}],
    )
    assert paper_module.arxiv_search("weird long query here", 3) == [
        {"title": "DDG paper"}
    ]


# ── A-08 paper-choice cache ──────────────────────────────────────────────────

def test_choice_cache_put_get_same_day(monkeypatch):
    monkeypatch.setattr(research, "_PAPER_CHOICE_CACHE", {})
    _choice_cache_put("RAG Survey", "arxiv-1.pdf", "RAG Survey", "https://arxiv.org/abs/1")
    entry = _choice_cache_get("rag survey")
    assert entry["source"] == "arxiv-1.pdf"


def test_choice_cache_expires_next_day(monkeypatch):
    monkeypatch.setattr(research, "_PAPER_CHOICE_CACHE", {})
    _choice_cache_put("RAG Survey", "arxiv-1.pdf", "t", "u")
    monkeypatch.setattr(
        research, "datetime", SimpleNamespace(date=SimpleNamespace(today=lambda: _S()))
    )
    assert _choice_cache_get("RAG Survey") is None


class _S:
    def isoformat(self):
        return "2099-01-01"


def test_query_arxiv_full_text_cache_hit_skips_api(monkeypatch):
    monkeypatch.setattr(research, "_PAPER_CHOICE_CACHE", {})
    monkeypatch.setattr(
        research,
        "_paper_service",
        lambda: SimpleNamespace(
            resolve_source=lambda source: source,
        ),
    )
    monkeypatch.setattr(
        research,
        "query_local_papers",
        lambda question, source: (
            f"CACHED:{question}:{source}",
            ["arxiv-1.pdf - Trang 1 [S1]"],
            [{"label": "S1", "url": ""}],
        ),
    )
    _choice_cache_put("retrieval augmented generation", "arxiv-1.pdf", "RAG", "url")
    _call_counter = {"arxiv": 0}
    monkeypatch.setattr(
        research, "arxiv_search", lambda *_a, **_k: _call_counter.__setitem__("arxiv", _call_counter["arxiv"] + 1) or []
    )

    context, citations, _details = query_arxiv_full_text(
        "RAG là gì?", "retrieval augmented generation"
    )
    assert "CACHED" in context
    assert _call_counter["arxiv"] == 0  # không gọi lại arXiv API


# ── A-07 trace + feedback ────────────────────────────────────────────────────

def test_record_trace_writes_jsonl_with_cost(monkeypatch, tmp_path):
    monkeypatch.setattr(trace_module, "OBS_DIR", tmp_path)
    trace = record_trace(
        trace_id="abc123",
        mode="normal",
        intent="slide",
        tools=["slide_search", "tutor_coach"],
        answer_text="câu trả lời dài vừa phải cho học viên",
        input_text="RAG là gì?",
        latency_ms=1234,
    )
    assert trace["cost_usd_est"] > 0
    assert trace["tool_match"] == "lookup"
    lines = (tmp_path / "traces.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["trace_id"] == "abc123"


def test_golden_tool_alias_mapping():
    assert golden_tool_alias("web_search_arxiv") == "papers"
    assert golden_tool_alias("refuse_off_topic") == "no_tool"
    assert golden_tool_alias("unknown_tool") == "unknown_tool"
    assert golden_tool_alias(None) is None


def test_estimate_tokens_never_zero():
    assert estimate_tokens("") >= 1


def test_record_feedback_validates_rating(monkeypatch, tmp_path):
    monkeypatch.setattr(trace_module, "OBS_DIR", tmp_path)
    assert record_feedback("t-1", 1) is True
    assert record_feedback("t-2", -1, "dài quá") is True
    assert record_feedback("t-3", 0) is False
    lines = (tmp_path / "feedback.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2


def test_feedback_endpoint(monkeypatch):
    monkeypatch.setattr(
        server, "record_feedback", lambda trace_id, rating, comment: rating in (1, -1)
    )
    assert server.feedback(server.FeedbackRequest(trace_id="t", rating=1)) == {
        "ok": True,
        "trace_id": "t",
    }


# ── A-08 routing: normal + "tìm paper" → research path ───────────────────────

def test_wants_paper_search_detects_paper_keywords():
    from agent.graph import wants_paper_search

    assert wants_paper_search("Tim paper ve attention interpretability")
    assert wants_paper_search("tìm bài báo arxiv về RAG")
    assert not wants_paper_search("RAG pipeline gồm những bước nào?")
    assert not wants_paper_search("giải thích attention mechanism")


def test_graph_routes_deep_paper_to_web_search(monkeypatch):
    from agent import nodes as nodes_pkg
    from agent.graph import build_graph
    from agent.nodes import orchestrator
    def fake_orchestrator_llm(_prompt):
        return SimpleNamespace(
            content='{"intent": "deep", "reason": "muốn paper"}'
        )

    def fake_web_search(state):
        return {
            **state,
            "web_search_result": "paper found [S1].",
            "citations": ["p.pdf - Trang 1 [S1]"],
            "citation_details": [{"label": "S1"}],
        }

    def fake_answer_llm(_messages):
        return SimpleNamespace(content="Đây là paper research [S1].")

    monkeypatch.setattr(orchestrator, "llm", SimpleNamespace(invoke=fake_orchestrator_llm))
    monkeypatch.setattr(nodes_pkg.web_search, "search_online", fake_web_search)
    monkeypatch.setattr(
        nodes_pkg.answer, "llm", SimpleNamespace(invoke=fake_answer_llm)
    )
    monkeypatch.setattr(nodes_pkg.tutor_coach, "llm",
                        SimpleNamespace(invoke=lambda _p: SimpleNamespace(content="")))


    graph = build_graph()
    result = graph.invoke(
        {
            "user_question": "tim paper ve attention interpretability",
            "slide_context": "context",
            "current_page": 1,
            "slide_title": "Day 8",
            "paper_source": None,
            "messages": [],
            "slide_search_result": None,
            "web_search_result": None,
            "final_answer": None,
            "citations": [],
            "citation_details": [],
            "needs_web_search": False,
            "error": None,
            "mode": "normal",
            "original_question": "tim paper ve attention interpretability",
            "normalized_question": None,
            "intent": None,
            "orchestrator_note": None,
            "retrieval_scope": "auto",
            "active_doc_id": "d1",
            "summary_doc_id": None,
            "summary_cache_hit": None,
            "move": "review_concept",
            "misconceptions": [],
            "follow_ups": [],
            "asked_check_question": False,
            "learner_id": None,
            "memory_context": "",
        }
    )
    assert "paper" in result["final_answer"].casefold()
    assert result["web_search_result"]


# ── t28: endpoint PDF paper cho citation [S1] nhảy trang ──────────────────────

def test_paper_pdf_rejects_invalid_source():
    from fastapi import HTTPException

    import server

    for bad in ("../etc/passwd", "foo.pdf", "https://evil.com/x.pdf", "", "arxiv-1.pdf;cat"):
        try:
            server.paper_pdf(bad)
            raise AssertionError(f"must reject {bad!r}")
        except HTTPException as exc:
            assert exc.status_code == 400


def test_paper_pdf_returns_file_for_indexed_source(monkeypatch, tmp_path):
    from fastapi.responses import FileResponse

    import server

    pdf_file = tmp_path / "arxiv-2201.04288v4.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 mock paper")

    class FakeService:
        @staticmethod
        def from_env():
            return FakeService()

        @staticmethod
        def resolve_source(source):
            return source if source == "arxiv-2201.04288v4.pdf" else None

        settings = type("S", (), {"pdf_dir": tmp_path})()

    monkeypatch.setattr(server, "RAGService", FakeService)
    response = server.paper_pdf("arxiv-2201.04288v4.pdf")
    assert isinstance(response, FileResponse)
    assert response.media_type == "application/pdf"
    assert str(response.path) == str(pdf_file)


def test_paper_pdf_404_when_not_indexed(monkeypatch, tmp_path):
    from fastapi import HTTPException

    import server

    class FakeService:
        @staticmethod
        def from_env():
            return FakeService()

        @staticmethod
        def resolve_source(_source):
            return None

    monkeypatch.setattr(server, "RAGService", FakeService)
    try:
        server.paper_pdf("arxiv-9999.00000v1.pdf")
        raise AssertionError("must 404")
    except HTTPException as exc:
        assert exc.status_code == 404
