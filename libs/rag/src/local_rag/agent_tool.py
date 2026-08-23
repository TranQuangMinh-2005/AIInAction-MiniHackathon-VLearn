from __future__ import annotations

from functools import lru_cache
from typing import Any

from .service import RAGService


TOOL_SCHEMA: dict[str, Any] = {
    "type": "function",
    "name": "ask_research_papers",
    "description": (
        "Answer a question using the locally indexed scientific-paper PDFs. "
        "Returns page-level citations and reports when evidence is insufficient."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "Question about the indexed scientific papers.",
            },
            "top_k": {
                "type": "integer",
                "minimum": 1,
                "maximum": 12,
                "default": 6,
                "description": "Maximum number of evidence excerpts to retrieve.",
            },
            "source": {
                "type": "string",
                "description": (
                    "Optional PDF filename or paper title. Set this when the "
                    "user asks about one specific paper. Omit this field when "
                    "the user does not select a paper."
                ),
            },
        },
        "required": ["question"],
        "additionalProperties": False,
    },
}


@lru_cache(maxsize=1)
def _service() -> RAGService:
    return RAGService.from_env()


def ask_research_papers(
    question: str, top_k: int = 6, source: str | None = None
) -> dict[str, Any]:
    """Stable Python boundary intended for another Agent to call."""
    if not 1 <= top_k <= 12:
        raise ValueError("top_k must be between 1 and 12")
    return _service().ask(
        question, top_k=top_k, source=source
    ).to_dict()
