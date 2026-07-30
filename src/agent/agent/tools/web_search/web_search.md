---
name: search_web
description: Search the web for information using Tavily API or DuckDuckGo.
arguments:
  query: str
  max_results: int (optional, default 5)
returns:
  title: str
  url: str
  snippet: str
---

Search up to 5 results from the web. Returns list of {title, url, snippet}.

Use this tool when:
- User asks a question not covered in the slide
- Slide content is insufficient
- User needs current/recent information
- User asks "what is", "how does", "explain" for concepts

Priority: Tavily API (AI-optimized) → DuckDuckGo (free fallback)

Format results with `format_results()` for display.
