"""A-01 + A-02 tests — Orchestrator Router + Slide retrieval nâng cấp."""

import re
from types import SimpleNamespace

import pytest

import server
from agent.nodes import orchestrator
from agent.nodes.answer import refuse_off_topic
from agent.rag import DOC_TITLES, SlideIndex


@pytest.fixture(autouse=True)
def _offline_expansion(monkeypatch):
    """Tests chạy offline: tắt LLM multi-query expansion (chỉ variant deterministic)."""
    monkeypatch.setenv("SLIDE_MULTI_QUERY", "0")
    monkeypatch.setenv("SLIDE_HYBRID", "0")


# ── A-01 normalize_question ───────────────────────────────────────────────────

def test_normalize_teencode_so_lai_to_slide():
    assert orchestrator.normalize_question("tóm tắt sờ lai này") == "tóm tắt slide này"


def test_normalize_slai_variant():
    assert orchestrator.normalize_question("slai 5 có gì?") == "slide 5 có gì?"


def test_normalize_promt_to_prompt():
    assert "prompt" in orchestrator.normalize_question("promt là gì?").casefold()


def test_normalize_react_to_react_in_ai_context():
    assert orchestrator.normalize_question("React là gì?") == "ReAct là gì?"


def test_normalize_keeps_react_js_context():
    question = "React js dùng để làm gì?"
    assert orchestrator.normalize_question(question) == question


def test_normalize_keeps_normal_question_unchanged():
    question = "RAG pipeline hoạt động thế nào?"
    assert orchestrator.normalize_question(question) == question


def test_normalize_dieu_toa_to_deploy():
    """VX11 — teencode "điêu toa" = deploy (Day 15 triển khai thực tế)."""
    assert orchestrator.normalize_question("điêu toa model lên server") == (
        "deploy model lên server"
    )


# ── A-01 deterministic intent classification ─────────────────────────────────

def test_deterministic_intent_summary():
    intent, _reason = orchestrator.classify_deterministic("tóm tắt toàn bộ day 4")
    assert intent == "summary"


def test_deterministic_intent_logistics():
    intent, _reason = orchestrator.classify_deterministic("deadline bài tập tuần này?")
    assert intent == "logistics"


def test_deterministic_intent_off_topic():
    intent, _reason = orchestrator.classify_deterministic("giá vàng hôm nay bao nhiêu?")
    assert intent == "off_topic"


def test_deterministic_intent_slide_needs_llm():
    assert orchestrator.classify_deterministic("RAG là gì?") is None


# ── A-01 LLM intent classification fallback ──────────────────────────────────

def test_classify_intent_llm_json(monkeypatch):
    called = []

    def fake_invoke(prompt):
        called.append(prompt)
        return SimpleNamespace(
            content='{"intent": "deep", "reason": "muốn paper khoa học"}'
        )

    monkeypatch.setattr(orchestrator, "llm", SimpleNamespace(invoke=fake_invoke))
    intent, reason = orchestrator.classify_intent("so sánh RAG nâng cao")
    assert intent == "deep"
    assert "paper" in reason
    assert "intent" in called[0].lower() or "intent" in called[0]


def test_classify_intent_llm_failure_falls_back_to_unclear(monkeypatch):
    class FailingLLM:
        def invoke(self, _prompt):
            raise RuntimeError("quota exceeded")

    monkeypatch.setattr(orchestrator, "llm", FailingLLM())
    intent, _reason = orchestrator.classify_intent("một câu hỏi lạ nào đó")
    assert intent in {"unclear", "slide"}


def test_classify_intent_llm_off_topic_without_keyword_downgraded_to_unclear(monkeypatch):
    """VX11 — LLM đánh off_topic nhưng câu có tín hiệu học tập (teencode
    "điêu toa" → deploy) → hạ xuống unclear (không chặn oan)."""
    monkeypatch.setattr(
        orchestrator,
        "llm",
        SimpleNamespace(
            invoke=lambda _prompt: SimpleNamespace(
                content='{"intent": "off_topic", "reason": "chữ khó đọc"}'
            )
        ),
    )
    intent, reason = orchestrator.classify_intent("điêu toa model của mình")
    assert intent == "unclear"
    assert "off_topic" in reason


