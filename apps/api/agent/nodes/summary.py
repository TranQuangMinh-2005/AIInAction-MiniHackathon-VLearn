"""
A-03 — Summary Agent (AGENT-UPGRADE-PLAN.md): tóm tắt toàn tài liệu map-reduce.
t27 — tóm tắt PAPER: intent=summary + câu hỏi/history trỏ paper (arXiv, [S1]...) →
tóm tắt paper đó (local_rag search top-k, 1 LLM call, có citation [S1] + cache),
thay vì vô tình tóm tắt slide của doc đang mở.
"""

import json
import re
from pathlib import Path

from agent.state import AgentState
from agent.llm import llm
from agent.rag import slide_index, PDF_FILES

SUMMARY_CACHE_DIR = Path(__file__).resolve().parents[1] / ".summary_cache"

# Nhóm trang theo số trang doc để cân token: doc ≥ 120 trang → 16 trang/nhóm,
# 80-119 → 12, còn lại → 10. Giới hạn tối đa ~10 nhóm (tránh quá nhiều map call).
_MAX_MAP_GROUPS = 10
_PAGE_CHAR_LIMIT = 900

# t27 — paper summary
_PAPER_SUMMARY_TOP_K = 12
_PAPER_CHUNK_CHAR_LIMIT = 1200
_PAPER_SUMMARY_CUES = ("paper", "bài báo", "arxiv", "research paper")

# Day N → doc_id (bản full d3..d16; day05-ref là tài liệu tham khảo, không map).
_DAY_TO_DOC_ID = {
    1: "d3", 2: "d4", 3: "d5", 4: "d6", 5: "d7", 6: "d8",
    7: "d9", 8: "d10", 9: "d11", 10: "d12", 11: "d13",
    13: "d14", 14: "d15", 15: "d16",
}

MAP_PROMPT = """Bạn là trợ lý tóm tắt tài liệu slide cho khóa học AI Thực Chiến.
Tóm tắt ý chính của các trang slide dưới đây (tiếng Việt, bullet, tối đa 150 từ).

QUY TẮC:
- Mỗi ý trích/nêu phải có nguồn trang, ghi ngay sau ý đó dạng [Trang X].
- Chỉ dùng nội dung có trong văn bản được cấp, KHÔNG bịa thêm.
- Nếu nhóm trang không có nội dung hữu ích, ghi "(trang này không có nội dung text)".

Các trang:
{group_text}"""

REDUCE_PROMPT = """Bạn là VLearn Tutor. Dưới đây là tóm tắt từng nhóm trang của tài liệu
"NGUỒN: {doc_title}". Hãy hợp nhất thành bản tóm tắt HOÀN CHỈNH, tiếng Việt, theo cấu trúc:

## Mở đầu (2-3 câu: tài liệu này nói về gì)
## Ý chính từng phần (thead đề chính + bullet ý từng phần)
## Kết luận (2-3 câu: điểm mấu chốt cần nhớ)

QUY TẮC:
- Giữ nguyên citation [Trang X] đi kèm mỗi ý.
- Chỉ tổng hợp từ nội dung được cấp, không bịa, không thêm kiến thức ngoài.
- Không chào hỏi; kết thúc bằng dòng: "Bạn muốn mình đào sâu phần nào không?"

Tóm tắt các nhóm:
{group_summaries}"""


def resolve_summary_doc_id(question: str, active_doc_id: str) -> str | None:
    """Chọn doc cần tóm tắt: "day N"/"ngày N" trong câu hỏi (ưu tiên), else doc đang học."""
    match = re.search(r"\bday\s*(\d{1,2})\b|\bngày\s*(\d{1,2})\b", question, re.IGNORECASE)
    if match:
        number = int(match.group(1) or match.group(2))
        mapped = _DAY_TO_DOC_ID.get(number)
        if mapped:
            return mapped
        # day có số nhưng chưa có doc trong data (vd day 12) → về doc đang học
    return active_doc_id or None


def _group_size(page_count: int) -> int:
    if page_count >= 120:
        return 16
    if page_count >= 80:
        return 12
    return 10


def build_page_groups(pages: list[dict]) -> list[list[dict]]:
    """Chia trang thành nhóm tóm tắt (map), giới hạn _MAX_MAP_GROUPS nhóm."""
    if not pages:
        return []
    size = _group_size(len(pages))
    total_groups = (len(pages) + size - 1) // size
    if total_groups > _MAX_MAP_GROUPS:
        size = (len(pages) + _MAX_MAP_GROUPS - 1) // _MAX_MAP_GROUPS
    return [
        pages[index : index + size]
        for index in range(0, len(pages), size)
    ][:_MAX_MAP_GROUPS]


