from __future__ import annotations

import json
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Sequence

from .models import Citation, SearchResult


_SOURCE_PATTERN = re.compile(
    r"\[(?:S\d+)(?:\s*,\s*S\d+)*\]"
)
_SOURCE_NUMBER_RE = re.compile(r"S(\d+)")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")
_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)


@dataclass(frozen=True)
class ClaimReference:
    id: str
    claim: str
    source_index: int
    start: int
    end: int


def _clean_claim(value: str) -> str:
    value = _SOURCE_PATTERN.sub("", value)
    value = re.sub(r"^[\s#>*\-–•\d.)]+", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip(" ,;:")


def claim_references(
    answer: str, sources: Sequence[SearchResult]
) -> list[ClaimReference]:
    references: list[ClaimReference] = []
    for match in _SOURCE_PATTERN.finditer(answer):
        line_start = answer.rfind("\n", 0, match.start()) + 1
        sentence_start = answer.rfind(". ", line_start, match.start())
        if sentence_start != -1:
            line_start = sentence_start + 2
        line_end = answer.find("\n", match.end())
        if line_end == -1:
            line_end = len(answer)
        claim = _clean_claim(answer[line_start:line_end])
        if not claim:
            continue
        for raw_index in _SOURCE_NUMBER_RE.findall(match.group(0)):
            source_index = int(raw_index)
            if not 1 <= source_index <= len(sources):
                continue
            references.append(
                ClaimReference(
                    id=f"C{len(references) + 1}",
                    claim=claim,
                    source_index=source_index,
                    start=match.start(),
                    end=match.end(),
                )
            )
    return references


def build_verification_prompt(
    answer: str,
    references: Sequence[ClaimReference],
    sources: Sequence[SearchResult],
) -> str:
    payload = {
        "answer": answer,
        "sources": [
            {
                "id": f"R{index}",
                "title": source.title,
                "page": source.page,
                "excerpt": source.content,
            }
            for index, source in enumerate(sources, start=1)
        ],
        "claim_references": [
            {
                "id": reference.id,
                "claim": reference.claim,
                "source_id": f"R{reference.source_index}",
            }
            for reference in references
        ],
    }
    return """Audit the answer against the supplied paper excerpts.

Return JSON only with this shape:
{
  "all_claims_supported": true,
  "items": [
    {
      "id": "C1",
      "entailed": true,
      "quote": "an exact verbatim span copied from the cited excerpt",
      "reason": "short explanation"
    }
  ]
}

Rules:
- Evaluate every claim_reference independently against only its source_id.
- A quote must be the smallest contiguous exact substring that supports the
  whole claim. Copy it verbatim; never paraphrase and never use ellipses.
- Set entailed=false and quote="" when the excerpt does not support the whole
  claim.
- Set all_claims_supported=false if any factual claim in the answer lacks a
  citation, any citation points to insufficient evidence, or any number,
  comparison, method, dataset, or conclusion is unsupported.

INPUT:
""" + json.dumps(payload, ensure_ascii=False)


def parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end <= start:
            return {}
        try:
            value = json.loads(stripped[start : end + 1])
        except json.JSONDecodeError:
            return {}
    return value if isinstance(value, dict) else {}


def _sentences(content: str) -> list[str]:
    return [
        sentence.strip()
        for sentence in _SENTENCE_SPLIT_RE.split(content)
        if sentence.strip()
    ]


def _normalized(value: str) -> str:
    return " ".join(value.split())


def _exact_quote(raw_quote: str, content: str) -> str:
    quote = raw_quote.strip().strip("\"“”")
    if quote and quote in content:
        return quote
    normalized_quote = _normalized(quote)
    normalized_content = _normalized(content)
    if normalized_quote and normalized_quote in normalized_content:
        start = normalized_content.index(normalized_quote)
        return normalized_content[start : start + len(normalized_quote)]
    if not quote:
        return ""
    candidates = _sentences(content)
    best = max(
        candidates,
        key=lambda sentence: SequenceMatcher(
            None, _normalized(quote), _normalized(sentence)
        ).ratio(),
        default="",
    )
    ratio = SequenceMatcher(
        None, _normalized(quote), _normalized(best)
    ).ratio()
    return best if ratio >= 0.82 else ""


def _fallback_span(claim: str, content: str) -> str:
    claim_terms = {
        token.casefold() for token in _TOKEN_RE.findall(claim)
        if len(token) > 2 or token.isdigit()
    }
    sentences = _sentences(content)
    windows = sentences + [
        f"{left} {right}"
        for left, right in zip(sentences, sentences[1:])
    ]
    if not windows:
        return content[:500]

    def score(window: str) -> tuple[float, int]:
        terms = {
            token.casefold() for token in _TOKEN_RE.findall(window)
        }
        overlap = len(claim_terms & terms) / max(len(claim_terms), 1)
        return overlap, -len(window)

    return max(windows, key=score)


def apply_verification(
    answer: str,
    sources: Sequence[SearchResult],
    verification: dict[str, Any],
) -> tuple[str, tuple[Citation, ...], bool]:
    references = claim_references(answer, sources)
    raw_items = verification.get("items", [])
    items = {
        str(item.get("id")): item
        for item in raw_items
        if isinstance(item, dict)
    }
    citations: list[Citation] = []
    replacement_labels: dict[tuple[int, int], list[str]] = {}

    for index, reference in enumerate(references, start=1):
        source = sources[reference.source_index - 1]
        item = items.get(reference.id, {})
        quote = _exact_quote(str(item.get("quote", "")), source.content)
        verifier_entails = item.get("entailed") is True
        entailed = verifier_entails and bool(quote)
        if not quote:
            quote = _fallback_span(reference.claim, source.content)
        label = f"S{index}"
        citations.append(
            Citation(
                label=label,
                title=source.title,
                source=source.source,
                page=source.page,
                quote=quote,
                claim=reference.claim,
                entailed=entailed,
                entailment_reason=str(item.get("reason", "")),
                line_start=source.line_start,
                line_end=source.line_end,
            )
        )
        replacement_labels.setdefault(
            (reference.start, reference.end), []
        ).append(label)

    relabeled_answer = answer
    replacements = [
        (
            start,
            end,
            " ".join(f"[{label}]" for label in labels),
        )
        for (start, end), labels in replacement_labels.items()
    ]
    for start, end, replacement in reversed(replacements):
        relabeled_answer = (
            relabeled_answer[:start]
            + replacement
            + relabeled_answer[end:]
        )

    all_supported = verification.get("all_claims_supported") is True
    grounded = bool(citations) and all_supported and all(
        citation.entailed for citation in citations
    )
    return relabeled_answer, tuple(citations), grounded
