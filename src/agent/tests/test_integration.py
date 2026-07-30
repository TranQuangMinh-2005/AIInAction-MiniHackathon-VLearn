from types import SimpleNamespace

import server
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


def test_research_answer_without_marker_returns_no_paper_citation():
    assert citations_used_in_answer(
        ["paper.pdf - Trang 1 [PAPER-1]"],
        "An answer without a source marker.",
    ) == []


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
    evidence = "Beginning " + ("support " * 200) + "exact ending result."
    fake_service = SimpleNamespace(
        resolve_source=lambda _: "paper.pdf",
        search=lambda *_args, **_kwargs: [
            SimpleNamespace(
                title="Paper",
                source="paper.pdf",
                page=2,
                section="Results",
                content=evidence,
                line_start=10,
                line_end=12,
            )
        ],
    )
    monkeypatch.setattr(
        research,
        "_paper_service",
        lambda: fake_service,
    )

    context, citations, details = research.query_local_papers(
        "question",
        "paper.pdf",
    )

    assert evidence in context
    assert citations == [
        "paper.pdf - Trang 2, dòng 10-12 [PAPER-1]"
    ]
    assert details[0]["line_start"] == 10
    assert details[0]["quote"].endswith("exact ending result.")


def test_research_node_forces_selected_local_pdf(
    monkeypatch,
):
    monkeypatch.setattr(
        web_search,
        "query_local_papers",
        lambda question, source: (
            f"LOCAL:{question}:{source}",
            ["paper.pdf - Trang 1, dòng 2-4 [PAPER-1]"],
            [
                {
                    "label": "PAPER-1",
                    "source": source,
                    "page": 1,
                    "line_start": 2,
                    "line_end": 4,
                    "quote": "Evidence",
                }
            ],
        ),
    )

    result = web_search.search_online(
        {
            "user_question": "question",
            "paper_source": "paper.pdf",
            "slide_title": "",
            "citations": ["D1 - Trang 1"],
            "citation_details": [],
        }
    )

    assert result["web_search_result"] == "LOCAL:question:paper.pdf"
    assert result["citations"][-1].endswith("[PAPER-1]")
    assert result["citation_details"][0]["source"] == "paper.pdf"


def test_research_node_requires_selected_paper():
    result = web_search.search_online(
        {
            "user_question": "new topic",
            "paper_source": None,
            "slide_title": "",
            "citations": [],
            "citation_details": [],
        }
    )

    assert "chọn một paper" in result["web_search_result"]
    assert result["citations"] == []


def test_arxiv_query_removes_demo_instruction_words():
    assert build_arxiv_query(
        "Tìm các paper về retrieval augmented generation "
        "và tóm tắt đóng góp chính"
    ) == "retrieval augmented generation"


def test_import_arxiv_downloads_one_pdf_and_indexes_it(
    monkeypatch,
    tmp_path,
):
    document = {
        "source": "arxiv-1234.5678.pdf",
        "title": "Imported Paper",
        "page_count": 8,
    }
    fake_service = SimpleNamespace(
        settings=SimpleNamespace(pdf_dir=tmp_path),
        ingest_directory=lambda reset=False: SimpleNamespace(
            to_dict=lambda: {
                "discovered_files": 1,
                "indexed_files": 1,
                "skipped_files": 0,
                "indexed_chunks": 3,
            }
        ),
        documents=lambda: [document],
    )
    monkeypatch.setattr(
        server,
        "arxiv_search",
        lambda query, max_results: [
            {
                "title": "Imported Paper",
                "abstract_url": "https://arxiv.org/abs/1234.5678",
                "pdf_url": "https://arxiv.org/pdf/1234.5678",
            }
        ],
    )
    monkeypatch.setattr(
        server,
        "arxiv_download_pdf",
        lambda _url: b"%PDF-1.4 mock",
    )
    monkeypatch.setattr(
        server,
        "RAGService",
        SimpleNamespace(from_env=lambda: fake_service),
    )

    response = server.import_arxiv_paper(
        server.PaperImportRequest(query="retrieval augmented generation")
    )

    assert response["paper"] == document
    assert response["ingest"]["indexed_files"] == 1
    assert (tmp_path / "arxiv-1234.5678.pdf").read_bytes().startswith(
        b"%PDF"
    )
