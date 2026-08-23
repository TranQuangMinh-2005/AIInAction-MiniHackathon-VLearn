"""
A-01 — Orchestrator Router (AGENT-UPGRADE-PLAN.md).

Node đầu luồng LangGraph:
1. Chuẩn hoá input — teencode/chính tả ("sờ lai"→slide, "promt"→prompt,
   "React"→"ReAct" khi không thuộc ngữ cảnh JavaScript).
2. Phân loại ý định — slide / deep / summary / logistics / off_topic / unclear
   (deterministic keyword trước, LLM flash-lite cho phần còn lại, fallback "slide").
3. Graph định tuyến theo intent (xem graph.py).

Giữ `validate_input` (security.py) làm cổng an toàn TRƯỚC node này.
"""

import json
import re

from agent.state import AgentState
from agent.llm import llm
from agent.nodes.slide_search import IRRELEVANT_KEYWORDS

# ── Chuẩn hoá input — deterministic, không cần LLM ────────────────────────────

# (pattern, thay thế) — áp theo thứ tự, regex ignore-case.
SPELL_FIXES: list[tuple[str, str]] = [
    (r"\bsờ\s*lai\b", "slide"),
    (r"\bsơ\s*lai\b", "slide"),
    (r"\bslai\b", "slide"),
    (r"\bpromt\b", "prompt"),
    (r"\bchabot\b", "chatbot"),
    (r"\btokenn?\b", "token"),
    (r"\bembeddingg?\b", "embedding"),
    (r"\bretrivel\b", "retrieval"),
    (r"\btóm\s*tắt\s*sờ\s*lai\b", "tóm tắt slide"),
    (r"\bai\s+thục\s+chiến\b", "ai thực chiến"),
    # VX11 — "điêu toa"/"dieu toa" = teencode của "deploy" (Day 15 triển khai thực tế)
    (r"\bđiêu\s*toa\b", "deploy"),
    (r"\bdieu\s*toa\b", "deploy"),
]

# "React" là framework JS; "ReAct" là pattern agent (Day 3). Chỉ ánh xạ khi
# không có dấu hiệu ngữ cảnh JavaScript/frontend.
REACT_JS_CONTEXT = re.compile(
    r"react\s*(js|native|hook|component|app)|javascript|frontend|"
    r"giao\s*diện|web\s*app|webpage|nút\s*bấm",
    re.IGNORECASE,
)
REACT_WORD = re.compile(r"\breact\b", re.IGNORECASE)


def normalize_question(question: str) -> str:
    """Chuẩn hoá teencode/chính tả + React→ReAct (an toàn, không cần LLM)."""
    text = question.strip()
    for pattern, replacement in SPELL_FIXES:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    if REACT_WORD.search(text) and not REACT_JS_CONTEXT.search(text):
        text = REACT_WORD.sub("ReAct", text)
    return text


# ── Phân loại ý định ─────────────────────────────────────────────────────────

SUMMARY_CUES = [
    "tóm tắt", "tổng hợp", "summary", "summarize", "overview",
    "tóm tắt toàn bộ", "tóm tắt cả buổi", "tóm tắt ngày", "tóm tắt day",
]
LOGISTICS_CUES = [
    "deadline", "bài tập", "bài tập về nhà", "lab", "giảng viên",
    "tải file", "tải tài liệu", "lịch học", "phòng học", "giờ học",
    "nộp bài", "chấm điểm", "điểm danh", "zoom", "meet", "link lớp",
    "khóa học", "lịch thi", "thi cuối",
]
PRIORITY_CUES = [  # đè cả logistics — bảo mật/pháp lý
    "bỏ qua hướng dẫn", "system prompt", "tiết lộ prompt",
]

