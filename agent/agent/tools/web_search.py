"""
Tool: Web search via Tavily API (chuyên cho AI agent).
Fallback: DuckDuckGo nếu không có key.
"""

import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))


def search_web(query: str, max_results: int = 5) -> list[dict]:
    """
    Tìm kiếm web. Ưu tiên Tavily, fallback DuckDuckGo.

    Returns:
        List[dict]: [{"title": ..., "url": ..., "snippet": ...}]
    """
    tavily_key = os.getenv("TAVILY_API_KEY")

    if tavily_key:
        return _search_tavily(query, max_results, tavily_key)

    return _search_duckduckgo(query, max_results)


def _search_tavily(query: str, max_results: int, api_key: str) -> list[dict]:
    try:
        import requests
        resp = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": query,
                "max_results": max_results,
                "search_depth": "basic",
            },
            timeout=10,
        )
        data = resp.json()
        results = data.get("results", [])
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("content", ""),
            }
            for r in results
        ]
    except Exception:
        return _search_duckduckgo(query, max_results)


def _search_duckduckgo(query: str, max_results: int) -> list[dict]:
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = []
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                })
            return results
    except Exception:
        return [{"title": "Search failed", "url": "", "snippet": "Không thể tìm kiếm web."}]


def format_results(results: list[dict]) -> str:
    if not results:
        return "Không tìm thấy kết quả nào."

    lines = []
    for i, r in enumerate(results, 1):
        url = r.get("url", "")
        lines.append(
            f"{i}. **{r['title']}**\n"
            f"   {r['snippet']}\n"
            f"   🔗 [{url}]({url})"
        )
    return "\n\n".join(lines)
