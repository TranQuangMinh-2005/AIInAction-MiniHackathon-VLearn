"""
VLearn Tutor Agent — Graph definition (A-01 Orchestrator Router).

Luồng xử lý (sau A-01):
1. orchestrator → Chuẩn hoá input + phân loại ý định (intent)
2. off_topic → refuse_off_topic (từ chối lịch sự, deterministic, không tốn LLM)
3. research mode → web_search trực tiếp (giữ nguyên hành vi cũ: luôn tìm paper,
   bỏ nhánh `if is_research` cứng trong server.py — research giờ nằm trong graph)
4. normal → search_slide → decide_search → (web_search?) → generate_answer
"""

from langgraph.graph import StateGraph, END
import re
from agent.state import AgentState
from agent.nodes import (
    orchestrator,
    slide_search,
    web_search,
    answer,
    summary,
    tutor_coach,
    examples,
)


_WANTS_PAPER = re.compile(
    r"\b(paper|papers|bài\s*báo|arxiv|research)\b",
    re.IGNORECASE,
)


def wants_paper_search(question: str) -> bool:
    """Câu hỏi rõ ràng muốn paper/nghiên cứu (A-08) — kể cả ở normal mode."""
    return bool(_WANTS_PAPER.search(question or ""))


def _route_after_orchestrator(state: AgentState) -> str:
    if state.get("intent") == "example":
        return "example_teacher"
    if state.get("intent") == "summary":
        return "summarize_doc"
    if state.get("mode") == "research":
        # Research luôn chạy paper search (giữ nguyên hành vi trước A-01);
        # orchestrator đã chặn off_topic bằng needs_web_search=False.
        if not state.get("needs_web_search", True):
            return "refuse_off_topic"
        return "web_search"
    if state.get("intent") == "off_topic":
        return "refuse_off_topic"
    # A-08 — normal mode nhưng câu hỏi muốn paper ("tìm paper về X") → research path
    if wants_paper_search(
        state.get("normalized_question") or state.get("user_question", "")
    ):
        return "web_search"
    return "search_slide"


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    # ── Nodes ──
    graph.add_node("orchestrator", orchestrator.orchestrate)
    graph.add_node("search_slide", slide_search.search_slide)
    graph.add_node("decide_search", slide_search.decide_search)
    graph.add_node("web_search", web_search.search_online)
    graph.add_node("generate_answer", answer.generate_answer)
    graph.add_node("refuse_off_topic", answer.refuse_off_topic)
    graph.add_node("summarize_doc", summary.summarize_doc)
    graph.add_node("tutor_coach", tutor_coach.tutor_coach)
    graph.add_node("example_teacher", examples.generate_examples)

    # ── Edges ──
    graph.set_entry_point("orchestrator")
    graph.add_conditional_edges(
        "orchestrator",
        _route_after_orchestrator,
        {
            "refuse_off_topic": "refuse_off_topic",
            "search_slide": "search_slide",
            "web_search": "web_search",
            "summarize_doc": "summarize_doc",
            "example_teacher": "example_teacher",
        },
    )
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
    graph.add_edge("generate_answer", "tutor_coach")
    graph.add_edge("summarize_doc", "tutor_coach")
    graph.add_edge("tutor_coach", END)
    graph.add_edge("example_teacher", END)
    graph.add_edge("refuse_off_topic", END)

    return graph.compile()


def run_agent(user_question: str, slide_context: str, current_page: int, slide_title: str) -> dict:
    """Chạy agent với input từ frontend."""
    graph = build_graph()

    initial_state: AgentState = {
        "user_question": user_question,
        "slide_context": slide_context,
        "current_page": current_page,
        "slide_title": slide_title,
        "paper_source": None,
        "messages": [],
        "slide_search_result": None,
        "web_search_result": None,
        "final_answer": None,
        "citations": [],
        "citation_details": [],
        "needs_web_search": False,
        "error": None,
        "original_question": user_question,
        "normalized_question": None,
        "intent": None,
        "orchestrator_note": None,
        "retrieval_scope": "auto",
        "active_doc_id": None,
        "summary_doc_id": None,
        "summary_cache_hit": None,
    }

    result = graph.invoke(initial_state)
    return result