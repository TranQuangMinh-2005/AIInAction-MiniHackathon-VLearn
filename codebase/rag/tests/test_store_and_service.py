from pathlib import Path

from local_rag.config import Settings
from local_rag.models import Citation, Chunk, Document
from local_rag.service import RAGService
from local_rag.store import SQLiteStore


class FakeEmbedder:
    def embed_query(self, text):
        return [1.0, 0.0]

    def embed_documents(self, texts):
        return [[1.0, 0.0] for _ in texts]


class FakeAnswerer:
    def answer(self, question, sources):
        citation = Citation(
            label="S1",
            title=sources[0].title,
            source=sources[0].source,
            page=sources[0].page,
            quote=sources[0].content,
        )
        return "Supported answer [S1]", (citation,), True


def _settings(path: Path) -> Settings:
    return Settings(
        index_path=path,
        pdf_dir=path.parent / "pdfs",
        provider="openai",
        chat_model="fake-chat",
        embedding_model="fake-embedding",
        reasoning_effort="low",
        gemini_embedding_dimensions=768,
        top_k=3,
        chunk_words=100,
        chunk_overlap_words=20,
        embedding_batch_size=16,
    )


def test_store_round_trip_and_service_answer(tmp_path):
    settings = _settings(tmp_path / "index.sqlite3")
    store = SQLiteStore(settings.index_path)
    document = Document("doc", "paper.pdf", "Paper", "hash", 1)
    chunk = Chunk(
        id="chunk",
        document_id="doc",
        source="paper.pdf",
        title="Paper",
        page=4,
        content="The method improves retrieval accuracy.",
        word_count=5,
        embedding=(1.0, 0.0),
    )
    store.save_document(document, [chunk], "openai:fake-embedding")
    service = RAGService(
        settings,
        embedder=FakeEmbedder(),
        answerer=FakeAnswerer(),
        store=store,
    )

    result = service.ask("What improves retrieval?")

    assert result.grounded is True
    assert result.citations[0].page == 4
    assert result.retrieval[0].source == "paper.pdf"
    assert store.stats()["chunks"] == 1


def test_embedding_model_mismatch_is_rejected(tmp_path):
    settings = _settings(tmp_path / "index.sqlite3")
    store = SQLiteStore(settings.index_path)
    document = Document("doc", "paper.pdf", "Paper", "hash", 1)
    chunk = Chunk(
        "chunk", "doc", "paper.pdf", "Paper", 1, "content", 1, (1.0, 0.0)
    )
    store.save_document(document, [chunk], "other-model")
    service = RAGService(
        settings,
        embedder=FakeEmbedder(),
        answerer=FakeAnswerer(),
        store=store,
    )

    try:
        service.search("question")
    except RuntimeError as exc:
        assert "Embedding model mismatch" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError")


def test_ingest_append_rejects_embedding_model_mismatch(tmp_path):
    settings = _settings(tmp_path / "index.sqlite3")
    settings.pdf_dir.mkdir()
    store = SQLiteStore(settings.index_path)
    document = Document("doc", "paper.pdf", "Paper", "hash", 1)
    chunk = Chunk(
        "chunk", "doc", "paper.pdf", "Paper", 1, "content", 1, (1.0, 0.0)
    )
    store.save_document(document, [chunk], "other-model")
    service = RAGService(
        settings,
        embedder=FakeEmbedder(),
        answerer=FakeAnswerer(),
        store=store,
    )

    try:
        service.ingest_directory(reset=False)
    except RuntimeError as exc:
        assert "Embedding model mismatch" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError")


def test_question_filename_filters_retrieval_to_one_document(tmp_path):
    settings = _settings(tmp_path / "index.sqlite3")
    store = SQLiteStore(settings.index_path)
    first_document = Document(
        "doc-a", "W-Online-payment.pdf", "Online Payment", "hash-a", 1
    )
    second_document = Document(
        "doc-b", "Other-paper.pdf", "Other Paper", "hash-b", 1
    )
    first_chunk = Chunk(
        "chunk-a",
        "doc-a",
        "W-Online-payment.pdf",
        "Online Payment",
        1,
        "fraud risk evidence",
        3,
        (1.0, 0.0),
        "Abstract",
    )
    second_chunk = Chunk(
        "chunk-b",
        "doc-b",
        "Other-paper.pdf",
        "Other Paper",
        1,
        "fraud risk evidence",
        3,
        (1.0, 0.0),
        "Abstract",
    )
    store.save_document(
        first_document, [first_chunk], "openai:fake-embedding"
    )
    store.save_document(
        second_document, [second_chunk], "openai:fake-embedding"
    )
    service = RAGService(
        settings,
        embedder=FakeEmbedder(),
        answerer=FakeAnswerer(),
        store=store,
    )

    results = service.search(
        "Summarize W-Online-payment", top_k=5
    )

    assert {result.source for result in results} == {
        "W-Online-payment.pdf"
    }
