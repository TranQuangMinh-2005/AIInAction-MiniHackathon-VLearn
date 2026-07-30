from .paper.tool import arxiv_search, arxiv_download_pdf, arxiv_extract_metadata_and_text, arxiv_extract_text

TOOL_FUNCTION = {
    "search_paper": arxiv_search,
    "arxiv_extract_text": arxiv_extract_text,
}