def _page_block(pages: list[dict]) -> str:
    lines = []
    for page in pages:
        text = (page["text"] or "")[:_PAGE_CHAR_LIMIT].strip()
        lines.append(f"[Trang {page['page']}]\n{text}")
    return "\n\n".join(lines)


def _map_summarize(group: list[dict]) -> str:
    response = llm.invoke(
        MAP_PROMPT.format(group_text=_page_block(group))
    )
    return (response.content or "").strip()


def _reduce_summaries(group_summaries: list[str], doc_title: str) -> str:
    block = "\n\n".join(
        f"### Nhóm {index + 1}\n{summary}"
        for index, summary in enumerate(group_summaries)
        if summary.strip()
    )
    if not block.strip():
        return "Không có nội dung text để tóm tắt trong tài liệu này."
    response = llm.invoke(REDUCE_PROMPT.format(doc_title=doc_title, group_summaries=block))
    return (response.content or "").strip()


def _cache_path(doc_id: str) -> Path:
    return SUMMARY_CACHE_DIR / f"{doc_id}.json"


def _file_signature(doc_id: str) -> str:
    path = PDF_FILES.get(doc_id)
    if path and path.exists():
        return f"{path.stat().st_mtime_ns}:{path.stat().st_size}"
    return "missing"


def load_cached_summary(doc_id: str) -> str | None:
    path = _cache_path(doc_id)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if data.get("doc_id") != doc_id or data.get("signature") != _file_signature(doc_id):
        return None
    return data.get("summary") or None


def store_cached_summary(doc_id: str, summary: str) -> None:
    try:
        SUMMARY_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "doc_id": doc_id,
            "signature": _file_signature(doc_id),
            "summary": summary,
        }
        _cache_path(doc_id).write_text(
            json.dumps(data, ensure_ascii=False, indent=1),
            encoding="utf-8",
        )
    except OSError:
        pass  # cache lỗi không ảnh hưởng kết quả trả về


# ── t27: tóm tắt PAPER (follow-up "tóm tắt paper này" sau Research) ──────────

PAPER_SUMMARY_PROMPT = """Bạn là VLearn Research Tutor. Dưới đây là các đoạn trích
từ paper được index (nhãn [S1], [S2]... kèm trang/dòng/mục).
Tóm tắt PAPER này bằng tiếng Việt theo cấu trúc:
## Mở đầu (paper này nghiên cứu gì)
## Ý chính từng phần (chủ đề chính + ý từng phần, giữ nhãn nguồn [S1]... ngay sau mỗi ý)
## Kết luận
QUY TẮC: chỉ dùng nội dung các đoạn được cấp; không bịa; không chào hỏi; kết thúc
bằng dòng "Bạn muốn mình đào sâu phần nào không?"

CÁC ĐOẠN:
{context}"""


def _history_entries(state: AgentState) -> list[dict]:
    entries = state.get("messages") or []
    normalized = []
    for entry in entries:
        if isinstance(entry, dict):
            normalized.append(entry)
        else:
            normalized.append({
                "role": "user" if getattr(entry, "type", "") in {"human", "user"} else "assistant",
                "content": str(getattr(entry, "content", "")),
            })
    return normalized


def _paper_summary_requested(question: str, state: AgentState) -> bool:
    q = (question or "").casefold()
    if any(cue in q for cue in _PAPER_SUMMARY_CUES):
        return True
    for entry in _history_entries(state):
        if entry.get("sources"):
            return True
        text = str(entry.get("content") or "").casefold()
        if "arxiv-" in text or ".pdf [" in text or "[s1]" in text:
            return True
    return False


def _paper_sources_from_history(state: AgentState) -> list[str]:
    sources: list[str] = []
    seen: set[str] = set()
    for entry in _history_entries(state):
        raw = entry.get("sources") or []
        if isinstance(raw, list):
            for source in raw:
                source = str(source or "").strip()
                if source and source not in seen:
                    seen.add(source)
                    sources.append(source)
        for match in re.findall(r"arxiv-[A-Za-z0-9._-]+\.pdf", str(entry.get("content") or "")):
            if match not in seen:
                seen.add(match)
                sources.append(match)
    return sources[:3]


