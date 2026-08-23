"""A-10 — learning analytics gaps tests (offline)."""

from types import SimpleNamespace

import pytest

from agent.analytics import build_gaps
from agent.analytics import gaps as gaps_module


class _T:
    def isoformat(self):
        return "2026-08-24"


@pytest.fixture(autouse=True)
def _tmp_runtime(monkeypatch, tmp_path):
    """Memory + observability tách riêng cho test."""
    from agent.memory import store as memory_store
    from agent.observability import trace as trace_module

    monkeypatch.setattr(memory_store, "MEMORY_DIR", tmp_path / "memory")
    monkeypatch.setattr(trace_module, "OBS_DIR", tmp_path / "obs")


def _seed(learner_id: str, concepts=None, misconceptions=None):
    from agent.memory.store import record_turn

    for concept in concepts or []:
        record_turn(learner_id, f"{concept} là gì?", concepts=[concept])
        record_turn(learner_id, f"{concept} là gì?", concepts=[concept])
    record_turn(learner_id, "x", misconceptions=misconceptions or [])


def _seed_trace(learner_id: str, errors: int = 0, ok: int = 1):
    from agent.observability.trace import record_trace

    for _ in range(ok):
        record_trace(
            trace_id="t-ok", mode="normal", intent="slide",
            tools=["slide_search"], learner_id=learner_id,
        )
    for i in range(errors):
        record_trace(
            trace_id=f"t-err-{i}", mode="normal", intent="slide",
            tools=["slide_search"], error="boom", learner_id=learner_id,
        )


def test_gaps_empty_for_unknown_learner(monkeypatch):
    monkeypatch.setattr(gaps_module, "slide_index", SimpleNamespace(retrieve=lambda *a, **k: []))
    result = build_gaps("khong-co")
    assert result["gaps"] == []
    assert result["signals_total"] == 0


def test_gaps_ranks_concepts_by_count(monkeypatch):
    _seed("u1", concepts=["RAG", "embedding"])
    monkeypatch.setattr(
        gaps_module, "slide_index",
        SimpleNamespace(retrieve=lambda *a, **k: [{"doc_id": "d10", "page": 3}]),
    )
    result = build_gaps("u1")
    assert [g["concept"] for g in result["gaps"]] == ["RAG", "embedding"]  # count 2 > 1
    assert result["gaps"][0]["ask_count"] == 2
    assert result["gaps"][0]["related_docs"][0]["doc_id"] == "d10"
    assert result["signals_total"] >= 3  # 2+2 counts + ... → hiện card


def test_gaps_includes_misconceptions_and_errors(monkeypatch):
    _seed("u2", concepts=["ReAct"], misconceptions=["Nhầm React/ReAct"])
    _seed_trace("u2", errors=2, ok=3)
    monkeypatch.setattr(gaps_module, "slide_index", SimpleNamespace(retrieve=lambda *a, **k: []))
    result = build_gaps("u2")
    assert result["errors"] == 2
    assert result["traces"] == 5
    assert result["gaps"][0]["misconception"] is not None
    assert result["signals_total"] >= 5  # 2 (counts) + 1 (misconception) + 2 (errors)


def test_gaps_avg_rating_from_feedback(monkeypatch, tmp_path):
    from agent.observability import trace as trace_module
    from agent.observability.trace import record_feedback, record_trace

    record_trace(trace_id="t-r1", mode="normal", intent="slide",
                 tools=["slide_search"], learner_id="u3")
    record_trace(trace_id="t-r2", mode="normal", intent="slide",
                 tools=["slide_search"], learner_id="u3")
    record_feedback("t-r1", 1)
    record_feedback("t-r2", -1)
    monkeypatch.setattr(gaps_module, "slide_index", SimpleNamespace(retrieve=lambda *a, **k: []))
    result = build_gaps("u3")
    assert result["avg_rating"] == 0.0
    assert result["traces"] == 2


def test_gaps_suggestion_text(monkeypatch):
    _seed("u4", concepts=["token"])
    monkeypatch.setattr(gaps_module, "slide_index", SimpleNamespace(retrieve=lambda *a, **k: [{"doc_id": "d6", "page": 2}]))
    result = build_gaps("u4")
    assert result["gaps"][0]["suggestion"].startswith("Ôn lại")
    assert result["gaps"][0]["related_docs"][0]["page"] == 2

# ── P0-4: notes persist + sync qua Memory ────────────────────────────────────

def test_set_get_page_note_roundtrip():
    from agent.memory import get_page_notes, set_page_note

    set_page_note("note-learner", "d9", 7, "nhớ: attention là gì")
    set_page_note("note-learner", "d9", 12, "ôn lại token")
    notes = get_page_notes("note-learner", doc_id="d9")
    assert [n["page"] for n in notes] == [7, 12]
    assert notes[0]["text"] == "nhớ: attention là gì"


def test_set_page_note_empty_deletes():
    from agent.memory import get_page_notes, set_page_note

    set_page_note("note-learner2", "d10", 3, "abc")
    set_page_note("note-learner2", "d10", 3, "   ")
    assert get_page_notes("note-learner2", doc_id="d10") == []


def test_page_note_upsert_replaces_same_page():
    from agent.memory import get_page_notes, set_page_note

    set_page_note("note-learner3", "d6", 5, "v1")
    set_page_note("note-learner3", "d6", 5, "v2")
    notes = get_page_notes("note-learner3", doc_id="d6")
    assert len(notes) == 1
    assert notes[0]["text"] == "v2"


def test_notes_endpoint_put_get(monkeypatch):
    import server

    monkeypatch.setattr(
        server, "set_page_note",
        lambda learner, doc, page, text: {
            "page_notes": [{"doc_id": doc, "page": page, "text": text}],
        },
    )
    resp = server.learner_note_upsert("l", server.NoteRequest(doc_id="d1", page=2, text="abc"))
    assert resp["ok"] is True
    assert resp["note"]["text"] == "abc"
