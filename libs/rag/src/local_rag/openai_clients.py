from __future__ import annotations

import os
import re
from typing import Protocol, Sequence

from .models import Citation, SearchResult
from .grounding import (
    apply_verification,
    build_verification_prompt,
    claim_references,
    parse_json_object,
)


class EmbeddingProvider(Protocol):
    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class AnswerProvider(Protocol):
    def answer(
        self, question: str, sources: Sequence[SearchResult]
    ) -> tuple[str, tuple[Citation, ...], bool]: ...


GROUNDING_SYSTEM_PROMPT = """You answer questions using only the supplied paper excerpts.

Rules:
- Use no outside facts, even if you know the topic.
- Every factual claim must have an inline citation such as [S1].
- Keep claims atomic: use a separate short sentence for each distinct fact or
  number.
- Never combine labels inside one bracket. Write [S1] [S2], not [S1, S2].
- A citation may only support a claim explicitly present in that excerpt.
- If the excerpts do not contain enough evidence, clearly say that the provided
  papers do not contain enough information. Do not guess.
- Keep terminology, numbers, dataset names, and limitations faithful to the text.
- Answer in the same language as the user's question.
- Synthesize across excerpts instead of dumping them verbatim.
"""


def _openai_client():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is missing. Export it in the current terminal; "
            "never put a real key in source control."
        )
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "openai is required. Install the project with: "
            'python -m pip install -e ".[dev]"'
        ) from exc
    return OpenAI()


class OpenAIEmbeddingProvider:
    def __init__(self, model: str, batch_size: int = 64) -> None:
        self.model = model
        self.batch_size = batch_size
        self.client = _openai_client()

    def _embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        all_vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = list(texts[start : start + self.batch_size])
            response = self.client.embeddings.create(
                model=self.model,
                input=batch,
                encoding_format="float",
            )
            ordered = sorted(response.data, key=lambda item: item.index)
            all_vectors.extend([list(item.embedding) for item in ordered])
        if len(all_vectors) != len(texts):
            raise RuntimeError("Embedding API returned an unexpected item count")
        return all_vectors

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return self._embed(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text])[0]


_SOURCE_PATTERN = re.compile(r"\[S(\d+)\]")


def citations_from_answer(
    answer: str, sources: Sequence[SearchResult]
) -> tuple[Citation, ...]:
    cited_indices: list[int] = []
    for raw_index in _SOURCE_PATTERN.findall(answer):
        index = int(raw_index)
        if 1 <= index <= len(sources) and index not in cited_indices:
            cited_indices.append(index)
    return tuple(
        Citation(
            label=f"S{index}",
            title=sources[index - 1].title,
            source=sources[index - 1].source,
            page=sources[index - 1].page,
            quote=sources[index - 1].content[:500],
            line_start=sources[index - 1].line_start,
            line_end=sources[index - 1].line_end,
        )
        for index in cited_indices
    )


def build_grounded_prompt(
    question: str, sources: Sequence[SearchResult]
) -> str:
    context_blocks = []
    for index, source in enumerate(sources, start=1):
        context_blocks.append(
            "\n".join(
                [
                    f"[S{index}]",
                    f"Title: {source.title}",
                        f"Source: {source.source}",
                        f"Page: {source.page}",
                        f"Lines: {source.line_start}-{source.line_end}",
                        f"Section: {source.section}",
                        f"Excerpt: {source.content}",
                ]
            )
        )
    return (
        f"Question:\n{question}\n\n"
        "Paper excerpts:\n\n" + "\n\n".join(context_blocks)
    )


class OpenAIAnswerProvider:
    SYSTEM_PROMPT = GROUNDING_SYSTEM_PROMPT

    def __init__(self, model: str, reasoning_effort: str = "low") -> None:
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.client = _openai_client()

    def answer(
        self, question: str, sources: Sequence[SearchResult]
    ) -> tuple[str, tuple[Citation, ...], bool]:
        if not sources:
            text = (
                "Không tìm thấy bằng chứng phù hợp trong các tài liệu đã nạp."
            )
            return text, (), False

        prompt = build_grounded_prompt(question, sources)
        response = self.client.responses.create(
            model=self.model,
            instructions=self.SYSTEM_PROMPT,
            input=prompt,
            reasoning={"effort": self.reasoning_effort},
        )
        text = response.output_text.strip()
        references = claim_references(text, sources)
        if not references:
            return text, (), False
        audit = self.client.responses.create(
            model=self.model,
            instructions=(
                "You are a strict factual-grounding auditor. "
                "Return valid JSON only."
            ),
            input=build_verification_prompt(text, references, sources),
            reasoning={"effort": self.reasoning_effort},
        )
        return apply_verification(
            text,
            sources,
            parse_json_object(audit.output_text),
        )
