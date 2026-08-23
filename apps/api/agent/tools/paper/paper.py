from __future__ import annotations

import html
import os
import re
import time
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import parse_qs, urlparse

import fitz
import requests

ARXIV_API_URL = "https://export.arxiv.org/api/query"

TIMEOUT = 30

ARXIV_MIN_INTERVAL_SECONDS = 3.0
_last_request_at = 0.0


def _user_agent() -> str:
    return os.getenv(
        "ARXIV_USER_AGENT",
        "Research-Agent/1.0 (Educational Project)"
    )


def _rate_limit():
    global _last_request_at

    elapsed = time.monotonic() - _last_request_at

    if elapsed < ARXIV_MIN_INTERVAL_SECONDS:
        time.sleep(ARXIV_MIN_INTERVAL_SECONDS - elapsed)

    _last_request_at = time.monotonic()


def _request(url: str, params=None, max_attempts: int = 3):

    last_response = None

    for i in range(max_attempts):

        _rate_limit()

        response = requests.get(
            url,
            params=params,
            timeout=TIMEOUT,
            headers={
                "User-Agent": _user_agent()
            }
        )

        last_response = response

        if response.status_code != 429:
            return response

        time.sleep((i + 1) * 3)

    return last_response


def _normalize_query(query: str):

    query = " ".join(query.split())

    if ":" in query:
        return query

    return f'all:"{query}"'


# Stop words bị loại khi tạo biến thể AND (A-08 — note phrase-query dài).
_AND_STOP_WORDS = {
    "the", "a", "an", "of", "for", "and", "with", "on", "in", "to", "from",
    "how", "what", "why", "via", "using", "is", "are", "about", "new", "most",
}


def _query_variants(query: str) -> list[str]:
    """A-08 — arXiv `all:"..."` đòi cụm NGUYÊN VẸN → query dài trả 0 kết quả.
    Fallback cascade: (1) phrase gốc (≤3 từ), (2) AND giữa từ khóa (≤5 từ,
    bỏ stop words), (3) cụm ngắn 3 từ đầu. Tối đa 3 biến thể."""
    variants = [query]
    terms = [t for t in re.findall(r"[A-Za-z0-9][A-Za-z0-9\-\+\.]*", query)]
    if len(terms) <= 3:
        return variants

    keywords = [t for t in terms if t.casefold() not in _AND_STOP_WORDS][:5]
    if len(keywords) >= 2:
        variants.append(" AND ".join(f"all:{keyword}" for keyword in keywords))

    short = " ".join(terms[:3])
    if short != query:
        variants.append(short)
    return variants[:3]


def _plain_text(value: str) -> str:
    return " ".join(
        html.unescape(re.sub(r"<[^>]+>", " ", value)).split()
    )


def _decode_duckduckgo_url(value: str) -> str:
    value = html.unescape(value)
    if value.startswith("//"):
        value = f"https:{value}"
    parsed = urlparse(value)
    redirected = parse_qs(parsed.query).get("uddg", [])
    return redirected[0] if redirected else value


def _search_duckduckgo_arxiv(
    query: str,
    max_results: int,
) -> list[dict[str, Any]]:
    """Discovery fallback when the official arXiv API is rate-limited."""
    response = requests.get(
        "https://html.duckduckgo.com/html/",
        params={"q": f"site:arxiv.org/abs {query}"},
        timeout=TIMEOUT,
        headers={"User-Agent": _user_agent()},
    )
    response.raise_for_status()
    matches = list(
        re.finditer(
            r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>'
            r"(.*?)</a>",
            response.text,
            flags=re.IGNORECASE | re.DOTALL,
        )
    )
    papers: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, match in enumerate(matches):
        url = _decode_duckduckgo_url(match.group(1))
        id_match = re.search(
            r"arxiv\.org/(?:abs|pdf)/([^/?#]+)",
            url,
            flags=re.IGNORECASE,
        )
        if not id_match:
            continue
        arxiv_id = id_match.group(1).removesuffix(".pdf")
        if arxiv_id in seen:
            continue
        seen.add(arxiv_id)
        next_start = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else len(response.text)
        )
        result_block = response.text[match.end():next_start]
        snippet_match = re.search(
            r'class="result__snippet"[^>]*>(.*?)</a>',
            result_block,
            flags=re.IGNORECASE | re.DOTALL,
        )
        papers.append(
            {
                "title": _plain_text(match.group(2)),
                "authors": [],
                "summary": (
                    _plain_text(snippet_match.group(1))
                    if snippet_match
                    else ""
                ),
                "published": "",
                "updated": "",
                "abstract_url": f"https://arxiv.org/abs/{arxiv_id}",
                "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}",
            }
        )
        if len(papers) >= max_results:
            break
    return papers



