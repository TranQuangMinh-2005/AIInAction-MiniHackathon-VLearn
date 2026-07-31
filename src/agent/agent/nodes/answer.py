"""Node: Tổng hợp câu trả lời cuối cùng."""

import re

from langchain_core.messages import HumanMessage, SystemMessage
from agent.state import AgentState
from agent.llm import llm

SYSTEM_PROMPT = """# Identity
Bạn là **VLearn Tutor**, trợ lý học tập AI. Chuyển kết quả nghiên cứu thành câu trả lời thân thiện.

# Instructions
1. Mở đầu bằng câu chào ngắn.
2. Dùng **in đậm** cho từ khóa, bullet points cho danh sách, `##` cho tiêu đề.
3. Kết thúc: "Bạn có muốn tìm hiểu sâu hơn về phần nào không?"
4. **KHÔNG** thêm kiến thức ngoài kết quả tìm kiếm. Tiếng Việt hoàn toàn.
"""

SYSTEM_PROMPT_WEB = """# Identity
Bạn là **VLearn Research Tutor**. Bạn mở rộng kiến thức trong slide bằng bằng
chứng lấy từ paper khoa học đã được Research tìm hoặc người dùng chọn.

# Instructions
1. Không chào hỏi, không "Bạn có muốn...", không bullet points.
2. Trả lời dạng **đoạn văn tự nhiên**.
3. Câu hỏi định nghĩa → 1-2 đoạn giải thích.
4. Giữ nguyên nhãn nguồn [S1], [S2]... ngay sau từng claim.
5. Cuối cùng ghi nguồn có URL nếu context cung cấp URL.
6. **KHÔNG** thêm kiến thức ngoài kết quả. Tiếng Việt.
"""


def without_slide_citations(citations: list[str]) -> list[str]:
    return [
        citation
        for citation in citations
        if not re.match(r"^D\d+\s*[-–]\s*Trang\s+\d+", citation, re.I)
    ]


def generate_answer(state: AgentState) -> AgentState:
    question = state["user_question"]
    slide_result = state.get("slide_search_result", "")
    web_result = state.get("web_search_result", "")
    current_page = state.get("current_page", 1)
    slide_title = state.get("slide_title", "")
    paper_source = state.get("paper_source")
    citations = state.get("citations", [])
    needs_web = state.get("needs_web_search", False)
    history = state.get("messages", [])

    if not slide_result.strip() or "SLIDE_NOT_ENOUGH_INFO" in slide_result:
        if web_result:
            prompt = SYSTEM_PROMPT_WEB
            context = web_result
            citations = without_slide_citations(citations)
        else:
            return {
                **state,
                "final_answer": f"Rất tiếc, nội dung slide hiện tại không có đủ thông tin để trả lời câu hỏi này. Bạn có thể thử:\n- Chuyển sang trang khác có nội dung liên quan\n- Đặt câu hỏi khác về chủ đề trong slide\n- Bôi đen đoạn văn bản cụ thể trên slide để mình giải thích",
                "citations": [],
            }
    else:
        prompt = SYSTEM_PROMPT
        context = slide_result
        if web_result and needs_web:
            context = f"{slide_result}\n\nKết quả research thêm từ web:\n{web_result}"
            citations = citations + ["Web search"]

    history_text = ""
    if history:
        lines = []
        for m in history[-4:]:
            if hasattr(m, "type"):
                role = "Học viên" if m.type == "human" else "Tutor"
                content = m.content
            else:
                role = "Học viên" if m.get("role") == "user" else "Tutor"
                content = m.get("content", "")
            lines.append(f"{role}: {content[:150]}")
        history_text = "LỊCH SỬ HỘI THOẠI:\n" + "\n".join(lines) + "\n\n"

    active_context = (
        (
            f'Người dùng yêu cầu focus vào paper: "{paper_source}".'
            if paper_source
            else (
                "Research tự động tìm paper ArXiv liên quan để mở rộng "
                "kiến thức của bài học."
            )
        )
        if state.get("mode") == "research"
        else (
            f'Học viên đang xem trang {current_page} của tài liệu '
            f'"{slide_title}".'
        )
    )
    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=f"""{history_text}<user_question>
{question}
</user_question>

<slide_research_result>
{context}
</slide_research_result>

<active_context>
{active_context}
</active_context>"""),
    ]

    response = llm.invoke(messages)
    return {**state, "final_answer": response.content, "citations": citations}
