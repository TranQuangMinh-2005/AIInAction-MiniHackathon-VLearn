"""
t41 — Example Teacher: "cho mình ví dụ thực tế / câu hỏi ôn tập về phần này".

Yêu cầu SINH NỘI DUNG SƯ PHẠM dựa trên ngữ cảnh slide (trang đang xem hoặc
retrieval doc-scope k=2) — KHÔNG phải tra cứu text nguyên văn, nên không được
báo "slide không đủ thông tin" kiểu lookup. Chỉ khi không có bất kỳ khái niệm
nào (trang/context trống) mới nói rõ "trang này không có nội dung…".
"""

import re

from agent.state import AgentState
from agent.llm import llm
from agent.rag import slide_index, DOC_TITLES, citation_label

EXAMPLE_PROMPT = """Bạn là VLearn Tutor. Học viên đang xem trang {page} của tài liệu "{title}"
và muốn học sâu hơn bằng ví dụ + ôn tập. Dựa CHỈ vào ngữ cảnh slide bên dưới:

{context}

Hãy trả lời TIẾNG VIỆT theo cấu trúc:
## Ví dụ thực tế
- 1-2 ví dụ BÁM SÁT khái niệm chính trong ngữ cảnh (đời thực/ngành, rõ ràng, có thể tưởng tượng được)
## Câu hỏi ôn tập
- 1-2 câu hỏi ôn tập ngắn + đáp án 1-2 dòng kèm giải thích vì sao
Mỗi ý trích từ slide ghi nguồn "{label} - Trang N" ngay sau ý đó.
QUY TẮC: không bịa khái niệm ngoài ngữ cảnh; không chào hỏi."""

_NO_CONTEXT_MESSAGE = (
    "Trang này không có nội dung để bám (có thể là trang hình minh hoạ). "
    "Bạn thử chuyển sang trang có nội dung chữ, hoặc gõ rõ khái niệm muốn ví dụ "
    "— mình sẽ lấy từ toàn tài liệu."
)


def generate_examples(state: AgentState) -> AgentState:
    """Node: intent=example → final_answer = ví dụ thực tế + câu hỏi ôn tập + citations."""
    question = state.get("user_question", "")
    doc_id = state.get("active_doc_id") or state.get("summary_doc_id") or ""
    current_page = state.get("current_page") or 1

    # Anchor: (1) nội dung trang đang xem nếu có text, (2) retrieval doc-scope k=2.
    page_texts = [
        page_data
        for page_data in slide_index.page_texts
        if page_data["doc_id"] == doc_id and page_data["page"] == current_page
    ]
    if page_texts:
        context = f"--- {citation_label(doc_id)} - Trang {current_page} ---\n{page_texts[0]['text'][:2400]}"
        anchor_page = current_page
        citations = [f"{citation_label(doc_id)} - Trang {current_page}"]
    else:
        context, cites = slide_index.retrieve_context(
            question or "ví dụ thực tế",
            doc_id=doc_id or None,
            k=2,
            current_page=current_page,
            scope="doc" if doc_id else "corpus",
        )
        anchor_page = current_page
        citations = list(cites)
        if not context.strip():
            return {
                **state,
                "final_answer": _NO_CONTEXT_MESSAGE,
                "citations": [],
                "citation_details": [],
            }

    title = DOC_TITLES.get(doc_id, doc_id)
    try:
        response = llm.invoke(
            EXAMPLE_PROMPT.format(
                page=anchor_page,
                title=title,
                context=context,
                label=citation_label(doc_id),
            )
        )
        final = (response.content or "").strip()
    except Exception:
        final = (
            "## Ví dụ thực tế\nĐang gặp lỗi sinh nội dung — thử lại sau ít phút nhé.\n\n"
            "## Câu hỏi ôn tập\n(Bạn vẫn có thể bôi đen đoạn slide để hỏi cụ thể hơn.)"
        )
    if not final:
        final = _NO_CONTEXT_MESSAGE

    return {
        **state,
        "final_answer": final,
        "citations": citations[:2],
        "citation_details": [],
        "summary_doc_id": doc_id,
        "summary_page": anchor_page,
    }


# Tái dùng cho stream: chia chunk theo đoạn (giống summary).
def example_token_chunks(text: str, limit: int = 400) -> list[str]:
    parts = re.split(r"(\n{2,})", text)
    chunks: list[str] = []
    buffer = ""
    for part in parts:
        while len(part) > limit:
            if buffer:
                chunks.append(buffer)
                buffer = ""
            chunks.append(part[:limit])
            part = part[limit:]
        if buffer and len(buffer) + len(part) > limit:
            chunks.append(buffer)
            buffer = ""
        buffer += part
    if buffer:
        chunks.append(buffer)
    return chunks or [text]