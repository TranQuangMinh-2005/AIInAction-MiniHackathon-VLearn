"""
State schema for VLearn Tutor Agent.

Dùng TypedDict để định nghĩa shape của state truyền qua các node trong graph.
"""

from typing import TypedDict, List, Dict, Annotated, Optional
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    # ── Input từ user ──
    user_question: str                    # Câu hỏi của học viên
    slide_context: str                    # Nội dung slide hiện tại (trang đang xem)
    current_page: int                     # Số trang hiện tại
    slide_title: str                      # Tiêu đề slide
    paper_source: Optional[str]            # PDF focus tùy chọn trong Research

    # ── Messages (hội thoại) ──
    messages: Annotated[List[Dict], add_messages]

    # ── Kết quả tìm kiếm ──
    slide_search_result: Optional[str]    # Kết quả tìm trong slide
    web_search_result: Optional[str]      # Kết quả research bên ngoài

    # ── Final answer ──
    final_answer: Optional[str]           # Câu trả lời cuối cùng
    citations: Optional[List[str]]        # Danh sách nguồn tham khảo
    citation_details: Optional[List[Dict]] # Trang, dòng, quote kiểm chứng

    # ── Flow control ──
    mode: str                             # "normal" | "research"
    needs_web_search: bool                # Có cần search web không?
    error: Optional[str]                  # Lỗi nếu có

    # ── A-01 Orchestrator Router ──
    original_question: Optional[str]      # Câu hỏi gốc (trước chuẩn hoá)
    normalized_question: Optional[str]    # Câu hỏi sau chuẩn hoá (teencode/spell-fix)
    intent: Optional[str]                 # "slide" | "deep" | "summary" | "logistics" | "off_topic" | "unclear"
    orchestrator_note: Optional[str]      # Lý do phân loại (debug/log)

    # ── A-02 Slide retrieval ──
    retrieval_scope: str                  # "doc" | "corpus" | "auto" (doc-first, corpus fallback)

    # ── A-03 Summary Agent ──
    active_doc_id: Optional[str]          # Doc đang học (frontend) — để summary chọn doc
    summary_doc_id: Optional[str]         # Doc đã được tóm tắt
    summary_cache_hit: Optional[bool]     # Kết quả từ cache hay tính mới

    # ── A-05 Tutor Coach (envelope) ──
    move: Optional[str]                   # review_concept | give_example | give_hint | validate
    misconceptions: Optional[List[str]]   # Nhầm lẫn phát hiện được
    follow_ups: Optional[List[str]]       # 2-3 câu gợi ý follow-up (click được trên UI)
    asked_check_question: Optional[bool]  # check hiểu CHỈ khi có dấu hiệu khó

    # ── A-06 Memory (anonymous per-browser) ──
    learner_id: Optional[str]             # Token ẩn danh do client sinh (localStorage)
    memory_context: Optional[str]         # Context từ memory (khái niệm đã hỏi, lặp...)
