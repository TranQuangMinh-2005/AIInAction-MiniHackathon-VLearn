from types import SimpleNamespace

from agent.config import PAPER_RAG_ROOT
from agent.nodes.answer import without_slide_citations
from agent.nodes import web_search
from agent.providers import GeminiChat
from agent.security import validate_input
from agent.tools import research
from agent.tools.research import build_arxiv_query
from server import citations_used_in_answer


def test_fraud_paper_question_is_not_blocked():
    safe, reason = validate_input(
        "Bài báo phát hiện fraud bằng LightGBM như thế nào?"
    )
    assert safe is True
    assert reason == ""


def test_integrated_rag_paths_are_absolute():
    import os

    assert os.path.isabs(os.environ["RAG_INDEX_PATH"])
    assert os.environ["RAG_INDEX_PATH"].startswith(str(PAPER_RAG_ROOT))


def test_external_answer_drops_irrelevant_slide_citation():
    assert without_slide_citations(
        ["D1 - Trang 21", "paper.pdf - Trang 1 [S1]"]
    ) == ["paper.pdf - Trang 1 [S1]"]


def test_stream_only_returns_citations_used_in_answer():
    assert citations_used_in_answer(
        [
            "paper.pdf - Trang 1 [PAPER-1]",
            "paper.pdf - Trang 3 [PAPER-2]",
        ],
        "Supported result [PAPER-1].",
    ) == ["paper.pdf - Trang 1 [PAPER-1]"]


def test_gemini_stream_falls_back_before_first_token():
    class RateLimited(Exception):
        code = 429

    class FakeModels:
        def generate_content_stream(self, *, model, **_kwargs):
            if model == "primary":
                raise RateLimited()
            return iter([SimpleNamespace(text="fallback worked")])

    chat = GeminiChat.__new__(GeminiChat)
    chat.client = SimpleNamespace(models=FakeModels())
    chat.model = "primary"
    chat.models = ["primary", "fallback"]
    chat.temperature = 0.1

    chunks = list(chat.stream("question"))

    assert [chunk.content for chunk in chunks] == ["fallback worked"]


def test_local_paper_fast_path_returns_bounded_evidence(monkeypatch):
    fake_service = SimpleNamespace(
        resolve_source=lambda _: "paper.pdf",
        search=lambda *_args, **_kwargs: [
            SimpleNamespace(
                title="Paper",
                source="paper.pdf",
                page=2,
                section="Results",
                content="Exact retrieved evidence.",
            )
        ],
    )
    monkeypatch.setattr(
        research,
        "_paper_service",
        lambda: fake_service,
    )

    context, citations = research.query_local_papers("question")

    assert "Exact retrieved evidence." in context
    assert citations == ["paper.pdf - Trang 2 [PAPER-1]"]


def test_research_node_short_circuits_arxiv_for_named_local_pdf(
    monkeypatch,
):
    monkeypatch.setattr(
        web_search,
        "query_local_papers",
        lambda _: ("LOCAL", ["paper.pdf - Trang 1 [PAPER-1]"]),
    )
    monkeypatch.setattr(
        web_search,
        "query_arxiv",
        lambda _: (_ for _ in ()).throw(
            AssertionError("arXiv must not run for a named local PDF")
        ),
    )

    result = web_search.search_online(
        {
            "user_question": "question",
            "slide_title": "",
            "citations": ["D1 - Trang 1"],
        }
    )

    assert "LOCAL" in result["web_search_result"]
    assert result["citations"][-1].endswith("[PAPER-1]")


def test_research_node_uses_arxiv_when_no_local_pdf_matches(monkeypatch):
    monkeypatch.setattr(
        web_search,
        "query_local_papers",
        lambda _: ("", []),
    )
    monkeypatch.setattr(
        web_search,
        "query_arxiv",
        lambda _: ("ARXIV", ["arXiv: title - https://arxiv.org/abs/1"]),
    )

    result = web_search.search_online(
        {
            "user_question": "new topic",
            "slide_title": "",
            "citations": [],
        }
    )

    assert result["web_search_result"] == "ARXIV"
    assert len(result["citations"]) == 1


def test_arxiv_query_removes_demo_instruction_words():
    assert build_arxiv_query(
        "Tìm các paper về retrieval augmented generation "
        "và tóm tắt đóng góp chính"
    ) == "retrieval augmented generation"
