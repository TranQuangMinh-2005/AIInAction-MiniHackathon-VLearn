"""
Node: Tổng hợp câu trả lời cuối cùng.

Prompt thiết kế theo OpenAI Prompt Engineering best practices:
- Identity → Instructions → Context
- Giọng điệu sư phạm, thân thiện, dễ hiểu
"""

from langchain_core.messages import HumanMessage, SystemMessage
from agent.state import AgentState
from agent.llm import llm

SYSTEM_PROMPT = """# Identity

Bạn là **VLearn Tutor**, trợ lý học tập AI trên nền tảng VLearn.
Nhiệm vụ của bạn là chuyển kết quả nghiên cứu thành câu trả lời
thân thiện, dễ hiểu cho học viên.

# Instructions

1. Mở đầu bằng một câu chào ngắn gọn.
2. Trình bày nội dung với cấu trúc rõ ràng:
   - Dùng **in đậm** cho từ khóa.
   - Dùng bullet points cho danh sách.
   - Dùng `## Tiêu đề nhỏ` để phân chia.
3. Kết thúc: "Bạn có muốn tìm hiểu sâu hơn về phần nào không?"

## Quy tắc bắt buộc
- **TUYỆT ĐỐI KHÔNG** thêm kiến thức ngoài kết quả tìm kiếm.
- Nếu kết quả là `SLIDE_NOT_ENOUGH_INFO` → thông báo thiếu.
- **KHÔNG** bịa đặt số liệu, năm tháng.
- Tiếng Việt hoàn toàn.
"""

SYSTEM_PROMPT_WEB = """# Identity

Bạn là **VLearn Tutor**. Bạn đang trả lời từ kết quả tìm kiếm web.

# Instructions
1. Không chào hỏi, không "Bạn có muốn...", không bullet points.
2. Trả lời dạng **đoạn văn tự nhiên**, mạch lạc.
3. Câu hỏi định nghĩa → 1-2 đoạn giải thích.
4. Câu hỏi danh sách → liệt kê ngắn gọn.
5. Cuối cùng thêm dòng:
   📎 **Nguồn tham khảo:**
   - [Tiêu đề bài viết](url)
   - [Tiêu đề bài viết](url)

## Quy tắc
- **KHÔNG** thêm kiến thức ngoài kết quả tìm kiếm.
- **KHÔNG** bịa đặt.
- Tiếng Việt.
"""


def generate_answer(state: AgentState) -> AgentState:
    question = state["user_question"]
    slide_result = state.get("slide_search_result", "")
    web_result = state.get("web_search_result", "")
    current_page = state.get("current_page", 1)
    slide_title = state.get("slide_title", "")
    citations = state.get("citations", [])
    needs_web = state.get("needs_web_search", False)
    history = state.get("messages", [])

    if not slide_result.strip() or "SLIDE_NOT_ENOUGH_INFO" in slide_result:
        if web_result:
            prompt = SYSTEM_PROMPT_WEB
            context = web_result
            citations = citations + ["Web search"]
        else:
            return {
                **state,
                "final_answer": f"Rất tiếc, nội dung slide hiện tại không có đủ thông tin để trả lời câu hỏi này. Bạn có thể thử:\n- Chuyển sang trang khác có nội dung liên quan\n- Đặt câu hỏi khác về chủ đề trong slide\n- Bôi đen đoạn văn bản cụ thể trên slide để mình giải thích",
                "citations": citations,
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

    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=f"""{history_text}<user_question>
{question}
</user_question>

<slide_research_result>
{context}
</slide_research_result>

<current_slide_info>
Học viên đang xem trang {current_page} của tài liệu "{slide_title}".
</current_slide_info>"""),
    ]

    response = llm.invoke(messages)
    final = response.content

    return {
        **state,
        "final_answer": final,
        "citations": citations,
    }
