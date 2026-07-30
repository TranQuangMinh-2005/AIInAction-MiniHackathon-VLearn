from types import SimpleNamespace
import json

from local_rag.gemini_clients import (
    GeminiAnswerProvider,
    GeminiEmbeddingProvider,
)
from local_rag.models import SearchResult
import local_rag.gemini_clients as gemini_module


class FakeModels:
    def __init__(self):
        self.embedding_calls = []

    def embed_content(self, **kwargs):
        self.embedding_calls.append(kwargs)
        return SimpleNamespace(
            embeddings=[
                SimpleNamespace(values=[1.0, 0.0])
                for _ in kwargs["contents"]
            ]
        )

    def generate_content(self, **kwargs):
        if kwargs.get("config", {}).get("response_mime_type") == "application/json":
            return SimpleNamespace(
                text=json.dumps(
                    {
                        "all_claims_supported": True,
                        "items": [
                            {
                                "id": "C1",
                                "entailed": True,
                                "quote": "Supporting evidence.",
                                "reason": "Exact support.",
                            }
                        ],
                    }
                )
            )
        return SimpleNamespace(text="The evidence supports this [S1].")


def _fake_client():
    return SimpleNamespace(models=FakeModels())


def _source():
    return SearchResult(
        chunk_id="chunk",
        source="paper.pdf",
        title="Paper",
        page=3,
        content="Supporting evidence.",
        score=0.9,
        dense_score=0.8,
        keyword_score=1.0,
    )


def test_gemini_uses_asymmetric_embedding_task_types():
    provider = GeminiEmbeddingProvider.__new__(GeminiEmbeddingProvider)
    provider.model = "gemini-embedding-2"
    provider.batch_size = 64
    provider.dimensions = 768
    provider.client = _fake_client()

    provider.embed_documents(["document"])
    provider.embed_query("question")

    calls = provider.client.models.embedding_calls
    assert calls[0]["config"]["task_type"] == "RETRIEVAL_DOCUMENT"
    assert calls[1]["config"]["task_type"] == "RETRIEVAL_QUERY"
    assert calls[0]["config"]["output_dimensionality"] == 768


def test_gemini_answer_preserves_structured_citation():
    provider = GeminiAnswerProvider.__new__(GeminiAnswerProvider)
    provider.model = "gemini-3.6-flash"
    provider.client = _fake_client()

    text, citations, grounded = provider.answer("Question?", [_source()])

    assert text.endswith("[S1].")
    assert citations[0].page == 3
    assert grounded is True


def test_gemini_embedding_retries_sdk_quota_error(monkeypatch):
    class QuotaError(Exception):
        code = 429

    class FlakyModels(FakeModels):
        def __init__(self):
            super().__init__()
            self.attempts = 0

        def embed_content(self, **kwargs):
            self.attempts += 1
            if self.attempts == 1:
                raise QuotaError()
            return super().embed_content(**kwargs)

    provider = GeminiEmbeddingProvider.__new__(GeminiEmbeddingProvider)
    provider.model = "gemini-embedding-2"
    provider.batch_size = 64
    provider.dimensions = 768
    provider.client = SimpleNamespace(models=FlakyModels())
    monkeypatch.setattr(gemini_module.time, "sleep", lambda _: None)

    result = provider.embed_documents(["document"])

    assert result == [[1.0, 0.0]]
    assert provider.client.models.attempts == 2
