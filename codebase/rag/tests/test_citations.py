from local_rag.models import SearchResult
from local_rag.openai_clients import citations_from_answer


def _source(page):
    return SearchResult(
        chunk_id=str(page),
        source="paper.pdf",
        title="Paper",
        page=page,
        content=f"Evidence from page {page}",
        score=0.9,
        dense_score=0.8,
        keyword_score=1.0,
    )


def test_extracts_valid_unique_citations_in_answer_order():
    sources = [_source(2), _source(7)]

    citations = citations_from_answer(
        "First claim [S2], second [S1], repeated [S2].", sources
    )

    assert [citation.label for citation in citations] == ["S2", "S1"]
    assert [citation.page for citation in citations] == [7, 2]


def test_ignores_out_of_range_citations():
    assert citations_from_answer("Unsupported [S99]", [_source(1)]) == ()
