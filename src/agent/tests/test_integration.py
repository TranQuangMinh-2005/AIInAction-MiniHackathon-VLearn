from agent.config import PAPER_RAG_ROOT
from agent.nodes.answer import without_slide_citations
from agent.nodes import web_search
from agent.security import validate_input
from agent.tools import research


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


def test_local_paper_tool_preserves_exact_quote(monkeypatch):
    monkeypatch.setattr(
        research,
        "ask_research_papers",
        lambda **_: {
            "answer": "Kết quả [S1].",
            "grounded": True,
            "citations": [
                {
                    "label": "S1",
                    "source": "paper.pdf",
                    "page": 2,
                    "quote": "Exact evidence span.",
                    "claim": "Supported claim.",
                    "entailed": True,
                }
            ],
        },
    )

    context, citations = research.query_local_papers("question")

    assert '"Exact evidence span."' in context
    assert citations == ["paper.pdf - Trang 2 [S1]"]


def test_research_node_combines_all_tools(monkeypatch):
    monkeypatch.setattr(
        web_search,
        "query_local_papers",
        lambda _: ("LOCAL", ["paper.pdf - Trang 1 [S1]"]),
    )
    monkeypatch.setattr(
        web_search,
        "query_arxiv",
        lambda _: ("ARXIV", ["arXiv: title - https://arxiv.org/abs/1"]),
    )
    monkeypatch.setattr(
        web_search,
        "search_web",
        lambda *_args, **_kwargs: [
            {"title": "Web", "url": "https://example.com", "snippet": "Text"}
        ],
    )

    result = web_search.search_online(
        {
            "user_question": "question",
            "slide_title": "",
            "citations": ["D1 - Trang 1"],
        }
    )

    assert "LOCAL" in result["web_search_result"]
    assert "ARXIV" in result["web_search_result"]
    assert "KẾT QUẢ TÌM KIẾM WEB" in result["web_search_result"]
    assert len(result["citations"]) == 3
