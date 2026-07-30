"""
VLearn Tutor Agent — Graph definition.

Luồng xử lý:
1. search_slide    → Tìm câu trả lời trong nội dung slide
2. decide_search   → Quyết định có cần research thêm không
3. web_search      → Tìm kiếm bên ngoài (nếu cần)
4. generate_answer → Tổng hợp câu trả lời cuối cùng
"""

from langgraph.graph import StateGraph, END
from agent.state import AgentState
from agent.nodes import slide_search, web_search, answer


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    # ── Nodes ──
    graph.add_node("search_slide", slide_search.search_slide)
    graph.add_node("decide_search", slide_search.decide_search)
    graph.add_node("web_search", web_search.search_online)
    graph.add_node("generate_answer", answer.generate_answer)

    # ── Edges ──
    graph.set_entry_point("search_slide")
    graph.add_edge("search_slide", "decide_search")

    # Conditional: nếu cần research thêm → web_search, không thì → generate_answer
    graph.add_conditional_edges(
        "decide_search",
        lambda state: "web_search" if state.get("needs_web_search") else "generate_answer",
        {
            "web_search": "web_search",
            "generate_answer": "generate_answer",
        },
    )
    graph.add_edge("web_search", "generate_answer")
    graph.add_edge("generate_answer", END)

    return graph.compile()


def run_agent(user_question: str, slide_context: str, current_page: int, slide_title: str) -> dict:
    """Chạy agent với input từ frontend."""
    graph = build_graph()

    initial_state: AgentState = {
        "user_question": user_question,
        "slide_context": slide_context,
        "current_page": current_page,
        "slide_title": slide_title,
        "messages": [],
        "slide_search_result": None,
        "web_search_result": None,
        "final_answer": None,
        "citations": [],
        "needs_web_search": False,
        "error": None,
    }

    result = graph.invoke(initial_state)
    return result
