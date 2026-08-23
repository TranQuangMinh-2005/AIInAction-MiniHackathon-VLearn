"""A-05 Tutor Coach + A-06 Memory tests (offline)."""

from types import SimpleNamespace

import pytest

import server
from agent.memory import store as memory_store
from agent.nodes import tutor_coach


@pytest.fixture(autouse=True)
def _tmp_memory(monkeypatch, tmp_path):
    """Mỗi test dùng thư mục memory riêng (không đụng data thật)."""
    monkeypatch.setattr(memory_store, "MEMORY_DIR", tmp_path / "memory")


# ── A-05 build_envelope ──────────────────────────────────────────────────────

def _state(**overrides):
    base = {
        "user_question": "RAG là gì?",
        "original_question": "RAG là gì?",
        "slide_context": "context",
        "current_page": 3,
        "slide_title": "Day 8 — RAG Pipeline",
        "messages": [],
        "web_search_result": None,
        "slide_search_result": "RAG là Retrieval Augmented Generation [Trang 5].",
        "final_answer": "RAG là...",
        "citations": [],
        "citation_details": [],
        "intent": "slide",
        "mode": "normal",
        "active_doc_id": "d10",
        "needs_web_search": False,
    }
    base.update(overrides)
    return base


def test_envelope_every_turn_has_all_fields():
    envelope = tutor_coach.build_envelope(_state())
    assert set(envelope) == {
        "move", "misconceptions", "follow_ups", "asked_check_question"
    }
    assert envelope["move"] in tutor_coach.MOVES
    assert isinstance(envelope["follow_ups"], list) and len(envelope["follow_ups"]) >= 2
    assert envelope["asked_check_question"] is False  # turn bình thường


def test_normal_turn_never_asks_check_question():
    envelope = tutor_coach.build_envelope(
        _state(original_question="RAG pipeline gồm những bước nào?")
    )
    assert envelope["asked_check_question"] is False


def test_react_react_misconception_detected():
    # Conv C0128 mô phỏng: "React là gì" trong khóa AI
    envelope = tutor_coach.build_envelope(
        _state(
            original_question="React là gì?",
            user_question="ReAct là gì?",
        )
    )
    assert envelope["misconceptions"]
    assert any("React" in item and "ReAct" in item for item in envelope["misconceptions"])
    assert any("ReAct pattern" in item for item in envelope["follow_ups"])
    assert envelope["asked_check_question"] is True  # nhầm lẫn = dấu hiệu khó


def test_vague_question_asks_check_and_gives_hint(monkeypatch):
    monkeypatch.setattr(
        tutor_coach,
        "llm",
        SimpleNamespace(
            invoke=lambda _prompt: SimpleNamespace(
                content="Bạn đã hiểu khái niệm RAG chưa?"
            )
        ),
    )
    envelope = tutor_coach.build_envelope(
        _state(original_question="mình không hiểu RAG lắm, nói lại dễ hiểu hơn được không?")
    )
    assert envelope["asked_check_question"] is True
    assert envelope["move"] == "give_hint"
    assert any("chưa" in item or "hiểu" in item.casefold() for item in envelope["follow_ups"])


def test_repeat_question_from_memory_flagged(monkeypatch):
    monkeypatch.setattr(
        tutor_coach,
        "llm",
        SimpleNamespace(invoke=lambda _prompt: SimpleNamespace(content="")),
    )
    tutor_coach.remember_turn(
        _state(learner_id="learner-x", original_question="embedding là gì?"),
        {"misconceptions": []},
    )
    tutor_coach.remember_turn(
        _state(learner_id="learner-x", original_question="embedding là gì?"),
        {"misconceptions": []},
    )
    envelope = tutor_coach.build_envelope(
        _state(learner_id="learner-x", original_question="embedding là gì?")
    )
    assert envelope["asked_check_question"] is True
    assert any("lặp" in item.casefold() or "trước đó" in item for item in envelope["follow_ups"])


def test_llm_failure_still_returns_envelope():
    class FailingLLM:
        def invoke(self, _prompt):
            raise RuntimeError("quota")

    original_llm = tutor_coach.llm
    tutor_coach.llm = FailingLLM()
    try:
        envelope = tutor_coach.build_envelope(
            _state(original_question="mình không hiểu")
        )
    finally:
        tutor_coach.llm = original_llm
    assert envelope["asked_check_question"] is True
    assert len(envelope["follow_ups"]) >= 2


def test_llm_failure_quiet_in_remember_turn():
    # remember_turn không ném lỗi kể cả khi memory lỗi
    tutor_coach.remember_turn(
        _state(learner_id="bad id!", original_question="x"),
        {"misconceptions": []},
    )


# ── A-06 memory store ────────────────────────────────────────────────────────

def test_memory_empty_for_unknown_learner():
    state = memory_store.get_state("khong-ton-tai")
    assert state["questions"] == []
    assert state["concepts"] == []
    assert state["doc_id"] is None


def test_memory_upsert_and_bump_counts():
    memory_store.record_turn("u1", "RAG là gì?", doc_id="d10", page=3, concepts=["RAG"])
    state = memory_store.get_state("u1")
    assert state["doc_id"] == "d10"
    assert state["page"] == 3
    assert state["questions"][0]["count"] == 1

    memory_store.record_turn("u1", "RAG là gì?", doc_id="d10", page=4, concepts=["RAG"])
    state = memory_store.get_state("u1")
    assert state["questions"][0]["count"] == 2
    assert state["questions"][0]["name"] == "RAG là gì?"
    assert memory_store.repeated_questions("u1") == ["RAG là gì?"]


def test_memory_update_state_merge():
    memory_store.update_state("u2", concepts=["LLM"], misconceptions=["token vs embedding"])
    memory_store.update_state("u2", concepts=["RAG"], notes=["ôn bài"])
    state = memory_store.get_state("u2")
    assert {item["name"] for item in state["concepts"]} == {"LLM", "RAG"}
    assert "token vs embedding" in state["misconceptions"]
    assert state["notes"] == ["ôn bài"]


def test_memory_bad_learner_id_safe():
    assert memory_store.get_state("")["questions"] == []
    assert memory_store.get_state("a/b\\c;d")["questions"] == []


def test_memory_build_context_empty_when_no_data():
    assert memory_store.build_context("u-không-có") == ""


def test_memory_build_context_lists_concepts():
    memory_store.record_turn("u3", "embedding là gì?", concepts=["embedding"])
    context = memory_store.build_context("u3")
    assert "embedding" in context


def test_endpoint_state_router_uses_memory(monkeypatch):
    import server as server_module

    record = {"called": False}

    def fake_get_state(learner_id):
        record["called"] = True
        return {"learner_id": learner_id}

    monkeypatch.setattr(server_module, "get_state", fake_get_state)
    response = server_module.learner_state("abc123")
    assert record["called"] is True
    assert response["learner_id"] == "abc123"