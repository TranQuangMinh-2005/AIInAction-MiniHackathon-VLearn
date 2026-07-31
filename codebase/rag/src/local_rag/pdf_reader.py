from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from .models import PDFPage


@dataclass(frozen=True)
class ParsedPDF:
    source: str
    title: str
    file_sha256: str
    pages: tuple[PDFPage, ...]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def clean_pdf_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"(?<=\w)-\s*\n\s*(?=\w)", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" *\n *", "\n", text)
    return text.strip()


def parse_pdf(path: Path, source: str | None = None) -> ParsedPDF:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError(
            "pypdf is required. Install the project with: "
            'python -m pip install -e ".[dev]"'
        ) from exc

    reader = PdfReader(str(path))
    raw_title = None
    if reader.metadata:
        raw_title = getattr(reader.metadata, "title", None)
    title = clean_pdf_text(str(raw_title)) if raw_title else path.stem
    pages = []
    for number, page in enumerate(reader.pages, start=1):
        text = clean_pdf_text(page.extract_text() or "")
        if text:
            pages.append(PDFPage(number=number, text=text))
    if not pages:
        raise ValueError(
            f"No selectable text found in {path.name}. "
            "Scanned PDFs need OCR before ingestion."
        )
    return ParsedPDF(
        source=source or path.name,
        title=title,
        file_sha256=sha256_file(path),
        pages=tuple(pages),
    )
