"""Shared configuration for the integrated Agent + local paper RAG."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[3]
AGENT_ROOT = REPO_ROOT / "src" / "agent"
PAPER_RAG_ROOT = REPO_ROOT / "codebase" / "rag"


def load_environment() -> None:
    """Load local secrets without requiring one specific working directory."""
    for env_file in (
        REPO_ROOT / ".env",
        AGENT_ROOT / ".env",
        PAPER_RAG_ROOT / ".env",
    ):
        if env_file.exists():
            load_dotenv(env_file, override=False)

    # The standalone RAG intentionally uses paths relative to its own folder.
    # Make those same values deterministic when it is imported by the Agent.
    for name, default in (
        ("RAG_INDEX_PATH", ".rag/index.sqlite3"),
        ("RAG_PDF_DIR", "data/papers"),
    ):
        value = Path(os.getenv(name, default)).expanduser()
        if not value.is_absolute():
            os.environ[name] = str((PAPER_RAG_ROOT / value).resolve())


load_environment()
