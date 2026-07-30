"""Research node locked to the PDF explicitly selected by the user."""

from agent.state import AgentState
from agent.tools import query_local_papers


def search_online(state: AgentState) -> AgentState:
    question = state["user_question"]
    paper_source = state.get("paper_source")
    citations = list(state.get("citations", []))
    citation_details = list(state.get("citation_details", []))

    if not paper_source:
        return {
            **state,
            "web_search_result": (
                "Hãy chọn một paper trước khi đặt câu hỏi Research."
            ),
            "citations": [],
            "citation_details": [],
        }

    try:
        context, local_citations, local_details = query_local_papers(
            question,
            paper_source,
        )
        citations.extend(local_citations)
        citation_details.extend(local_details)
        return {
            **state,
            "web_search_result": context,
            "citations": citations,
            "citation_details": citation_details,
        }
    except Exception as exc:
        return {
            **state,
            "web_search_result": (
                f"Không thể truy vấn paper {paper_source}: {exc}"
            ),
            "citations": [],
            "citation_details": [],
        }
