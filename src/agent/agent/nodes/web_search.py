"""Research scientific papers, with an optional user-selected PDF focus."""

import re

from agent.llm import llm
from agent.state import AgentState
from agent.tools import (
    query_arxiv_full_text,
    query_local_papers,
    query_relevant_local_paper,
)


def _build_research_query(question: str, slide_context: str) -> str | None:
    """Turn a Vietnamese/English learning question into a compact arXiv query."""
    response = llm.invoke(
        """Bạn là router tìm kiếm paper khoa học cho khóa học AI/ML.
Từ câu hỏi và ngữ cảnh slide, trả về DUY NHẤT 4-10 từ khóa tiếng Anh phù hợp
để tìm trên arXiv. Không giải thích, không dấu ngoặc, không tiền tố.
Nếu câu hỏi rõ ràng ngoài phạm vi học thuật/công nghệ, trả về OUT_OF_SCOPE.

Câu hỏi:
"""
        + question
        + "\n\nNgữ cảnh slide:\n"
        + slide_context[:1200]
    )
    query = " ".join(response.content.split()).strip("`\"' ")
    if query.upper() == "OUT_OF_SCOPE":
        return None
    query = re.sub(r"^(?:query|keywords?)\s*:\s*", "", query, flags=re.I)
    return query[:240] or question


def _is_primary_topic_match(
    search_query: str,
    paper_title: str,
    topic_preview: str,
) -> bool:
    """Reject papers that merely mention the topic in related work."""
    response = llm.invoke(
        """Bạn đang kiểm tra độ phù hợp của paper trước khi tái sử dụng.
Trả về DUY NHẤT YES nếu chủ đề nghiên cứu chính của paper trực tiếp phù hợp
với truy vấn. Trả về NO nếu paper chỉ nhắc thoáng qua, dùng như kỹ thuật phụ,
hoặc có một chủ đề chính khác. Hãy đánh giá nghiêm ngặt.

Truy vấn:
"""
        + search_query
        + "\n\nTiêu đề paper:\n"
        + paper_title
        + "\n\nTitle/abstract/introduction preview:\n"
        + topic_preview[:1800]
    )
    return response.content.strip().upper().splitlines()[0] == "YES"


def search_online(state: AgentState) -> AgentState:
    question = state["user_question"]
    paper_source = state.get("paper_source")
    citations = list(state.get("citations", []))
    citation_details = list(state.get("citation_details", []))

    try:
        if paper_source:
            context, local_citations, local_details = query_local_papers(
                question,
                paper_source,
            )
        else:
            search_query = _build_research_query(
                question,
                state.get("slide_context", ""),
            )
            if not search_query:
                return {
                    **state,
                    "web_search_result": (
                        "Câu hỏi này nằm ngoài phạm vi nội dung học thuật "
                        "của bài học nên Research không tìm paper."
                    ),
                    "citations": [],
                    "citation_details": [],
                }
            local_match = query_relevant_local_paper(
                question,
                search_query,
                topic_validator=_is_primary_topic_match,
            )
            if local_match:
                context, local_citations, local_details = local_match
            else:
                context, local_citations, local_details = (
                    query_arxiv_full_text(
                        question,
                        search_query,
                    )
                )
            if not context:
                return {
                    **state,
                    "web_search_result": (
                        "Không tìm thấy paper phù hợp trên arXiv cho câu hỏi "
                        "này. Hãy thử mô tả chủ đề cụ thể hơn."
                    ),
                    "citations": [],
                    "citation_details": [],
                }
        citations.extend(local_citations)
        citation_details.extend(local_details)
        return {
            **state,
            "web_search_result": context,
            "citations": citations,
            "citation_details": citation_details,
        }
    except Exception as exc:
        target = paper_source or "arXiv"
        return {
            **state,
            "web_search_result": (
                f"Không thể research từ {target}: {exc}"
            ),
            "citations": [],
            "citation_details": [],
        }