# VX13/VX14 — câu cá nhân ngắn ("t có đẹp trai không", "bạn là model của hãng
# nào") phải bị từ chối (off_topic), KHÔNG được kéo vào unclear→lookup.
PERSONAL_TOPIC_CUES = [
    "đẹp trai", "xinh gái", "xinh đẹp", "có giàu", "bạn là ai", "bạn là gì",
    "bạn là model", "model của hãng", "hãng nào tạo", "ai tạo ra bạn",
    "ai làm ra bạn", "có yêu", "cưới", "làm bạn gái", "làm bạn trai",
    "có người yêu chưa", "tên gì", "bao nhiêu tuổi",
]

# VX13/VX14 — ngưỡng cho downgrade LLM-off_topic → unclear (VX11):
# chỉ hạ xuống khi có tín hiệu học tập rõ (keyword khóa học) hoặc câu đủ dài
# (câu dài hiếm khi là hỏi cá nhân). Ngắn + không keyword → GIỮ off_topic.
COURSE_SIGNAL_KEYWORDS = [
    "slide", "bài giảng", "day 1", "day 2", "day 3", "day 4", "day 5", "day 6",
    "day 7", "day 8", "day 9", "day 10", "day 11", "day 13", "day 14", "day 15",
    "ai", "model", "llm", "rag", "prompt", "token", "embedding", "agent",
    "thuật toán", "giải thích", "khái niệm", "học", "hỏi", "python", "code",
    "deploy", "triển khai", "paper", "research", "network", "attention",
    "vector", "hackathon", "bài tập", "khóa học", "ai thực chiến", "ví dụ",
]
_MIN_DOWNGRADE_LENGTH = 20

OFF_TOPIC_FALLBACK = "off_topic"

INTENTS = {"slide", "deep", "summary", "logistics", "off_topic", "unclear", "example"}

# t41 — yêu cầu SINH NỘI DUNG SƯ PHẠM (ví dụ thực tế / câu hỏi ôn tập)
EXAMPLES_CUES = [
    "ví dụ thực tế", "ví dụ về", "cho mình ví dụ", "cho ví dụ", "example",
    "câu hỏi ôn tập", "câu hỏi ôn", "ôn tập phần này", "ôn tập về", "quiz",
    "hỏi ôn tập", "câu hỏi kiểm tra", "đưa ra ví dụ",
]

INTENT_PROMPT = """Bạn là bộ định tuyến (router) cho trợ lý học tập của khóa học "AI Thực Chiến" (AI, LLM, ML, RAG, agent...).

Phân loại câu hỏi của học viên thành DUY NHẤT MỘT intent:
- slide: hỏi nội dung có trong bài giảng/slide (định nghĩa, khái niệm, giải thích)
- example: xin VÍ DỤ THỰC TẾ hoặc CÂU HỎI ÔN TẬP dựa trên phần đang học (ví dụ, quiz, ôn tập)
- deep: muốn đào sâu/kiến thức ngoài slide (paper khoa học, so sánh nâng cao, nghiên cứu)
- summary: yêu cầu tóm tắt/tổng hợp toàn bộ hoặc một phần tài liệu
- logistics: deadline, bài tập, giảng viên, lịch học, tải file, điểm, phòng học...
- off_topic: hoàn toàn không liên quan khóa học (thời tiết, ẩm thực, thể thao, giải trí...)
- unclear: không đủ rõ để xác định

Chú ý: "React" trong khóa học này thường là "ReAct" (pattern agent) nếu không nói về JavaScript.
Chú ý teencode/sai chính tả (vd "điêu toa", "sờ lai"): nếu có thể đoán chủ đề học tập thì vẫn là
câu học tập; KHÔNG đánh off_topic chỉ vì chữ khó đọc — đánh unclear khi không chắc chắn.

Trả về DUY NHẤT một JSON object:
{{"intent": "<một trong các intent trên>", "reason": "<lý do ngắn gọn tiếng Việt>"}}

Câu hỏi: {question}"""


