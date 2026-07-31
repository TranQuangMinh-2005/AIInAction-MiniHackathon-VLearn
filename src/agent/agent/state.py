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
