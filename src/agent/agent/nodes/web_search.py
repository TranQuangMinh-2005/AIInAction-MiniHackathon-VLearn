"""Fast research node using one source path: local PDF or arXiv."""

from agent.state import AgentState
from agent.tools import query_arxiv, query_local_papers


def search_online(state: AgentState) -> AgentState:
    question = state["user_question"]
    citations = list(state.get("citations", []))

    # If a filename/title selects an indexed PDF, do not waste time querying
    # arXiv. Otherwise use arXiv only, matching the one-day MVP scope.
    try:
        local_context, local_citations = query_local_papers(question)
        if local_context:
            citations.extend(local_citations)
            return {
                **state,
                "web_search_result": local_context,
                "citations": citations,
            }
    except Exception as exc:
        local_error = f"Local paper RAG tạm thời không khả dụng: {exc}"
    else:
        local_error = ""

    try:
        arxiv_context, arxiv_citations = query_arxiv(question)
        if arxiv_context:
            citations.extend(arxiv_citations)
            return {
                **state,
                "web_search_result": arxiv_context,
                "citations": citations,
            }
    except Exception as exc:
        arxiv_error = f"arXiv tạm thời không khả dụng: {exc}"
    else:
        arxiv_error = "Không tìm thấy paper phù hợp trên arXiv."

    return {
        **state,
        "web_search_result": "\n".join(
            item for item in (local_error, arxiv_error) if item
        ),
        "citations": citations,
    }