def _text(node, path, ns):

    x = node.find(path, ns)

    if x is None:
        return ""

    return (x.text or "").strip()




def _arxiv_api_search(query: str, max_results: int, sort_by: str) -> list[dict]:
    """Một lần gọi official arXiv API (không fallback DDG ở đây — cascade caller lo)."""
    params = {
        "search_query": _normalize_query(query),
        "start": 0,
        "max_results": max_results,
        "sortBy": sort_by,
        "sortOrder": "descending",
    }

    response = _request(
        ARXIV_API_URL,
        params=params,
        max_attempts=1,
    )
    if response.status_code == 429:
        return []
    response.raise_for_status()

    try:
        root = ET.fromstring(response.text)
    except ET.ParseError:
        return []

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }

    papers = []

    for entry in root.findall("./atom:entry", ns):

        links = entry.findall("./atom:link", ns)

        pdf_url = ""

        for link in links:

            if link.get("title") == "pdf":
                pdf_url = link.get("href")
                break

        authors = []

        for author in entry.findall("./atom:author", ns):
            authors.append(_text(author, "./atom:name", ns))

        summary = _text(entry, "./atom:summary", ns)

        papers.append(
            {
                "title": _text(entry, "./atom:title", ns),
                "authors": authors,
                "summary": summary,
                "published": _text(entry, "./atom:published", ns),
                "updated": _text(entry, "./atom:updated", ns),
                "abstract_url": _text(entry, "./atom:id", ns),
                "pdf_url": pdf_url,
            }
        )
    return papers


def arxiv_search(
    query: str,
    max_results: int = 3,
    sort_by: str = "relevance",
):
    """A-08 — tìm arXiv với fallback cascade: phrase → AND keywords → cụm ngắn
    → DuckDuckGo discovery. Query dài không còn bị `all:"..."` giết (note A-08)."""
    max_results = min(max_results, 10)

    last_error = None
    for variant in _query_variants(query):
        try:
            papers = _arxiv_api_search(variant, max_results, sort_by)
        except requests.RequestException as exc:
            last_error = exc
            continue
        if papers:
            return papers

    # Mọi biến thể đều rỗng/lỗi → discovery fallback (giữ hành vi cũ)
    fallback = _search_duckduckgo_arxiv(query, max_results)
    if fallback:
        return fallback
    if last_error:
        raise last_error
    return []



def arxiv_download_pdf(pdf_url: str) -> bytes:

    response = _request(pdf_url)


    MAX_PDF_SIZE = 50 * 1024 * 1024

    if len(response.content) > MAX_PDF_SIZE:
        raise ValueError("PDF too large")

    response.raise_for_status()

    return response.content


def arxiv_extract_text(pdf_url: str):

    pdf = arxiv_download_pdf(pdf_url)

    with fitz.open(stream=pdf, filetype="pdf") as doc:

        pages = []
        full_text = []

        for page_number, page in enumerate(doc, start=1):

            blocks = page.get_text("blocks")

            text = "\n".join(
                block[4]
                for block in blocks
                if block[4].strip()
            )

            pages.append(
                {
                    "page": page_number,
                    "text": text,
                    "blocks": blocks,
                }
            )

            full_text.append(text)

    return {
        "num_pages": len(pages),
        "pages": pages,
        "text": "\n".join(full_text),
    }




def arxiv_extract_metadata_and_text(paper: dict):

    pdf = arxiv_extract_text(paper["pdf_url"])

    return {
        **paper,
        **pdf,
    }