def test_vx13_personal_question_stays_off_topic(monkeypatch):
    """VX13 — "t có đẹp trai không" → từ chối (off_topic), không kéo vào lookup."""
    monkeypatch.setattr(
        orchestrator,
        "llm",
        SimpleNamespace(
            invoke=lambda _prompt: SimpleNamespace(
                content='{"intent": "slide", "reason": "?"}'
            )
        ),
    )
    intent, reason = orchestrator.classify_intent("t có đẹp trai không")
    assert intent == "off_topic"
    assert "cá nhân" in reason


def test_vx14_short_llm_off_topic_without_signal_stays_off_topic(monkeypatch):
    """VX14 — LLM nói off_topic, câu ngắn không keyword học tập → GIỮ off_topic
    (ngưỡng VX13/VX14: không downgrade bừa)."""
    monkeypatch.setattr(
        orchestrator,
        "llm",
        SimpleNamespace(
            invoke=lambda _prompt: SimpleNamespace(
                content='{"intent": "off_topic", "reason": "không liên quan"}'
            )
        ),
    )
    intent, reason = orchestrator.classify_intent("bạn là model của hãng nào")
    assert intent == "off_topic"
    assert "cá nhân" in reason
    intent_short, _reason = orchestrator.classify_intent("xyz lạ lắm nhỉ")
    assert intent_short == "off_topic"  # ngắn + không keyword → giữ từ chối


def test_vx13_long_course_like_question_downgraded(monkeypatch):
    """Câu dài khó đọc nhưng dạng học tập → downgrade unclear (nhờ ngưỡng độ dài)."""
    monkeypatch.setattr(
        orchestrator,
        "llm",
        SimpleNamespace(
            invoke=lambda _prompt: SimpleNamespace(
                content='{"intent": "off_topic", "reason": "khó đọc"}'
            )
        ),
    )
    long_question = "mình muốn hỏi về một khái niệm khá khó hiểu trong bài này với ạ"
    intent, _reason = orchestrator.classify_intent(long_question)
    assert intent == "unclear"


def test_classify_intent_llm_off_topic_with_keyword_stays_off_topic(monkeypatch):
    monkeypatch.setattr(
        orchestrator,
        "llm",
        SimpleNamespace(
            invoke=lambda _prompt: SimpleNamespace(
                content='{"intent": "off_topic", "reason": "giá vàng"}'
            )
        ),
    )
    intent, _reason = orchestrator.classify_intent("giá vàng hôm nay bao nhiêu")
    assert intent == "off_topic"


# ── A-01 orchestrate node ────────────────────────────────────────────────────

def test_orchestrate_normalizes_and_sets_intent():
    result = orchestrator.orchestrate(
        {
            "user_question": "sờ lai này có gì?",
            "mode": "normal",
            "needs_web_search": False,
        }
    )
    assert result["normalized_question"] == "slide này có gì?"
    assert result["original_question"] == "sờ lai này có gì?"
    assert result["intent"] == "slide"


def test_orchestrate_offs_topic_research_disables_web():
    result = orchestrator.orchestrate(
        {
            "user_question": "thời tiết Paris hôm nay?",
            "mode": "research",
            "needs_web_search": True,
        }
    )
    assert result["intent"] == "off_topic"
    assert result["needs_web_search"] is False


def test_refuse_off_topic_returns_friendly_answer():
    result = refuse_off_topic(
        {"user_question": "giá vàng?", "final_answer": None}
    )
    assert "AI Thực Chiến" in result["final_answer"]
    assert result["citations"] == []


# ── A-01 regression: research mode qua graph không crash (HTTP 500 bug) ──────

