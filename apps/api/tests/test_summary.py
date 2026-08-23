"""A-03 Summary Agent + A-04 SSE status events tests."""

from types import SimpleNamespace

import pytest

import server
from agent.nodes import summary
from agent.nodes.summary import (
    build_page_groups,
    load_cached_summary,
    resolve_summary_doc_id,
    store_cached_summary,
    summarize_doc,
)


# ── A-03 day-resolver ────────────────────────────────────────────────────────

def test_resolve_summary_doc_day4_maps_to_d6():
    assert resolve_summary_doc_id("tóm tắt day 4", "d7") == "d6"


def test_resolve_summary_doc_ngay5_maps_to_d7():
    assert resolve_summary_doc_id("tóm tắt ngày 5", "d10") == "d7"


def test_resolve_summary_doc_no_day_uses_active_doc():
    assert resolve_summary_doc_id("tóm tắt toàn bộ buổi học", "d9") == "d9"


def test_resolve_summary_doc_missing_day12_falls_back_to_active():
    # Day 12 chưa có trong data (đã ghi nhận P2) → về doc đang học
    assert resolve_summary_doc_id("tóm tắt day 12", "d4") == "d4"


# ── A-03 page grouping ───────────────────────────────────────────────────────

def test_build_page_groups_small_doc():
    pages = [{"doc_id": "d1", "page": i + 1, "text": "x"} for i in range(29)]
    groups = build_page_groups(pages)
    assert len(groups) == 3
    assert [page["page"] for page in groups[0]] == list(range(1, 11))


def test_build_page_groups_caps_at_ten():
    pages = [{"doc_id": "d6", "page": i + 1, "text": "x"} for i in range(400)]
    groups = build_page_groups(pages)
    assert len(groups) <= 10
    total = sum(len(group) for group in groups)
    assert total == 400


def test_summary_cache_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setattr(summary, "SUMMARY_CACHE_DIR", tmp_path)
    store_cached_summary("d9", "Tóm tắt day 9…")
    assert load_cached_summary("d9") == "Tóm tắt day 9…"


def test_summary_cache_missing_returns_none(monkeypatch, tmp_path):
    monkeypatch.setattr(summary, "SUMMARY_CACHE_DIR", tmp_path)
    assert load_cached_summary("d1") is None


# ── A-03 summarize_doc node (offline: cache hit + no pages + no doc) ─────────

def test_summarize_doc_cache_hit(monkeypatch):
    monkeypatch.setattr(
        summary, "load_cached_summary", lambda _doc_id: "Tóm tắt đã cache."
    )
    result = summarize_doc(
        {
            "user_question": "tóm tắt day 4",
            "active_doc_id": "d7",
            "final_answer": None,
            "citations": [],
            "citation_details": [],
        }
    )
    assert result["final_answer"] == "Tóm tắt đã cache."
    assert result["summary_cache_hit"] is True


def test_summarize_doc_no_pages_message(monkeypatch):
    monkeypatch.setattr(summary, "load_cached_summary", lambda _doc_id: None)
    monkeypatch.setattr(summary.slide_index, "page_texts", [])
    result = summarize_doc(
        {
            "user_question": "tóm tắt day 5",
            "active_doc_id": "d7",
            "final_answer": None,
            "citations": [],
            "citation_details": [],
        }
    )
    assert "chưa có nội dung text" in result["final_answer"]


def test_summarize_doc_unknown_doc_friendly(monkeypatch):
    result = summarize_doc(
        {
            "user_question": "tóm tắt",
            "active_doc_id": "",
            "final_answer": None,
            "citations": [],
            "citation_details": [],
        }
    )
    assert "không thấy tài liệu" in result["final_answer"]


def test_summarize_doc_map_failure_graceful(monkeypatch):
    monkeypatch.setattr(summary, "load_cached_summary", lambda _doc_id: None)
    # "day 1" → doc_id d3 (bản full) — cấp page đúng doc để đi vào nhánh map
    monkeypatch.setattr(
        summary.slide_index,
        "page_texts",
        [{"doc_id": "d3", "page": 1, "text": "nội dung"}],
    )

    class FailingLLM:
        def invoke(self, _prompt):
            raise RuntimeError("llm down")

    monkeypatch.setattr(summary, "llm", FailingLLM())
    result = summarize_doc(
        {
            "user_question": "tóm tắt day 1",
            "active_doc_id": "d1",
            "final_answer": None,
            "citations": [],
            "citation_details": [],
        }
    )
    assert "lỗi" in result["final_answer"].casefold()


# ── A-04 status events ───────────────────────────────────────────────────────

def test_status_event_format():
    event = server.status_event("answering", elapsed_ms=123)
    assert event.startswith("data: ")
    assert '"status": "answering"' in event
    assert '"elapsed_ms": 123' in event


