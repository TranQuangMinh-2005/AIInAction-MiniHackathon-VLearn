from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from .models import Chunk, Document, PDFPage


_SPACE_RE = re.compile(r"\s+")
_NUMBERED_HEADING_RE = re.compile(
    r"^(?:(?:\d+(?:\.\d+)*)|(?:[IVXLCDM]+))[.)]?\s+[A-Z][A-Z0-9 &:/,\-]{2,}$"
)
_INLINE_HEADING_RE = re.compile(
    r"^(Abstract|ABSTRACT)\s+(.+)$"
)
_KNOWN_HEADINGS = {
    "abstract",
    "introduction",
    "background",
    "related work",
    "literature review",
    "data",
    "dataset",
    "data and feature engineering",
    "method",
    "methods",
    "methodology",
    "materials and methods",
    "proposed method",
    "model",
    "models",
    "experiments",
    "experimental setup",
    "results",
    "results and discussion",
    "discussion",
    "limitations",
    "conclusion",
    "conclusions",
    "future work",
    "references",
    "bibliography",
    "appendix",
    "acknowledgements",
    "acknowledgments",
    "abbreviations",
    "author contributions",
    "authors' contributions",
    "funding",
    "data availability",
    "availability of data and materials",
    "declarations",
    "ethics approval and consent to participate",
    "consent for publication",
    "competing interests",
    "publisher's note",
}


@dataclass(frozen=True)
class _SectionBlock:
    section: str
    text: str


def _normalise_space(text: str) -> str:
    return _SPACE_RE.sub(" ", text).strip()


def _heading(line: str) -> str | None:
    candidate = _normalise_space(line).strip(" :")
    if not candidate or len(candidate) > 100:
        return None
    lowered = candidate.casefold()
    if (
        "volume " in lowered
        or lowered.startswith("page ")
        or "doi.org" in lowered
    ):
        return None
    if lowered in _KNOWN_HEADINGS:
        return candidate
    if _NUMBERED_HEADING_RE.match(candidate):
        return candidate
    return None


def _section_blocks(
    page: PDFPage, current_section: str
) -> tuple[list[_SectionBlock], str]:
    blocks: list[_SectionBlock] = []
    buffer: list[str] = []
    section = current_section
    for raw_line in page.text.splitlines():
        inline = _INLINE_HEADING_RE.match(_normalise_space(raw_line))
        if inline:
            text = _normalise_space(" ".join(buffer))
            if text:
                blocks.append(_SectionBlock(section=section, text=text))
            section = inline.group(1)
            buffer = [inline.group(2)]
            continue
        detected = _heading(raw_line)
        if detected:
            text = _normalise_space(" ".join(buffer))
            if text:
                blocks.append(_SectionBlock(section=section, text=text))
            section = detected
            buffer = []
        else:
            buffer.append(raw_line)
    text = _normalise_space(" ".join(buffer))
    if text:
        blocks.append(_SectionBlock(section=section, text=text))
    return blocks, section


def chunk_document(
    document: Document,
    pages: tuple[PDFPage, ...],
    chunk_words: int,
    overlap_words: int,
) -> list[Chunk]:
    if chunk_words <= 0:
        raise ValueError("chunk_words must be greater than zero")
    if overlap_words < 0 or overlap_words >= chunk_words:
        raise ValueError("overlap_words must be in [0, chunk_words)")

    chunks: list[Chunk] = []
    step = chunk_words - overlap_words
    current_section = "Front matter"
    for page in pages:
        blocks, current_section = _section_blocks(page, current_section)
        block_offset = 0
        for block in blocks:
            words = block.text.split()
            for start in range(0, len(words), step):
                selected = words[start : start + chunk_words]
                if not selected:
                    continue
                # Avoid a tiny duplicate tail created only by overlap.
                if start > 0 and len(selected) <= overlap_words:
                    break
                content = " ".join(selected)
                stable_key = (
                    f"{document.id}:{page.number}:{block.section}:"
                    f"{block_offset + start}:{content}".encode("utf-8")
                )
                chunks.append(
                    Chunk(
                        id=hashlib.sha256(stable_key).hexdigest()[:24],
                        document_id=document.id,
                        source=document.source,
                        title=document.title,
                        page=page.number,
                        content=content,
                        word_count=len(selected),
                        section=block.section,
                    )
                )
            block_offset += len(words)
    return chunks
