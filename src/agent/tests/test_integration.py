from types import SimpleNamespace

import server
from agent.config import PAPER_RAG_ROOT
from agent.nodes.answer import without_slide_citations
from agent.nodes import web_search
from agent.providers import GeminiChat
from agent.security import validate_input
from agent.tools import research
from agent.tools.paper import paper as paper_tool
from agent.tools.research import build_arxiv_query
from server import citation_details_used_in_answer, citations_used_in_answer


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


def test_combined_paper_markers_keep_each_citation_and_detail():
    answer = "Supported by two excerpts [PAPER-1, PAPER-2]."
    citations = [
        "paper.pdf - Trang 1 [PAPER-1]",
        "paper.pdf - Trang 3 [PAPER-2]",
    ]
    details = [
        {"label": "PAPER-1"},
        {"label": "PAPER-2"},
    ]

    assert citations_used_in_answer(citations, answer) == citations
    assert citation_details_used_in_answer(details, answer) == details


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


def test_auto_research_reranks_arxiv_before_using_exact_local_cache(
    monkeypatch,
):
    calls = []
    papers = [
        {
            "title": "Narrow RAG Variant",
            "summary": "A narrow variant.",
            "abstract_url": "https://arxiv.org/abs/1111.1111",
            "pdf_url": "https://arxiv.org/pdf/1111.1111",
        },
        {
            "title": "Retrieval Augmented Generation Survey",
            "summary": "A broad survey.",
            "abstract_url": "https://arxiv.org/abs/2222.2222",
            "pdf_url": "https://arxiv.org/pdf/2222.2222",
        },
    ]
    fake_service = SimpleNamespace(
        resolve_source=lambda source: (
            calls.append(("resolve", source)) or source
        ),
    )
    monkeypatch.setattr(research, "_paper_service", lambda: fake_service)
    monkeypatch.setattr(
        research,
        "arxiv_search",
        lambda query, max_results: (
            calls.append(("search", query, max_results)) or papers
        ),
    )
    monkeypatch.setattr(
        research,
        "arxiv_download_pdf",
        lambda _url: (_ for _ in ()).throw(
            AssertionError("cached paper must not be downloaded")
        ),
    )
    monkeypatch.setattr(
        research,
        "query_local_papers",
        lambda question, source: (
            f"{question}:{source}",
            ["citation"],
            [{"label": "PAPER-1"}],
        ),
    )

    result = research.query_arxiv_full_text(
        "RAG là gì?",
        "retrieval augmented generation survey foundations",
        paper_selector=lambda _question, _query, _papers: 1,
    )

    assert calls[0] == (
        "search",
        "retrieval augmented generation survey foundations",
        5,
    )
    assert calls[1] == ("resolve", "arxiv-2222.2222.pdf")
    assert "arxiv-2222.2222.pdf" in result[0]


def test_auto_research_downloads_only_the_reranked_arxiv_id(
    monkeypatch,
    tmp_path,
):
    downloaded = []
    papers = [
        {
            "title": "Incidental Deep Learning Mention",
            "summary": "A fraud paper that briefly mentions deep learning.",
            "abstract_url": "https://arxiv.org/abs/1111.1111",
            "pdf_url": "https://arxiv.org/pdf/1111.1111",
        },
        {
            "title": "Deep Learning Foundations",
            "summary": "A tutorial on deep learning foundations.",
            "abstract_url": "https://arxiv.org/abs/2222.2222",
            "pdf_url": "https://arxiv.org/pdf/2222.2222",
        },
    ]
    fake_service = SimpleNamespace(
        settings=SimpleNamespace(pdf_dir=tmp_path),
        resolve_source=lambda _source: None,
        ingest_directory=lambda reset=False: SimpleNamespace(),
    )
    monkeypatch.setattr(research, "_paper_service", lambda: fake_service)
    monkeypatch.setattr(
        research,
        "arxiv_search",
        lambda _query, max_results: papers,
    )
    monkeypatch.setattr(
        research,
        "arxiv_download_pdf",
        lambda url: downloaded.append(url) or b"%PDF-1.4 mock",
    )
    monkeypatch.setattr(
        research,
        "query_local_papers",
        lambda question, source: (
            f"{question}:{source}",
            ["citation"],
            [],
        ),
    )

    result = research.query_arxiv_full_text(
        "Deep learning là gì?",
        "deep learning survey tutorial foundations",
        paper_selector=lambda _question, _query, _papers: 1,
    )

    assert downloaded == ["https://arxiv.org/pdf/2222.2222"]
    assert (tmp_path / "arxiv-2222.2222.pdf").exists()
    assert "arxiv-2222.2222.pdf" in result[0]


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