def _try_paper_summary(state: AgentState, question: str) -> AgentState | None:
    """None = không phải yêu cầu paper → đi slide path như cũ (t27)."""
    if not _paper_summary_requested(question, state):
        return None

    from local_rag.service import RAGService

    service = RAGService.from_env()
    sources = _paper_sources_from_history(state)
    if not sources:
        # t27 — history (đã bị graph normalize) không có sources → đọc Memory
        from agent.memory import get_state

        learner_id = state.get("learner_id")
        paper = get_state(learner_id).get("paper_source") if learner_id else None
        if paper:
            sources = [paper]
    if not sources:
        return {
            **state,
            "final_answer": (
                "Bạn muốn mình tóm tắt paper nào? Hãy hỏi Research một chủ đề trước "
                "(ví dụ \"tìm paper về X\"), rồi mình sẽ tóm tắt paper đó."
            ),
            "citations": [],
            "citation_details": [],
            "summary_doc_id": None,
        }

    resolved = next((s for s in sources if service.resolve_source(s)), None)
    if not resolved:
        return {
            **state,
            "final_answer": (
                f"Paper {sources[0]} chưa được index — bạn vào Research và tìm "
                "paper này trước nhé, rồi mình tóm tắt."
            ),
            "citations": [],
            "citation_details": [],
            "summary_doc_id": None,
        }

    cache_key = f"paper-{resolved}"
    cached = _load_paper_cache(resolved)
    if cached:
        return {
            **state,
            "final_answer": cached["summary"],
            "citations": cached.get("citations") or [],
            "citation_details": cached.get("details") or [],
            "summary_doc_id": cache_key,
            "summary_cache_hit": True,
        }

    try:
        results = service.search(question, top_k=_PAPER_SUMMARY_TOP_K, source=resolved)
    except Exception:
        results = service.keyword_search(question, top_k=_PAPER_SUMMARY_TOP_K, source=resolved)
    if not results:
        return {
            **state,
            "final_answer": f"Không lấy được nội dung paper {resolved} để tóm tắt.",
            "citations": [],
            "citation_details": [],
            "summary_doc_id": None,
        }

    blocks: list[str] = []
    citations: list[str] = []
    details: list[dict] = []
    for index, result in enumerate(results, 1):
        label = f"S{index}"
        content = (result.content or "")[:_PAPER_CHUNK_CHAR_LIMIT].strip()
        blocks.append(
            f"[{label}] Trang {result.page}, dòng {result.line_start}-{result.line_end}, "
            f"mục {result.section}\n{content}"
        )
        citations.append(
            f"{result.source} - Trang {result.page}, dòng {result.line_start}-{result.line_end} [{label}]"
        )
        details.append({
            "label": label,
            "title": (result.title or resolved)[:80],
            "source": result.source,
            "page": result.page,
            "line_start": result.line_start,
            "line_end": result.line_end,
            "quote": content,
        })

    final: str | None = None
    try:
        response = llm.invoke(PAPER_SUMMARY_PROMPT.format(context="\n\n".join(blocks)))
        final = (response.content or "").strip()
    except Exception:
        final = None
    if not final:
        final = (
            "## Tóm tắt paper (bản hợp nhất gặp lỗi — hiển thị các đoạn chính được index):\n\n"
            + "\n\n".join(blocks)
        )
    _store_paper_cache(resolved, final, citations, details)
    return {
        **state,
        "final_answer": final,
        "citations": citations,
        "citation_details": details,
        "summary_doc_id": cache_key,
        "summary_cache_hit": False,
    }


def _load_paper_cache(source: str) -> dict | None:
    """t27 — cache paper kèm citations (để lượt sau vẫn hiển thị [S1]...)."""
    path = _cache_path(f"paper-{source}")
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data.get("summary"), str) or not data.get("summary"):
        return None
    return data


def _store_paper_cache(source: str, summary: str, citations: list, details: list) -> None:
    try:
        SUMMARY_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "doc_id": f"paper-{source}",
            "signature": "paper-index",
            "summary": summary,
            "citations": citations,
            "details": details,
        }
        _cache_path(f"paper-{source}").write_text(
            json.dumps(data, ensure_ascii=False, indent=1),
            encoding="utf-8",
        )
    except OSError:
        pass


# ── t36: tóm tắt THEO TRANG ("trang này" / "trang N" / "trang đang xem") ─────

_PAGE_SCOPE_RES = [
    re.compile(r"\btrang\s+này\b"),
    re.compile(r"\btrang\s+hiện\s+(?:tại|đang)\b"),
    re.compile(r"\btrang\s+đang\s+xem\b"),
    re.compile(r"\b(page|trang)\s+\d+\b"),
]

_PAGE_SUMMARY_PROMPT = """Bạn là VLearn Tutor. Tóm tắt NGẮN GỌN nội dung trang {page}
của tài liệu "{title}" (tiếng Việt: 1 đoạn ngắn + 3-6 bullet nếu có nhiều ý).
QUY TẮC: chỉ dùng nội dung trang; nếu trang không có nội dung hữu ích, ghi rõ.
Không chào hỏi.

NỘI DUNG TRANG {page}:
{text}"""


def _page_request(question: str) -> tuple[bool, int | None]:
    """(có phải yêu cầu theo trang?, số trang explicit hoặc None = trang đang xem)."""
    q = (question or "").casefold()
    if not any(pattern.search(q) for pattern in _PAGE_SCOPE_RES):
        return False, None
    explicit = re.search(r"(?:page|trang)\s+(\d+)\b", q)
    return True, int(explicit.group(1)) if explicit else None