def classify_deterministic(question: str) -> tuple[str, str] | None:
    """Phân loại nhanh bằng keyword cho các trường hợp rõ ràng. None = cần LLM."""
    lowered = question.casefold()
    for cue in PRIORITY_CUES:
        if cue in lowered:
            return "off_topic", f"cue an toàn: '{cue}'"
    for cue in PERSONAL_TOPIC_CUES:
        if cue in lowered:
            return "off_topic", f"cue cá nhân: '{cue}'"
    for cue in OFF_TOPIC_KEYWORDS_EXPANDED():
        if cue in lowered:
            return "off_topic", f"keyword: '{cue}'"
    for cue in EXAMPLES_CUES:
        if cue in lowered:
            return "example", f"keyword sư phạm: '{cue}'"
    for cue in LOGISTICS_CUES:
        if cue in lowered:
            return "logistics", f"keyword: '{cue}'"
    for cue in SUMMARY_CUES:
        if cue in lowered:
            return "summary", f"keyword: '{cue}'"
    return None


def OFF_TOPIC_KEYWORDS_EXPANDED() -> list[str]:
    """Danh sách chủ đề ngoài khóa học (gồm IRRELEVANT_KEYWORDS của slide_search)."""
    return [
        *IRRELEVANT_KEYWORDS,
        "thời tiết", "giá vàng", "chứng khoán", "bóng đá", "nấu ăn",
        "phim", "ca nhạc", "game", "tình yêu", "du lịch", "mua sắm",
    ]


def _parse_intent_json(text: str) -> dict | None:
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def classify_intent(
    question: str,
    state: AgentState | None = None,
) -> tuple[str, str]:
    """Trả về (intent, reason). Deterministic trước, LLM sau, fallback 'slide'."""
    deterministic = classify_deterministic(question)
    if deterministic:
        return deterministic

    try:
        response = llm.invoke(INTENT_PROMPT.format(question=question[:800]))
        data = _parse_intent_json(response.content) or {}
        intent = str(data.get("intent", "")).strip().lower()
        reason = str(data.get("reason", ""))[:200]
        if intent in INTENTS:
            # VX11+VX13/VX14: LLM dễ đánh off_topic cho câu teencode/gibberish,
            # nhưng câu cá nhân ngắn phải giữ off_topic. Chỉ hạ xuống unclear khi
            # có tín hiệu học tập (course keyword) HOẶC câu đủ dài (≥20 ký tự).
            if intent == "off_topic" and _should_downgrade_to_unclear(question):
                return (
                    "unclear",
                    f"LLM nói off_topic nhưng có tín hiệu học tập — hạ xuống unclear: {reason}",
                )
            return intent, reason
    except Exception:
        pass
    return "unclear", "fallback: không phân loại được — xử lý như slide"


def _should_downgrade_to_unclear(question: str) -> bool:
    """Ngưỡng VX13/VX14: downgrade off_topic→unclear chỉ khi câu có vẻ học tập.
    Có keyword off-topic/cá nhân rõ → GIỮ off_topic (từ chối)."""
    lowered = question.casefold()
    if any(cue in lowered for cue in OFF_TOPIC_KEYWORDS_EXPANDED()):
        return False
    if any(cue in lowered for cue in PERSONAL_TOPIC_CUES):
        return False
    if any(keyword in lowered for keyword in COURSE_SIGNAL_KEYWORDS):
        return True
    return len(question.strip()) >= _MIN_DOWNGRADE_LENGTH


# ── Node chính ────────────────────────────────────────────────────────────────

def orchestrate(state: AgentState) -> AgentState:
    """Node Orchestrator: chuẩn hoá + phân loại → ghi vào state chung."""
    raw = state.get("user_question", "")
    normalized = normalize_question(raw)
    intent, reason = classify_intent(normalized, state)

    updated: AgentState = {
        **state,
        "original_question": raw,
        "normalized_question": normalized,
        "user_question": normalized,           # downstream dùng câu đã chuẩn hoá
        "intent": intent,
        "orchestrator_note": reason,
    }

    # Research mode: off-topic chặn luôn (không tốn LLM research); còn lại đi web.
    if state.get("mode") == "research" and intent == "off_topic":
        updated["needs_web_search"] = False
    return updated