def test_research_node_auto_searches_arxiv_without_selected_paper(
    monkeypatch,
):
    monkeypatch.setattr(
        web_search,
        "_build_research_query",
        lambda question, slide_context, history: (
            "retrieval augmented generation"
        ),
    )
    monkeypatch.setattr(
        web_search,
        "query_arxiv_full_text",
        lambda question, search_query, paper_selector: (
            f"ARXIV:{question}:{search_query}",
            ["arxiv-paper.pdf - Trang 2 [PAPER-1]"],
            [
                {
                    "label": "PAPER-1",
                    "source": "arxiv-paper.pdf",
                    "page": 2,
                    "quote": "Evidence",
                }
            ],
        ),
    )

    result = web_search.search_online(
        {
            "user_question": "new topic",
            "paper_source": None,
            "slide_context": "course context",
            "citations": [],
            "citation_details": [],
        }
    )

    assert result["web_search_result"].startswith("ARXIV:")
    assert result["citations"] == [
        "arxiv-paper.pdf - Trang 2 [PAPER-1]"
    ]


def test_research_node_rejects_out_of_scope_question(monkeypatch):
    monkeypatch.setattr(
        web_search,
        "_build_research_query",
        lambda question, slide_context, history: None,
    )

    result = web_search.search_online(
        {
            "user_question": "Thời tiết Paris hôm nay?",
            "paper_source": None,
            "slide_context": "AI course",
            "citations": [],
            "citation_details": [],
        }
    )

    assert "ngoài phạm vi" in result["web_search_result"]
    assert result["citations"] == []


def test_research_query_resolves_follow_up_from_history(monkeypatch):
    prompts = []

    class FakeLLM:
        def invoke(self, prompt):
            prompts.append(prompt)
            return SimpleNamespace(
                content=(
                    "generative adversarial networks limitations "
                    "training survey"
                )
            )

    monkeypatch.setattr(web_search, "llm", FakeLLM())

    query = web_search._build_research_query(
        "Nó có nhược điểm gì?",
        "AI, ML and Deep Learning",
        [
            {"role": "user", "content": "GAN là gì?"},
            {
                "role": "assistant",
                "content": "GAN là Generative Adversarial Network.",
            },
        ],
    )

    assert query.startswith("generative adversarial networks")
    assert "GAN là gì?" in prompts[0]
    assert "Nó có nhược điểm gì?" in prompts[0]


def test_arxiv_reranker_prefers_foundational_candidate(monkeypatch):
    prompts = []

    class FakeLLM:
        def invoke(self, prompt):
            prompts.append(prompt)
            return SimpleNamespace(content="2")

    monkeypatch.setattr(web_search, "llm", FakeLLM())

    selected = web_search._select_best_arxiv_paper(
        "GAN là gì?",
        "generative adversarial networks survey foundations",
        [
            {
                "title": "FIS-GAN",
                "summary": "A flow importance sampling GAN variant.",
            },
            {
                "title": "Generative Adversarial Networks: An Overview",
                "summary": "A broad tutorial and survey of GAN foundations.",
            },
        ],
    )

    assert selected == 1
    assert "tránh biến thể hẹp" in prompts[0]


def test_arxiv_query_removes_demo_instruction_words():
    assert build_arxiv_query(
        "Tìm các paper về retrieval augmented generation "
        "và tóm tắt đóng góp chính"
    ) == "retrieval augmented generation"


def test_arxiv_empty_api_result_uses_discovery_fallback(monkeypatch):
    response = SimpleNamespace(
        status_code=200,
        text=(
            '<?xml version="1.0"?>'
            '<feed xmlns="http://www.w3.org/2005/Atom"></feed>'
        ),
        raise_for_status=lambda: None,
    )
    fallback = [
        {
            "title": "Deep Learning Survey",
            "abstract_url": "https://arxiv.org/abs/1234.5678",
            "pdf_url": "https://arxiv.org/pdf/1234.5678",
        }
    ]
    monkeypatch.setattr(paper_tool, "_request", lambda *_args, **_kwargs: response)
    monkeypatch.setattr(
        paper_tool,
        "_search_duckduckgo_arxiv",
        lambda query, max_results: fallback,
    )

    assert paper_tool.arxiv_search("deep learning", 1) == fallback


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