def test_status_event_is_backward_compatible_payload():
    # Frontend cũ chỉ đọc token/done/error → payload status chỉ thêm key mới
    import json

    payload = json.loads(server.status_event("searching_arxiv")[6:])
    assert set(payload) == {"status", "detail", "elapsed_ms"}


def test_summary_token_chunks_reassemble():
    text = "## Mở đầu\n\nĐoạn một.\n\n## Ý chính\n\n" + ("từ lặp " * 120)
    chunks = server.summary_token_chunks(text)
    assert "".join(chunks) == text
    assert all(len(chunk) <= 400 for chunk in chunks)

# ── t27: tóm tắt PAPER sau Research (bug: trả tóm tắt slide Day 1) ───────────

def test_paper_summary_requested_by_question():
    state = {"messages": []}
    assert summary._paper_summary_requested("tóm tắt paper này", state) is True
    assert summary._paper_summary_requested("tóm tắt bài báo đó đi", state) is True
    assert summary._paper_summary_requested("tóm tắt day 4", state) is False


def test_paper_summary_requested_by_history_sources():
    state = {
        "messages": [
            {
                "role": "assistant",
                "content": "Multiview Transformers... [S1]",
                "sources": ["arxiv-2201.04288v4.pdf"],
            }
        ]
    }
    assert summary._paper_summary_requested("tóm tắt paper này", state) is True
    sources = summary._paper_sources_from_history(state)
    assert sources == ["arxiv-2201.04288v4.pdf"]


def test_paper_sources_extracted_from_content_regex():
    state = {
        "messages": [
            {"role": "assistant", "content": "xem arxiv-2201.04288v4.pdf - Trang 1 [S1]"}
        ]
    }
    assert summary._paper_sources_from_history(state) == ["arxiv-2201.04288v4.pdf"]


def test_summarize_doc_routes_to_paper_when_requested(monkeypatch, tmp_path):
    """t27 — "tóm tắt paper này" sau Research → tóm tắt PAPER (không phải slide)."""
    monkeypatch.setattr(summary, "SUMMARY_CACHE_DIR", tmp_path)

    class FakeService:
        @staticmethod
        def from_env():
            return FakeService()

        @staticmethod
        def resolve_source(source):
            return source if source.startswith("arxiv-") else None

        def search(self, _question, top_k, source):
            assert source == "arxiv-2201.04288v4.pdf"
            return [
                SimpleNamespace(
                    source="arxiv-2201.04288v4.pdf", title="Multiview Transformers",
                    page=3, line_start=10, line_end=12, section="Method",
                    content="Multiview Transformers dùng cross-view attention để gộp nhiều view.",
                ),
                SimpleNamespace(
                    source="arxiv-2201.04288v4.pdf", title="Multiview Transformers",
                    page=6, line_start=1, line_end=4, section="Results",
                    content="Đạt SOTA trên video recognition benchmarks.",
                ),
            ]

    monkeypatch.setattr(
        "local_rag.service.RAGService",
        SimpleNamespace(from_env=FakeService.from_env),
    )
    fake_summary = (
        "## Mở đầu\nPaper nghiên cứu Multiview Transformers cho video recognition.\n\n"
        "## Ý chính từng phần\n- Cross-view attention [S1].\n- SOTA trên benchmarks [S2].\n\n"
        "## Kết luận\nMô hình hiệu quả khi kết hợp nhiều view."
    )
    monkeypatch.setattr(
        summary, "llm",
        SimpleNamespace(invoke=lambda _prompt: SimpleNamespace(content=fake_summary)),
    )

    result = summarize_doc(
        {
            "user_question": "tóm tắt paper này",
            "active_doc_id": "d1",
            "messages": [
                {
                    "role": "assistant",
                    "content": "Multiview Transformers answer [S1].",
                    "sources": ["arxiv-2201.04288v4.pdf"],
                }
            ],
            "final_answer": None,
            "citations": [],
            "citation_details": [],
        }
    )
    assert "Multiview Transformers" in result["final_answer"]
    assert result["citations"][0].startswith("arxiv-2201.04288v4.pdf - Trang")
    assert result["citation_details"][0]["source"] == "arxiv-2201.04288v4.pdf"
    assert str(result["summary_doc_id"]).startswith("paper-")


def test_summarize_doc_slide_path_unchanged_without_paper_context(monkeypatch, tmp_path):
    """Không có context paper → vẫn slide như cũ (backward-compatible)."""
    monkeypatch.setattr(summary, "SUMMARY_CACHE_DIR", tmp_path)
    monkeypatch.setattr(summary, "load_cached_summary", lambda _doc_id: None)
    monkeypatch.setattr(
        summary.slide_index,
        "page_texts",
        [{"doc_id": "d1", "page": 1, "text": "Chào mừng Day 1 hackathon."}],
    )

    class FailingLLM:
        def invoke(self, _prompt):
            raise RuntimeError("llm down")

    monkeypatch.setattr(summary, "llm", FailingLLM())
    result = summarize_doc(
        {
            "user_question": "tóm tắt toàn bộ tài liệu này",
            "active_doc_id": "d1",
            "messages": [],
            "final_answer": None,
            "citations": [],
            "citation_details": [],
        }
    )
    assert "Day 1" not in result["final_answer"]  # vẫn nhánh slide (lỗi LLM → ghép nhóm)
    assert result["summary_doc_id"] == "d1"


