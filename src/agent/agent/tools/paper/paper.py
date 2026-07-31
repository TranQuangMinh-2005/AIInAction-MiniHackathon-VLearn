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




def arxiv_search(
    query: str,
    max_results: int = 3,
    sort_by: str = "relevance",
):
    max_results = min(max_results, 10)

    params = {
        "search_query": _normalize_query(query),
        "start": 0,
        "max_results": max_results,
        "sortBy": sort_by,
        "sortOrder": "descending",
    }

    try:
        response = _request(
            ARXIV_API_URL,
            params=params,
            max_attempts=1,
        )
    except requests.RequestException:
        fallback = _search_duckduckgo_arxiv(query, max_results)
        if fallback:
            return fallback
        raise
    if response.status_code == 429:
        fallback = _search_duckduckgo_arxiv(query, max_results)
        if fallback:
            return fallback
    response.raise_for_status()

    try:
        root = ET.fromstring(response.text)
    except ET.ParseError:
        fallback = _search_duckduckgo_arxiv(query, max_results)
        if fallback:
            return fallback
        raise

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

    if not papers:
        fallback = _search_duckduckgo_arxiv(query, max_results)
        if fallback:
            return fallback
    return papers



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
