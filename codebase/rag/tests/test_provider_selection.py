from local_rag.config import Settings


def _clear_model_overrides(monkeypatch):
    monkeypatch.delenv("RAG_CHAT_MODEL", raising=False)
    monkeypatch.delenv("RAG_EMBEDDING_MODEL", raising=False)


def test_auto_prefers_openai_when_both_keys_exist(monkeypatch):
    monkeypatch.setenv("RAG_PROVIDER", "auto")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    _clear_model_overrides(monkeypatch)

    settings = Settings.from_env()

    assert settings.provider == "openai"
    assert settings.embedding_model == "text-embedding-3-large"


def test_auto_uses_gemini_without_openai_key(monkeypatch):
    monkeypatch.setenv("RAG_PROVIDER", "auto")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    _clear_model_overrides(monkeypatch)

    settings = Settings.from_env()

    assert settings.provider == "gemini"
    assert settings.chat_model == "gemini-3.6-flash"
    assert settings.embedding_model == "gemini-embedding-2"


def test_explicit_gemini_wins_when_both_keys_exist(monkeypatch):
    monkeypatch.setenv("RAG_PROVIDER", "gemini")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    _clear_model_overrides(monkeypatch)

    assert Settings.from_env().provider == "gemini"