def test_summarize_doc_paper_from_memory_when_history_lacks_sources(monkeypatch, tmp_path):
    """t27 — history bị graph normalize (mất sources) → summary đọc paper_source từ Memory."""
    monkeypatch.setattr(summary, "SUMMARY_CACHE_DIR", tmp_path)
    from agent.memory import store as memory_store
    import tempfile

    memory_store.MEMORY_DIR = tmp_path / "mem"
    memory_store.update_state("t27-learner", paper_source="arxiv-2201.04288v4.pdf")

    class FakeService:
        @staticmethod
        def from_env():
            return FakeService()

        @staticmethod
        def resolve_source(source):
            return source if source.startswith("arxiv-") else None

        def search(self, _q, top_k, source):
            return [
                SimpleNamespace(
                    source="arxiv-2201.04288v4.pdf", title="Multiview Transformers",
                    page=3, line_start=1, line_end=2, section="Method",
                    content="Multiview Transformers gộp nhiều view bằng cross-view attention.",
                )
            ]

    monkeypatch.setattr(
        "local_rag.service.RAGService",
        SimpleNamespace(from_env=FakeService.from_env),
    )
    monkeypatch.setattr(
        summary, "llm",
        SimpleNamespace(
            invoke=lambda _p: SimpleNamespace(content="## Mở đầu\nPaper Multiview Transformers...")
        ),
    )
    result = summarize_doc(
        {
            "user_question": "tóm tắt paper này",
            "active_doc_id": "d1",
            "learner_id": "t27-learner",
            "messages": [],  # mô phỏng graph đã normalize → không còn sources
            "final_answer": None,
            "citations": [],
            "citation_details": [],
        }
    )
    assert "Multiview Transformers" in result["final_answer"]
    assert result["citations"][0].startswith("arxiv-2201.04288v4.pdf")


# ── t36: "tóm tắt trang này" → PAGE-scope (không phải cả slide) ──────────────

def test_page_request_detection():
    assert summary._page_request("tóm tắt trang này") == (True, None)
    assert summary._page_request("tóm tắt trang 5") == (True, 5)
    assert summary._page_request("tóm tắt trang đang xem") == (True, None)
    assert summary._page_request("tóm tắt day 4") == (False, None)
    assert summary._page_request("tóm tắt toàn bộ tài liệu") == (False, None)


def test_page_summary_uses_single_page_not_doc(monkeypatch, tmp_path):
    """t36 — yêu cầu trang → summary 1 trang + citation đúng trang, KHÔNG map-reduce."""
    monkeypatch.setattr(summary, "SUMMARY_CACHE_DIR", tmp_path)
    monkeypatch.setattr(
        summary.slide_index,
        "page_texts",
        [
            {"doc_id": "d10", "page": 16, "text": "Retrieval là bước quan trọng nhất trong RAG pipeline."},
            {"doc_id": "d10", "page": 17, "text": "Pre-RAG: query transformation."},
        ],
    )

    def fake_invoke(prompt):
        assert "Trang 16" in prompt
        assert "Retrieval là bước quan trọng" in prompt
        return SimpleNamespace(content="## Trang 16 — Retrieval là bước quan trọng nhất của RAG.")

    monkeypatch.setattr(summary, "llm", SimpleNamespace(invoke=fake_invoke))
    result = summarize_doc(
        {
            "user_question": "tóm tắt trang này",
            "active_doc_id": "d10",
            "current_page": 16,
            "final_answer": None,
            "citations": [],
            "citation_details": [],
        }
    )
    assert "Retrieval" in result["final_answer"]
    assert result["citations"] == ["D10 - Trang 16"]
    assert result.get("summary_page") == 16
    assert result.get("summary_cache_hit") is None  # không đi map-reduce/cache doc


def test_page_summary_no_text_page_message(monkeypatch, tmp_path):
    monkeypatch.setattr(summary, "SUMMARY_CACHE_DIR", tmp_path)
    monkeypatch.setattr(summary.slide_index, "page_texts", [])
    result = summarize_doc(
        {
            "user_question": "tóm tắt trang 99",
            "active_doc_id": "d10",
            "current_page": 1,
            "final_answer": None,
            "citations": [],
            "citation_details": [],
        }
    )
    assert "chưa có nội dung text" in result["final_answer"]