def _try_page_summary(state: AgentState, question: str, doc_id: str) -> AgentState | None:
    """t36 — "tóm tắt trang này/trang N" → tóm tắt 1 trang + citation; None = không phải."""
    is_page, explicit_page = _page_request(question)
    if not is_page:
        return None

    page = explicit_page or state.get("current_page") or 1
    pages = [
        page_data
        for page_data in slide_index.page_texts
        if page_data["doc_id"] == doc_id and page_data["page"] == page
    ]
    if not pages:
        return {
            **state,
            "final_answer": (
                f"Trang {page} của tài liệu này chưa có nội dung text để tóm tắt "
                "(có thể là trang ảnh — ngày 3 hiện đã có OCR, các tài liệu khác đều có text)."
            ),
            "citations": [],
            "citation_details": [],
            "summary_doc_id": doc_id,
            "summary_page": page,
        }

    from agent.rag import DOC_TITLES, citation_label

    text = pages[0]["text"][: _PAGE_CHAR_LIMIT * 3]
    try:
        response = llm.invoke(
            _PAGE_SUMMARY_PROMPT.format(
                page=page, title=DOC_TITLES.get(doc_id, doc_id), text=text
            )
        )
        final = (response.content or "").strip()
    except Exception:
        final = f"**Trang {page} — nội dung chính:**\n\n{text[:1200]}"

    label = citation_label(doc_id)
    return {
        **state,
        "final_answer": final,
        "citations": [f"{label} - Trang {page}"],
        "citation_details": [],
        "summary_doc_id": doc_id,
        "summary_page": page,
    }


def summarize_doc(state: AgentState) -> AgentState:
    """Node Summary: intent=summary → final_answer = tóm tắt có cấu trúc + citations.

    t27 — ưu tiên PAPER summary khi câu hỏi/history trỏ paper (sau turn Research),
    t36 — phân biệt PAGE-scope ("trang này/trang N") → tóm tắt 1 trang; còn lại
    tóm tắt slide doc-scope (map-reduce cũ giữ nguyên)."""
    question = state.get("user_question", "")
    active_doc_id = state.get("active_doc_id") or ""

    paper_result = _try_paper_summary(state, question)
    if paper_result is not None:
        return paper_result

    doc_id = resolve_summary_doc_id(question, active_doc_id)

    if not doc_id or doc_id not in PDF_FILES:
        return {
            **state,
            "final_answer": (
                "Mình tìm không thấy tài liệu cần tóm tắt — bạn đang mở tài liệu "
                "nào thì mình tóm tắt tài liệu đó nhé (ví dụ hỏi: \"tóm tắt day 4\")."
            ),
            "citations": [],
            "citation_details": [],
            "summary_doc_id": doc_id,
        }

    # t36 — page-scope: "tóm tắt trang này / trang 5 / trang đang xem"
    page_result = _try_page_summary(state, question, doc_id)
    if page_result is not None:
        return page_result

    cached = load_cached_summary(doc_id)
    if cached:
        return {
            **state,
            "final_answer": cached,
            "citations": [],
            "citation_details": [],
            "summary_doc_id": doc_id,
            "summary_cache_hit": True,
        }

    pages = [
        page
        for page in slide_index.page_texts
        if page["doc_id"] == doc_id
    ]
    if not pages:
        return {
            **state,
            "final_answer": (
                "Tài liệu này hiện chưa có nội dung text để tóm tắt "
                "(có thể là bản scan chưa OCR)."
            ),
            "citations": [],
            "citation_details": [],
            "summary_doc_id": doc_id,
        }

    try:
        group_summaries = [
            _map_summarize(group)
            for group in build_page_groups(pages)
        ]
    except Exception:
        return {
            **state,
            "final_answer": (
                "Mình đang gặp lỗi khi tóm tắt tài liệu này — vui lòng thử lại "
                "sau ít phút. (Gợi ý: hỏi tóm tắt theo từng phần nhỏ hơn.)"
            ),
            "citations": [],
            "citation_details": [],
            "summary_doc_id": doc_id,
        }

    from agent.rag import DOC_TITLES

    doc_title = DOC_TITLES.get(doc_id, doc_id)
    try:
        final = _reduce_summaries(group_summaries, doc_title)
    except Exception:
        # Fallback: ghép tóm tắt nhóm đã có (không mất công map)
        final = (
            "## Tóm tắt theo nhóm trang (bản hợp nhất gặp lỗi — hiển thị "
            "tóm tắt từng phần):\n\n"
            + "\n\n".join(group_summaries)
        )

    store_cached_summary(doc_id, final)
    return {
        **state,
        "final_answer": final,
        "citations": [],
        "citation_details": [],
        "summary_doc_id": doc_id,
        "summary_cache_hit": False,
    }