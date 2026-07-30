"""Node: Web search — research kiến thức ngoài slide."""

from agent.state import AgentState
from agent.tools import search_web, format_results


def search_online(state: AgentState) -> AgentState:
    question = state["user_question"]
    slide_title = state.get("slide_title", "")
    query = f"{slide_title} {question}" if slide_title else question
    results = search_web(query, max_results=3)
    formatted = format_results(results)
    return {**state, "web_search_result": formatted}
