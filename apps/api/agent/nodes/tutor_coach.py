"""
A-05 — Tutor Coach Agent (AGENT-UPGRADE-PLAN.md + P2-ACCEPTANCE.md).

Soạn câu trả lời cuối theo ENVELOPE 5 trường:
  answer · move (review_concept/give_example/give_hint/validate) ·
  misconceptions[] · follow_ups[] (2-3) · asked_check_question (bool).

Quyết định user: check hiểu CHỈ KHI learner có dấu hiệu khó (không gắn mỗi turn).
Dấu hiệu khó (deterministic): câu hỏi mơ hồ ("không hiểu", "rõ hơn"...), hỏi LẶP
cùng câu/khái niệm (từ Memory A-06), nhầm lẫn React/ReAct (mục tiêu Conv C0128).

Node chạy: (1) generate_answer nếu chưa có final_answer (giữ nguyên hành vi cũ),
(2) build_envelope — shared với server.py (stream path) để SSE done mang envelope.
"""

import re

from agent.state import AgentState
from agent.llm import llm
from agent.nodes.answer import generate_answer
from agent.memory import build_context, get_state, record_turn

MOVES = {"review_concept", "give_example", "give_hint", "validate", "explain"}

# ── Dấu hiệu khó (deterministic) ─────────────────────────────────────────────

_VAGUE_PATTERNS = [
    r"không\s+hiểu", r"chưa\s+hiểu", r"chả\s+hiểu", r"mơ\s+hồ",
    r"rõ\s+hơn", r"dễ\s+hiểu\s+hơn", r"giải\s+thích\s+lại", r"nói\s+lại",
    r"lại\s+lần\s+nữa", r"sờ\s+lai", r"hiểu\s+sai", r"nhầm",
    r"bối\s+rối", r"lạc\s+lối", r"không\s+biết\s+bắt\s+đầu",
]
_REACT_JS_CONTEXT = re.compile(
    r"react\s*(js|native|hook|component|app)|javascript|frontend|web\s*app",
    re.IGNORECASE,
)

_CHECK_QUESTION_PROMPT = """Bạn là VLearn Tutor. Học viên đang gặp khó (dấu hiệu: {signals}).
Viết DUY NHẤT MỘT câu hỏi kiểm tra hiểu NGẮN tiếng Việt (≤25 từ) về đúng khái niệm
đang học trong câu hỏi — để xác nhận học viên đã nắm ý chính chưa.
KHÔNG giải thích, KHÔNG trả lời thay học viên. Chỉ trả về câu hỏi, không kèm gì khác.

Câu hỏi của học viên: {question}"""


def _has_vague_markers(question: str) -> bool:
    lowered = question.casefold()
    return any(re.search(pattern, lowered) for pattern in _VAGUE_PATTERNS)


def _react_react_misconception(original: str, normalized: str) -> str | None:
    """Conv C0128: "React là gì" trong khóa AI → nhầm React (JS) với ReAct (agent)."""
    if (
        re.search(r"\breact\b", original, re.IGNORECASE)
        and not _REACT_JS_CONTEXT.search(original)
    ):
        return "Nhầm React (framework JS) với ReAct (pattern agent trong slide Day 3)"
    return None


def _concepts_from_question(question: str, state: AgentState) -> list[str]:
    """Trích khái niệm chính theo heuristic: bỏ từ hỏi, giữ thuật ngữ (giữ nguyên case)."""
    text = re.sub(
        r"(?i)\b(là gì|thế nào|như thế nào|giải thích|tóm tắt|cho mình biết|"
        r"về|bằng|của|trong|với|và|hay|có|không|bạn|mình)\b",
        " ",
        question,
    )
    text = re.sub(r"[^\w\s-]", " ", text)
    terms = [term.strip() for term in text.split() if len(term.strip()) >= 3]
    technical = [
        term for term in terms
        if term.isupper() or re.search(
            r"rag|llm|token|embed|retriev|agent|react|prompt|vector", term, re.I
        )
    ]
    return (technical or terms)[:3]


# ── Envelope (shared: graph node + server stream) ────────────────────────────

