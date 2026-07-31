---
name: search_paper
description: Search papers from arXiv by topic.
arguments:
  query: str
returns:
  title: str
  authors: list[str]
  updated: str
  summary: str
  abstract_url: str
  pdf_url: str
---

Search up to 3 papers from arXiv.

Use this tool when the user asks to:
- search papers
- find papers
- research a topic
- recommend papers



---
name: arxiv_extract_text
description: Download a paper PDF from arXiv and extract its text.
arguments:
  link_pdf: str
returns:
  text: str
  pages: list
  num_pages: int
---

Extract full text from an arXiv PDF.

Use this tool only after obtaining a PDF URL.