def test_graph_research_routes_web_search_and_answers(monkeypatch):
    """/api/chat mode=research: web_search → generate_answer, slide_search_result
    có thể là None/"" — không được 500 ở answer.py .strip()."""
    from agent import nodes as nodes_pkg
    from agent.graph import build_graph

    def fake_orchestrator_llm(_prompt):
        return SimpleNamespace(
            content='{"intent": "deep", "reason": "cần paper khoa học"}'
        )

    def fake_web_search(state):
        return {
            **state,
            "web_search_result": "Paper evidence about retrieval [S1].",
            "citations": ["paper.pdf - Trang 1 [S1]"],
            "citation_details": [{"label": "S1"}],
        }

    def fake_answer_llm(_messages):
        return SimpleNamespace(content="Đây là câu trả lời từ paper [S1].")

    monkeypatch.setattr(orchestrator, "llm", SimpleNamespace(invoke=fake_orchestrator_llm))
    monkeypatch.setattr(
        nodes_pkg.web_search, "search_online", fake_web_search
    )
    monkeypatch.setattr(
        nodes_pkg.answer, "llm", SimpleNamespace(invoke=fake_answer_llm)
    )

    graph = build_graph()
    result = graph.invoke(
        {
            "user_question": "tìm paper về RAG nâng cao",
            "slide_context": "context",
            "current_page": 3,
            "slide_title": "Day 8 — RAG Pipeline",
            "paper_source": None,
            "messages": [],
            "slide_search_result": "",   # research: "" (fix 500)
            "web_search_result": None,
            "final_answer": None,
            "citations": [],
            "citation_details": [],
            "needs_web_search": True,
            "error": None,
            "mode": "research",
            "original_question": "tìm paper về RAG nâng cao",
            "normalized_question": None,
            "intent": None,
            "orchestrator_note": None,
            "retrieval_scope": "auto",
        }
    )
    assert result["final_answer"]
    assert "paper" in result["final_answer"].casefold()
    assert result["web_search_result"]


def test_generate_answer_survives_none_slide_result(monkeypatch):
    """Defensive: nếu state vẫn giữ slide_search_result=None, generate_answer
    không được ném TypeError (bug HTTP 500 cũ)."""
    from agent.nodes.answer import generate_answer

    monkeypatch.setattr(
        "agent.nodes.answer.llm",
        SimpleNamespace(
            invoke=lambda _messages: SimpleNamespace(
                content="Trả lời từ web [S1]."
            )
        ),
    )

    result = generate_answer(
        {
            "user_question": "câu hỏi",
            "slide_search_result": None,
            "web_search_result": "evidence [S1]",
            "current_page": 1,
            "slide_title": "t",
            "citations": [],
            "needs_web_search": True,
            "messages": [],
            "mode": "research",
        }
    )
    assert result["final_answer"] == "Trả lời từ web [S1]."


# ── A-02 DOC_TITLES ──────────────────────────────────────────────────────────

def test_doc_titles_cover_all_slide_ids():
    for doc_id in (
        "d1", "d2", "d3", "d4", "d5", "d6", "d7", "day05-ref",
        "d8", "d9", "d10", "d11", "d12", "d13", "d14", "d15", "d16",
    ):
        assert doc_id in DOC_TITLES


def test_resolve_slide_title_no_longer_hardcodes_d1_d2():
    assert "Thiết kế sản phẩm AI" in server.resolve_slide_title("d7")
    assert "AI & LLM Foundation" in server.resolve_slide_title("d1")
    assert server.resolve_slide_title("nonexistent") != ""


# ── A-02 retrieval: doc-first + corpus fallback + scope ──────────────────────

def _fake_index() -> SlideIndex:
    index = SlideIndex()
    index._loaded = True
    index.page_texts = [
        {"doc_id": "d1", "page": 1, "text": "Chào mừng buổi hackathon khai mạc."},
        {"doc_id": "d1", "page": 2, "text": "Giới thiệu đội ngũ ban tổ chức."},
        {"doc_id": "d7", "page": 10, "text": "Retrieval Augmented Generation RAG pipeline embedding vector store."},
        {"doc_id": "d7", "page": 11, "text": "Hybrid dense BM25 retrieval reranking MMR."},
        {"doc_id": "d10", "page": 5, "text": "LLM token embedding semantic search."},
    ]
    return index


def test_retrieve_auto_falls_back_to_full_corpus_when_doc_has_no_hit():
    index = _fake_index()
    results = index.retrieve("RAG pipeline embedding", doc_id="d1", k=3, scope="auto")
    assert results, "phải fallback ra corpus khi doc hiện tại không có hit"
    assert results[0]["doc_id"] == "d7"


def test_retrieve_doc_scope_stays_inside_doc():
    index = _fake_index()
    results = index.retrieve(
        "RAG pipeline embedding", doc_id="d1", k=3, scope="doc"
    )
    assert all(page["doc_id"] == "d1" for page in results)


