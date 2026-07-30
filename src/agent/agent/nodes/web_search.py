"""Node: research outside slides using web, arXiv, and local-paper RAG."""

from agent.state import AgentState
from agent.tools import (
    format_results,
    query_arxiv,
    query_local_papers,
    search_web,
)


def search_online(state: AgentState) -> AgentState:
    question = state["user_question"]
    slide_title = state.get("slide_title", "")
    query = f"{slide_title} {question}" if slide_title else question
    contexts: list[str] = []
    citations = list(state.get("citations", []))

    # Each tool is isolated so one unavailable public API does not take down
    # the complete research flow.
    try:
        local_context, local_citations = query_local_papers(question)
        if local_context:
            contexts.append(local_context)
            citations.extend(local_citations)
    except Exception as exc:
        contexts.append(f"Local paper RAG tạm thời không khả dụng: {exc}")

    try:
        arxiv_context, arxiv_citations = query_arxiv(question)
        if arxiv_context:
            contexts.append(arxiv_context)
            citations.extend(arxiv_citations)
    except Exception as exc:
        contexts.append(f"arXiv tạm thời không khả dụng: {exc}")

    try:
        web_results = search_web(query, max_results=3)
        if web_results:
            contexts.append(
                "KẾT QUẢ TÌM KIẾM WEB:\n" + format_results(web_results)
            )
    except Exception as exc:
        contexts.append(f"Web search tạm thời không khả dụng: {exc}")

    return {
        **state,
        "web_search_result": "\n\n".join(contexts),
        "citations": citations,
    }
