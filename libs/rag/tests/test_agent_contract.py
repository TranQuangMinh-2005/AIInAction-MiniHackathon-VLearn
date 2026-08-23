from types import SimpleNamespace

from fastapi.testclient import TestClient

import local_rag.agent_tool as agent_tool
import local_rag.api as api_module


RESPONSE = {
    "answer": "Supported answer [S1].",
    "grounded": True,
    "citations": [],
    "retrieval": [],
}


class FakeService:
    def __init__(self):
        self.calls = []

    def ask(self, question, top_k=6, source=None):
        self.calls.append((question, top_k, source))
        return SimpleNamespace(to_dict=lambda: RESPONSE)

    def health(self):
        return {"status": "ok"}


def test_python_agent_tool_keeps_question_only_backward_compatibility(
    monkeypatch,
):
    service = FakeService()
    monkeypatch.setattr(agent_tool, "_service", lambda: service)

    result = agent_tool.ask_research_papers("Question?")

    assert result == RESPONSE
    assert service.calls == [("Question?", 6, None)]
    assert agent_tool.TOOL_SCHEMA["parameters"]["required"] == ["question"]


def test_http_ask_accepts_minimal_v1_request(monkeypatch):
    service = FakeService()
    monkeypatch.setattr(api_module, "get_service", lambda: service)
    client = TestClient(api_module.app)

    response = client.post("/ask", json={"question": "Question?"})

    assert response.status_code == 200
    assert response.json() == RESPONSE
    assert service.calls == [("Question?", 6, None)]


def test_http_ask_forwards_optional_source(monkeypatch):
    service = FakeService()
    monkeypatch.setattr(api_module, "get_service", lambda: service)
    client = TestClient(api_module.app)

    response = client.post(
        "/ask",
        json={
            "question": "Question?",
            "top_k": 4,
            "source": "paper.pdf",
        },
    )

    assert response.status_code == 200
    assert service.calls == [("Question?", 4, "paper.pdf")]