def test_retrieve_corpus_scope_searches_everything():
    index = _fake_index()
    results = index.retrieve("embedding", doc_id="d1", k=4, scope="corpus")
    doc_ids = {page["doc_id"] for page in results}
    assert "d7" in doc_ids or "d10" in doc_ids


def test_retrieve_citations_carry_doc_prefix():
    index = _fake_index()
    context, citations = index.retrieve_context(
        "RAG pipeline embedding", doc_id="d1", k=2, scope="auto"
    )
    assert context.startswith("--- ")
    assert all(re.match(r"^D\d+\s*-\s*Trang\s+\d+$", c) for c in citations)


def test_multi_query_merge_keeps_result_count_bounded():
    index = _fake_index()
    results = index.retrieve("RAG pipeline", doc_id=None, k=2, scope="corpus")
    assert len(results) <= 2


def test_expand_queries_uses_llm_variants(monkeypatch):
    monkeypatch.setenv("SLIDE_MULTI_QUERY", "1")
    monkeypatch.setattr(
        "agent.llm.llm",
        SimpleNamespace(
            invoke=lambda _prompt: SimpleNamespace(
                content="rag pipeline survey\nretrieval augmented generation"
            )
        ),
    )
    from agent.rag import _expand_queries

    variants = _expand_queries("RAG là gì?")
    assert len(variants) >= 2
    assert variants[0] == "RAG là gì?"
    assert any("survey" in variant for variant in variants)


def test_expand_queries_llm_failure_falls_back_to_deterministic(monkeypatch):
    monkeypatch.setenv("SLIDE_MULTI_QUERY", "1")

    class FailingLLM:
        def invoke(self, _prompt):
            raise RuntimeError("quota")

    monkeypatch.setattr("agent.llm.llm", FailingLLM())
    from agent.rag import _expand_queries

    variants = _expand_queries("giải thích về RAG")
    assert variants[0] == "giải thích về RAG"
    assert any("RAG" in variant for variant in variants[1:])


def test_page_boost_prefers_current_page():
    index = _fake_index()
    # Từ "retrieval" xuất hiện ở cả trang 10 và 11 với cùng tần suất → điểm BM25 bằng
    # nhau → boost trang đang xem (current_page=11) phải đẩy trang 11 lên đầu.
    results = index.retrieve(
        "retrieval",
        doc_id="d7",
        k=2,
        current_page=11,
        scope="doc",
    )
    assert results
    assert results[0]["page"] == 11

# ── P0-1: dedupe citation label (short vs full) ──────────────────────────────

def test_citation_label_scheme():
    from agent.rag import citation_label

    assert citation_label("d1") == "D1"      # short hackathon giữ nguyên
    assert citation_label("d2") == "D2"
    assert citation_label("d3") == "D1 Full"  # full Day1 — KHÔNG trùng short
    assert citation_label("d4") == "D2 Full"
    assert citation_label("d5") == "D5"      # các doc khác giữ doc_id.upper()
    assert citation_label("day05-ref") == "DAY05-REF"


def test_retrieve_context_citations_use_dedupe_labels():
    from agent.rag import SlideIndex

    index = SlideIndex()
    index._loaded = True
    index.page_texts = [
        {"doc_id": "d3", "page": 12, "text": "Day 1 full noi dung LLM foundation."},
    ]
    _context, citations = index.retrieve_context(
        "LLM foundation", doc_id="d3", k=1, scope="doc"
    )
    assert citations[0].startswith("D1 Full - Trang 12")


# ── t41: intent "example" (sinh ví dụ/câu hỏi ôn tập sư phạm) ────────────────

def test_deterministic_intent_example():
    intent, _reason = orchestrator.classify_deterministic(
        "Cho mình ví dụ thực tế hoặc câu hỏi ôn tập về phần này"
    )
    assert intent == "example"
    intent2, _r2 = orchestrator.classify_deterministic("cho ví dụ về RAG")
    assert intent2 == "example"
    intent3, _r3 = orchestrator.classify_deterministic("câu hỏi ôn tập về embedding")
    assert intent3 == "example"


def test_deterministic_intent_unaffected():
    assert orchestrator.classify_deterministic("tóm tắt day 4")[0] == "summary"
    assert orchestrator.classify_deterministic("giá vàng hôm nay")[0] == "off_topic"
    assert orchestrator.classify_deterministic("RAG pipeline hoạt động thế nào?") is None
