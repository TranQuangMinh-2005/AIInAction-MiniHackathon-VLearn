# from agent.tools.web_search import search_web, format_results


from .paper.tool import arxiv_search, arxiv_extract_text

__all__ = {
    "arxiv_search": arxiv_search,
    "arxiv_extract_text": arxiv_extract_text
    # "search_web" : search_web,
    # "format_results" : format_results,
}
