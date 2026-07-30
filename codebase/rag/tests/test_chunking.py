from local_rag.chunking import chunk_document
from local_rag.models import Document, PDFPage


def test_chunks_stay_on_one_page_and_keep_overlap():
    document = Document(
        id="doc",
        source="paper.pdf",
        title="Paper",
        file_sha256="abc",
        page_count=2,
    )
    pages = (
        PDFPage(1, "one two three four five six seven eight"),
        PDFPage(2, "alpha beta gamma"),
    )

    chunks = chunk_document(
        document, pages, chunk_words=5, overlap_words=2
    )

    assert [chunk.page for chunk in chunks] == [1, 1, 2]
    assert chunks[0].content == "one two three four five"
    assert chunks[1].content.startswith("four five")
    assert chunks[2].content == "alpha beta gamma"
    assert (chunks[0].line_start, chunks[0].line_end) == (1, 1)


def test_rejects_invalid_overlap():
    document = Document("d", "x.pdf", "X", "hash", 1)
    pages = (PDFPage(1, "some text"),)

    try:
        chunk_document(document, pages, chunk_words=5, overlap_words=5)
    except ValueError as exc:
        assert "overlap_words" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_detects_sections_and_keeps_them_on_chunks():
    document = Document("d", "paper.pdf", "Paper", "hash", 1)
    pages = (
        PDFPage(
            1,
            "Abstract\nMain finding with evidence.\n"
            "Introduction\nBackground and motivation.",
        ),
    )

    chunks = chunk_document(
        document, pages, chunk_words=20, overlap_words=2
    )

    assert [chunk.section for chunk in chunks] == [
        "Abstract",
        "Introduction",
    ]
    assert (chunks[0].line_start, chunks[0].line_end) == (2, 2)
    assert (chunks[1].line_start, chunks[1].line_end) == (4, 4)
