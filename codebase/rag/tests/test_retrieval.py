from local_rag.models import Chunk
from local_rag.retrieval import HybridRetriever, bm25_scores


class FakeEmbedder:
    def embed_query(self, text):
        if "transformer" in text.casefold():
            return [1.0, 0.0]
        return [0.0, 1.0]

    def embed_documents(self, texts):
        raise NotImplementedError


def _chunk(chunk_id, text, vector, page):
    return Chunk(
        id=chunk_id,
        document_id="doc",
        source="paper.pdf",
        title="Paper",
        page=page,
        content=text,
        word_count=len(text.split()),
        embedding=tuple(vector),
    )


def test_bm25_prefers_exact_scientific_term():
    chunks = [
        _chunk("a", "transformer attention encoder", [1, 0], 1),
        _chunk("b", "convolution image network", [0, 1], 2),
    ]

    scores = bm25_scores("transformer encoder", chunks)

    assert scores[0] > scores[1]


def test_hybrid_search_returns_semantic_and_keyword_match_first():
    chunks = [
        _chunk("a", "transformer attention encoder", [1, 0], 1),
        _chunk("b", "convolution image network", [0, 1], 2),
        _chunk("c", "unrelated appendix", [-1, 0], 3),
    ]
    retriever = HybridRetriever(FakeEmbedder())

    results = retriever.search("transformer encoder", chunks, top_k=2)

    assert results[0].chunk_id == "a"
    assert results[0].keyword_score == 1.0
    assert len(results) == 2