def build_envelope(state: AgentState) -> dict:
    """Tính envelope từ state (không LLM nếu không có dấu hiệu khó)."""
    original = state.get("original_question") or state.get("user_question", "")
    normalized = state.get("user_question", "")
    learner_id = state.get("learner_id")
    memory = get_state(learner_id) if learner_id else {}

    misconceptions: list[str] = []
    misconception = _react_react_misconception(original, normalized)
    if misconception:
        misconceptions.append(misconception)
    misconceptions.extend(memory.get("misconceptions", [])[:1])

    # Dấu hiệu khó
    repeat_signals = []
    if learner_id:
        repeated = [
            item for item in memory.get("questions", [])
            if item.get("count", 0) >= 2
        ]
        repeat_signals = [item["name"] for item in repeated[:2]]
    signals: list[str] = []
    if _has_vague_markers(original):
        signals.append("câu hỏi mơ hồ/dấu hiệu khó hiểu")
    if repeat_signals:
        signals.append("hỏi lặp: " + ", ".join(repeat_signals))
    if misconception:
        signals.append("dấu hiệu nhầm lẫn khái niệm")
    has_difficulty = bool(signals)

    # Check hiểu: CHỈ khi có dấu hiệu khó (quyết định user).
    asked_check = has_difficulty
    check_question = ""
    if has_difficulty:
        try:
            response = llm.invoke(
                _CHECK_QUESTION_PROMPT.format(
                    signals="; ".join(signals),
                    question=normalized[:300],
                )
            )
            check_question = (response.content or "").strip().strip('"')
        except Exception:
            check_question = ""

    # Follow-ups: 2-3 câu (1 check-question nếu có; 1 recap khi lặp; 1 chung).
    follow_ups: list[str] = []
    if check_question:
        follow_ups.append(check_question)
    if repeat_signals:
        follow_ups.append(
            "Mình đã giải thích về chủ đề này trước đó — bạn muốn mình đi sâu "
            "hơn vào phần nào, hay nhắc lại ngắn gọn?"
        )
    concepts = _concepts_from_question(normalized, state)
    if concepts:
        follow_ups.append(
            f"Bạn muốn mình đào sâu hơn về {concepts[0]} không?"
        )
    if misconception:
        follow_ups.append(
            "Bạn có định hỏi **ReAct pattern** trong slide Day 3 (Design Pattern "
            "& ReAct cho Agent) — khác với React framework JavaScript nhé?"
        )
    if len(follow_ups) < 2:
        follow_ups.append(
            "Bạn có muốn mình cho ví dụ thực tế hoặc câu hỏi ôn tập về phần này không?"
        )
    follow_ups = follow_ups[:4]

    # Move
    if has_difficulty:
        move = "give_hint"
    elif state.get("intent") == "summary":
        move = "validate"
    elif state.get("web_search_result"):
        move = "give_example"
    else:
        move = "review_concept"

    return {
        "move": move,
        "misconceptions": misconceptions[:3],
        "follow_ups": follow_ups,
        "asked_check_question": asked_check,
    }


def remember_turn(state: AgentState, envelope: dict) -> None:
    """A-06 — ghi memory cuối turn (không ném lỗi)."""
    learner_id = state.get("learner_id")
    if not learner_id:
        return
    try:
        record_turn(
            learner_id,
            question=state.get("original_question") or state.get("user_question", ""),
            doc_id=state.get("active_doc_id") or state.get("summary_doc_id"),
            page=state.get("current_page"),
            concepts=_concepts_from_question(
                state.get("user_question", ""), state
            ),
            misconceptions=envelope.get("misconceptions", []),
        )
    except Exception:
        pass


def tutor_coach(state: AgentState) -> AgentState:
    """Node cuối: bảo đảm final_answer + envelope 5 trường + ghi memory."""
    if not (state.get("final_answer") or "").strip():
        state = generate_answer(state)

    envelope = build_envelope(state)
    remember_turn(state, envelope)
    memory_context = build_context(state.get("learner_id"))
    return {
        **state,
        **envelope,
        "memory_context": memory_context,
    }