"""t41 — Example Teacher tests (offline)."""

from types import SimpleNamespace

import pytest

from agent.nodes.examples import generate_examples, example_token_chunks


@pytest.fixture(autouse=True)
def _fake_index(monkeypatch):
    from agent.nodes import examples

    monkeypatch.setattr(
        examples.slide_index,
        "page_texts",
        [
            {"doc_id": "d10", "page": 16, "text": "Retrieval là bước quan trọng nhất trong RAG pipeline."},
            {"doc_id": "d10", "page": 17, "text": "Pre-RAG: query transformation."},
        ],
    )


def test_generate_examples_returns_pedagogy_structure(monkeypatch):
    calls = {}

    def fake_invoke(prompt):
        calls["prompt"] = prompt
        return SimpleNamespace(
            content=(
                "## Ví dụ thực tế\n- Ví dụ tìm đúng chứng cứ … (D10 - Trang 16)\n\n"
                "## Câu hỏi ôn tập\n- Q1: Retrieval quan trọng thế nào? – A: …"
            )
        )

    monkeypatch.setattr("agent.nodes.examples.llm", SimpleNamespace(invoke=fake_invoke))
    result = generate_examples(
        {
            "user_question": "Cho mình ví dụ thực tế hoặc câu hỏi ôn tập về phần này",
            "active_doc_id": "d10",
            "current_page": 16,
            "final_answer": None,
            "citations": [],
            "citation_details": [],
        }
    )
    assert "## Ví dụ thực tế" in result["final_answer"]
    assert "## Câu hỏi ôn tập" in result["final_answer"]
    assert result["citations"] == ["D10 - Trang 16"]
    assert "Trang 16" in calls["prompt"]


def test_generate_examples_empty_context_uses_clear_message(monkeypatch):
    from agent.nodes import examples as examples_module

    monkeypatch.setattr(examples_module.slide_index, "page_texts", [])
    monkeypatch.setattr(
        examples_module.slide_index, "retrieve_context", lambda *_a, **_k: ("", []), raising=False
    )
    result = generate_examples(
        {
            "user_question": "cho ví dụ về phần này",
            "active_doc_id": "d10",
            "current_page": 99,
            "final_answer": None,
            "citations": [],
            "citation_details": [],
        }
    )
    assert "không có nội dung" in result["final_answer"]
    assert "Rất tiếc" not in result["final_answer"]


def test_example_token_chunks_reassemble():
    text = "## Ví dụ thực tế\n\nĐoạn mẫu.\n\n## Câu hỏi ôn tập\n\n" + ("từ lặp " * 90)
    chunks = example_token_chunks(text)
    assert "".join(chunks) == text
    assert all(len(c) <= 400 for c in chunks)


def test_graph_routes_example_intent(monkeypatch):
    from agent.graph import build_graph
    from agent.nodes import orchestrator

    monkeypatch.setattr(
        orchestrator,
        "llm",
        SimpleNamespace(
            invoke=lambda _p: SimpleNamespace(
                content='{"intent": "example", "reason": "xin ví dụ"}'
            )
        ),
    )
    monkeypatch.setattr(
        "agent.nodes.examples.llm",
        SimpleNamespace(
            invoke=lambda _p: SimpleNamespace(
                content="## Ví dụ thực tế\n- ví dụ A\n\n## Câu hỏi ôn tập\n- Q?"
            )
        ),
    )
    graph = build_graph()
    result = graph.invoke(
        {
            "user_question": "cho mình ví dụ thực tế về phần này",
            "slide_context": "ctx",
            "current_page": 16,
            "slide_title": "Day 8 — RAG Pipeline",
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
            "original_question": "cho mình ví dụ thực tế về phần này",
            "normalized_question": None,
            "intent": None,
            "orchestrator_note": None,
            "retrieval_scope": "auto",
            "active_doc_id": "d10",
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
    assert "## Ví dụ thực tế" in result["final_answer"]
    assert result["intent"] == "example"
