"""
VLearn Agent API Server.
Chạy lệnh: python server.py
"""

import json
import os
import re
import time
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
from agent.graph import build_graph, AgentState, wants_paper_search
from agent.rag import slide_index, DOC_TITLES
from agent.security import validate_input
from agent.llm import llm
from agent.nodes.orchestrator import orchestrate
from agent.nodes.tutor_coach import build_envelope, remember_turn
from agent.memory import build_context, get_state, get_page_notes, set_page_note, update_state
from agent.analytics import build_gaps
from agent.observability import (
    WINDOW_HOURS,
    admin_metrics,
    new_trace_id,
    record_feedback,
    record_trace,
)
from langchain_core.messages import SystemMessage, HumanMessage
from local_rag.agent_tool import ask_research_papers
from local_rag.service import RAGService
from agent.nodes.web_search import _select_best_arxiv_paper
from agent.tools.paper.paper import arxiv_download_pdf, arxiv_search

app = FastAPI(title="VLearn Agent API")

AI_UNAVAILABLE_MESSAGE = (
    "Dịch vụ AI đang tạm thời không phản hồi. "
    "Vui lòng thử lại sau ít phút."
)

_CORS_DEFAULTS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
]
# Render/deploy: mở rộng origin qua env CORS_ORIGINS (comma-separated),
# vd: https://vlearn-web.onrender.com,https://vlearn-web-abc.onrender.com
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "").split(",")
    if origin.strip()
] + _CORS_DEFAULTS

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def citations_used_in_answer(
    citations: list[str],
    answer: str,
) -> list[str]:
    used_labels = labels_used_in_answer(answer)
    used: list[str] = []
    unlabeled: list[str] = []
    for citation in citations:
        labels = re.findall(r"\[([^\]]+)\]", citation)
        if not labels:
            unlabeled.append(citation)
            continue
        if any(label in used_labels for label in labels):
            used.append(citation)
    return unlabeled + used


def labels_used_in_answer(answer: str) -> set[str]:
    """Parse current [S1] labels and legacy PAPER/ARXIV markers."""
    labels: set[str] = set()
    for marker in re.findall(r"\[([^\]]+)\]", answer):
        labels.update(
            part.strip()
            for part in marker.split(",")
            if re.fullmatch(
                r"(?:S\d+|(?:PAPER|ARXIV)-\d+)",
                part.strip(),
            )
        )
    return labels


def citation_details_used_in_answer(
    details: list[dict],
    answer: str,
) -> list[dict]:
    used_labels = labels_used_in_answer(answer)
    return [
        detail
        for detail in details
        if detail.get("label", "") in used_labels
    ]


@app.on_event("startup")
async def startup():
    slide_index.load()

class ChatRequest(BaseModel):
    question: str
    active_doc_id: str
    current_page: int
    history: list[dict] = []
    mode: str = "normal"
    paper_source: str | None = None
    # A-06 — anonymous per-browser token (client sinh, localStorage); optional
    learner_id: str | None = None


class PaperAskRequest(BaseModel):
    question: str
    source: str | None = None
    top_k: int = 6


class PaperImportRequest(BaseModel):
    query: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[str]
    citation_details: list[dict] = []
    current_page: int
    slide_title: str
    # A-05 envelope — optional, backward-compatible (frontend cũ bỏ qua)
    move: str = "review_concept"
    misconceptions: list[str] = []
    follow_ups: list[str] = []
    asked_check_question: bool = False
    # A-07 — trace (optional, backward-compatible)
    trace_id: str = ""
    trace: dict = {}


@app.get("/api/health")
def health():
    paper_rag = RAGService.from_env().health()
    return {
        "status": "ok",
        "slide_pages": len(slide_index.page_texts),
        "paper_rag": paper_rag,
    }


@app.get("/api/papers")
def papers():
    return {"papers": RAGService.from_env().documents()}


@app.post("/api/papers/import-arxiv")
def import_arxiv_paper(req: PaperImportRequest):
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query không được trống.")
    try:
        matches = arxiv_search(query, max_results=5)
        if not matches:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy paper phù hợp trên arXiv.",
            )
        selected_index = (
            _select_best_arxiv_paper(query, query, matches)
            if len(matches) > 1
            else 0
        )
        paper = matches[selected_index]
        pdf_url = paper.get("pdf_url", "")
        if not pdf_url:
            raise HTTPException(
                status_code=404,
                detail="Paper arXiv không có PDF.",
            )
        pdf = arxiv_download_pdf(pdf_url)
        if not pdf.startswith(b"%PDF"):
            raise HTTPException(
                status_code=502,
                detail="arXiv không trả về PDF hợp lệ.",
            )

        raw_id = (
            paper.get("abstract_url", "").rstrip("/").split("/")[-1]
            or "paper"
        )
        safe_id = re.sub(r"[^A-Za-z0-9._-]+", "-", raw_id).strip("-")
        source = f"arxiv-{safe_id}.pdf"
        service = RAGService.from_env()
        service.settings.pdf_dir.mkdir(parents=True, exist_ok=True)
        destination = service.settings.pdf_dir / source
        temporary = destination.with_suffix(".pdf.part")
        temporary.write_bytes(pdf)
        temporary.replace(destination)
        report = service.ingest_directory(reset=False)
        document = next(
            (
                item
                for item in service.documents()
                if item["source"] == source
            ),
            None,
        )
        return {
            "paper": document,
            "arxiv": {
                "title": paper.get("title", ""),
                "abstract_url": paper.get("abstract_url", ""),
                "pdf_url": pdf_url,
            },
            "ingest": report.to_dict(),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/papers/ask")
def papers_ask(req: PaperAskRequest):
    """Direct diagnostic endpoint; the Agent uses this same tool boundary."""
    try:
        return ask_research_papers(
            question=req.question,
            source=req.source,
            top_k=req.top_k,
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


_PAPER_SOURCE_RE = re.compile(r"^arxiv-[A-Za-z0-9._-]+\.pdf$")


@app.get("/api/papers/{source}/pdf")
def paper_pdf(source: str):
    """t28 — phục vụ PDF paper đã index cho viewer (citation [S1] nhảy trang).

    Validate tên an toàn (arxiv-*.pdf) + resolve qua RAGService → 404 nếu chưa
    có; trả application/pdf. Không expose path tuỳ ý."""
    if not _PAPER_SOURCE_RE.fullmatch(source):
        raise HTTPException(status_code=400, detail="Tên paper không hợp lệ.")
    service = RAGService.from_env()
    resolved = service.resolve_source(source)
    if not resolved:
        raise HTTPException(status_code=404, detail="Paper chưa được index.")
    path = service.settings.pdf_dir / resolved
    if not path.exists():
        raise HTTPException(status_code=404, detail="File PDF của paper không tồn tại.")
    return FileResponse(path, media_type="application/pdf", filename=resolved)

def resolve_slide_title(doc_id: str) -> str:
    """A-02 — tên tài liệu từ metadata (DOC_TITLES), thay hardcode d1/d2."""
    return DOC_TITLES.get(doc_id, "Bài giảng AI Thực Chiến")


def _remember_paper_source(req: ChatRequest, result: dict) -> None:
    """t27 — Research trả paper arXiv → lưu paper_source vào Memory (A-06).
    LangGraph normalize messages (mất key sources của frontend) nên follow-up
    "tóm tắt paper này" đọc paper từ memory — sống qua mọi path."""
    if not req.learner_id:
        return
    details = result.get("citation_details") or []
    sources = [
        str(detail.get("source") or "")
        for detail in details
        if str(detail.get("source") or "").startswith("arxiv-")
    ]
    if not sources:
        return
    try:
        update_state(req.learner_id, paper_source=sources[0])
    except Exception:
        pass


def build_initial_state(req: ChatRequest, slide_context: str, citations: list[str], is_research: bool) -> AgentState:
    """State chung cho /api/chat + /api/chat/stream (A-01 orchestrator fields)."""
    slide_title = resolve_slide_title(req.active_doc_id)
    return {
        "user_question": req.question,
        "slide_context": slide_context,
        "current_page": req.current_page,
        "slide_title": slide_title,
        "paper_source": req.paper_source,
        "messages": req.history,
        "slide_search_result": "" if is_research else None,
        "web_search_result": None,
        "final_answer": None,
        "citations": citations,
        "citation_details": [],
        "needs_web_search": is_research,
        "error": None,
        "mode": req.mode,
        "original_question": req.question,
        "normalized_question": None,
        "intent": None,
        "orchestrator_note": None,
        "retrieval_scope": "auto",
        "active_doc_id": req.active_doc_id,
        "summary_doc_id": None,
        "summary_cache_hit": None,
        # A-05/A-06
        "move": "review_concept",
        "misconceptions": [],
        "follow_ups": [],
        "asked_check_question": False,
        "learner_id": req.learner_id,
        "memory_context": build_context(req.learner_id) if req.learner_id else "",
    }


def retrieve_slide_context(req: ChatRequest) -> tuple[str, list[str]]:
    """A-02 — retrieval: research giữ k=2 doc-only (chỉ làm context cho paper query);
    normal = doc-first + corpus fallback + page-in-view boost."""
    if req.mode == "research":
        return slide_index.retrieve_context(
            req.question,
            doc_id=req.active_doc_id,
            k=2,
            scope="doc",
        )
    return slide_index.retrieve_context(
        req.question,
        doc_id=req.active_doc_id,
        k=3,
        current_page=req.current_page,
        scope="auto",
    )


def status_event(phase: str, detail: str = "", elapsed_ms: int = 0) -> str:
    """A-04 — SSE status event. Backward-compatible: frontend cũ bỏ qua event lạ."""
    payload = {"status": phase, "detail": detail, "elapsed_ms": elapsed_ms}
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


# ── A-06 Memory endpoints (anonymous per-browser, không PII) ─────────────────

class MemoryStateRequest(BaseModel):
    doc_id: str | None = None
    page: int | None = None
    concepts: list[str] = []
    misconceptions: list[str] = []
    notes: list[str] = []


@app.get("/api/learners/{learner_id}/state")
def learner_state(learner_id: str):
    """State memory của learner; learner_id lạ → state rỗng (không crash)."""
    return get_state(learner_id)


@app.put("/api/learners/{learner_id}/state")
def learner_update(learner_id: str, req: MemoryStateRequest):
    """Upsert nhẹ state memory (merge list dedupe; doc/page thay thế)."""
    return update_state(
        learner_id,
        doc_id=req.doc_id,
        page=req.page,
        concepts=req.concepts,
        misconceptions=req.misconceptions,
        notes=req.notes,
    )


# ── P0-4: Notes persist + sync (per learner · doc · trang) ───────────────────

class NoteRequest(BaseModel):
    doc_id: str
    page: int
    text: str = ""


@app.get("/api/learners/{learner_id}/notes")
def learner_notes(learner_id: str, doc_id: str | None = None):
    """P0-4 — danh sách note của learner (lọc theo doc nếu có)."""
    return {"notes": get_page_notes(learner_id, doc_id)}


@app.put("/api/learners/{learner_id}/notes")
def learner_note_upsert(learner_id: str, req: NoteRequest):
    """P0-4 — upsert note (doc, trang); text rỗng = xoá note."""
    note = set_page_note(learner_id, req.doc_id, req.page, req.text)
    current = next(
        (n for n in note.get("page_notes", [])
         if str(n.get("doc_id")) == req.doc_id and int(n.get("page", -1)) == req.page),
        None,
    )
    return {"note": current, "ok": True}


@app.get("/api/learners/{learner_id}/gaps")
def learner_gaps(learner_id: str):
    """A-10 — lỗ hổng kiến thức + gợi ý ôn tập (memory + trace + feedback, local)."""
    return build_gaps(learner_id)


def summary_token_chunks(text: str, limit: int = 400) -> list[str]:
    """A-03 — chia tóm tắt dài thành token-chunk theo đoạn để stream mượt."""
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


def _tools_for_result(result: dict, is_research: bool, intent: str | None) -> list[str]:
    """A-07 — liệt kê tool thực tế đã dùng trong turn (cho trace + gate tool-match)."""
    if intent == "off_topic":
        return ["refuse_off_topic"]
    if intent == "summary":
        return ["summarize_doc"]
    if intent == "example":
        return ["example_teacher"]  # t41: sinh ví dụ/câu hỏi ôn tập sư phạm
    web_text = (result.get("web_search_result") or "").casefold()
    if web_text:
        if "kết quả tìm web" in web_text or "tavily" in web_text or "duckduckgo" in web_text:
            return ["web_search_tavily"]
        return ["web_search_arxiv"]
    if result.get("slide_search_result"):
        return ["slide_search"]
    return ["clarify"]


class FeedbackRequest(BaseModel):
    trace_id: str = ""
    rating: int
    comment: str = ""


@app.post("/api/feedback")
def feedback(req: FeedbackRequest):
    """A-07 — rating 👍(1)/👎(-1) gắn trace_id; lưu JSONL observability."""
    if not record_feedback(req.trace_id, req.rating, req.comment):
        raise HTTPException(status_code=400, detail="rating phải là 1 (👍) hoặc -1 (👎).")
    return {"ok": True, "trace_id": req.trace_id}


@app.get("/api/admin/metrics")
def metrics(window: str = "24h"):
    """P0-5 — metrics tổng hợp (1h/24h/7d) cho mini-dashboard /admin.

    Nguồn: traces.jsonl + feedback.jsonl (observability) — không gọi LLM.
    """
    if window not in WINDOW_HOURS:
        raise HTTPException(
            status_code=422,
            detail="window phải là 1h, 24h hoặc 7d.",
        )
    return admin_metrics(window_hours=WINDOW_HOURS[window])


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """A-01 — luồng thống nhất qua graph (orchestrator → slide | web → answer)."""
    is_safe, reason = validate_input(req.question)
    if not is_safe:
        return ChatResponse(
            answer=f"⚠️ {reason}",
            citations=[],
            citation_details=[],
            current_page=req.current_page,
            slide_title="",
        )

    is_research = req.mode == "research"
    slide_context, rag_citations = retrieve_slide_context(req)
    citations = [] if is_research else (rag_citations[:1] if rag_citations else [])
    slide_title = resolve_slide_title(req.active_doc_id)
    started = time.monotonic()

    initial_state: AgentState = build_initial_state(
        req, slide_context, citations, is_research
    )
    result = build_graph().invoke(initial_state)
    _remember_paper_source(req, result)
    answer = result.get("final_answer", "Không thể tạo câu trả lời.")
    # A-07 — trace mỗi turn (latency thật, tokens/cost ước lượng, tool routing)
    trace_id = new_trace_id()
    trace = record_trace(
        trace_id=trace_id,
        mode=req.mode,
        intent=result.get("intent"),
        tools=_tools_for_result(result, is_research, result.get("intent")),
        answer_text=answer,
        input_text=req.question,
        latency_ms=int((time.monotonic() - started) * 1000),
        learner_id=req.learner_id,
    )
    response = ChatResponse(
        answer=answer,
        citations=citations_used_in_answer(
            result.get("citations", citations),
            answer,
        ),
        citation_details=citation_details_used_in_answer(
            result.get("citation_details", []),
            answer,
        ),
        current_page=req.current_page,
        slide_title=slide_title,
        # A-05 envelope (optional — backward-compatible)
        move=result.get("move") or "review_concept",
        misconceptions=result.get("misconceptions") or [],
        follow_ups=result.get("follow_ups") or [],
        asked_check_question=bool(result.get("asked_check_question")),
        trace_id=trace_id,
        trace=trace,
    )
    return JSONResponse(
        content=response.model_dump(),
        headers={"X-VLearn-Trace-Id": trace_id},
    )


@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    """
    Streaming endpoint: chạy graph → stream final answer token by token.
    """
    is_safe, reason = validate_input(req.question)
    if not is_safe:
        async def error_stream():
            yield f"data: {json.dumps({'error': reason})}\n\n"
        return StreamingResponse(error_stream(), media_type="text/event-stream")

    is_research = req.mode == "research"
    slide_context, rag_citations = retrieve_slide_context(req)
    citations = [] if is_research else (rag_citations[:1] if rag_citations else [])
    slide_title = resolve_slide_title(req.active_doc_id)
    initial_state_stream: AgentState = build_initial_state(
        req, slide_context, citations, is_research
    )

    async def event_stream():
        from agent.nodes.slide_search import search_slide, decide_search
        from agent.nodes.web_search import search_online
        from agent.nodes.answer import (
            SYSTEM_PROMPT as SLIDE_PROMPT,
            SYSTEM_PROMPT_WEB as WEB_PROMPT,
            without_slide_citations,
            refuse_off_topic,
        )
        from agent.nodes.summary import summarize_doc
        from agent.nodes.examples import example_token_chunks, generate_examples

        def _ms() -> int:
            return int((time.monotonic() - started) * 1000)

        started = time.monotonic()
        trace_id = new_trace_id()

        def finish_trace(answer_text: str = "", error: str | None = None) -> None:
            record_trace(
                trace_id=trace_id,
                mode=req.mode,
                intent=result.get("intent"),
                tools=_tools_for_result(result, is_research, result.get("intent")),
                answer_text=answer_text,
                input_text=req.question,
                error=error,
                latency_ms=_ms(),
                learner_id=req.learner_id,
            )

        # A-01 — Orchestrator: chuẩn hoá input (teencode/spell-fix) + phân loại intent.
        yield status_event("routing")
        result = orchestrate(initial_state_stream)
        if result.get("intent") == "off_topic":
            refused = refuse_off_topic(result)
            envelope = {
                "move": "validate",
                "misconceptions": [],
                "follow_ups": ["Bạn muốn hỏi gì về slide đang xem không?"],
                "asked_check_question": False,
            }
            yield f"data: {json.dumps({'token': refused['final_answer']})}\n\n"
            finish_trace(answer_text=refused["final_answer"])
            yield (
                "data: "
                + json.dumps({"done": True, "trace_id": trace_id, "citations": [], "citation_details": [], **envelope})
                + "\n\n"
            )
            return

        # t41 — Example Teacher: intent=example → sinh ví dụ/câu hỏi ôn tập sư phạm
        if result.get("intent") == "example":
            yield status_event("answering", elapsed_ms=_ms())
            result = generate_examples(result)
            envelope = build_envelope(result)
            answer_text = result.get("final_answer", "")
            example_citations = result.get("citations") or []
            for chunk in example_token_chunks(answer_text):
                yield f"data: {json.dumps({'token': chunk}, ensure_ascii=False)}\n\n"
            yield (
                "data: "
                + json.dumps(
                    {
                        "done": True,
                        "trace_id": trace_id,
                        "citations": example_citations,
                        "citation_details": [],
                        "full_answer": answer_text,
                        **envelope,
                    },
                    ensure_ascii=False,
                )
                + "\n\n"
            )
            remember_turn(result, envelope)
            finish_trace(answer_text=answer_text)
            return

        # A-03 — Summary Agent: intent=summary → tóm tắt map-reduce, stream theo đoạn.
        if result.get("intent") == "summary":
            yield status_event("summarizing", elapsed_ms=_ms())
            result = summarize_doc(result)
            envelope = build_envelope(result)
            answer_text = result.get("final_answer", "")
            # t27 — paper summary trả citation [S1]... kèm theo turn answer
            summary_citations = result.get("citations") or []
            summary_details = result.get("citation_details") or []
            yield status_event("answering", elapsed_ms=_ms())
            for chunk in summary_token_chunks(answer_text):
                yield f"data: {json.dumps({'token': chunk}, ensure_ascii=False)}\n\n"
            yield (
                "data: "
                + json.dumps(
                    {
                        "done": True,
                        "trace_id": trace_id,
                        "citations": summary_citations,
                        "citation_details": summary_details,
                        "full_answer": answer_text,
                        **envelope,
                    },
                    ensure_ascii=False,
                )
                + "\n\n"
            )
            remember_turn(result, envelope)
            finish_trace(answer_text=answer_text)
            return

        # Research mode skips the slide LLM call (retrieval context only).
        web_ran = False
        if is_research:
            yield status_event("rewriting_query", elapsed_ms=_ms())
            result = search_online(result)
            web_ran = True
            _remember_paper_source(req, result)
            if not result.get("citations"):
                envelope = build_envelope(result)
                message = result.get(
                    "web_search_result",
                    "Không tìm thấy paper phù hợp trên arXiv.",
                )
                yield status_event("answering", elapsed_ms=_ms())
                yield f"data: {json.dumps({'token': message})}\n\n"
                yield (
                    "data: "
                    + json.dumps({"done": True, "trace_id": trace_id, "citations": [], "citation_details": [], **envelope})
                    + "\n\n"
                )
                remember_turn(result, envelope)
                finish_trace(answer_text=message)
                return
            yield status_event("reading_paper", elapsed_ms=_ms())
        else:
            yield status_event("searching_slide", elapsed_ms=_ms())
            # A-08 — normal nhưng câu hỏi muốn paper ("tìm paper về X") → research path
            if wants_paper_search(result.get("user_question", "")):
                result = search_online(result)
                web_ran = True
                yield status_event("reading_paper", elapsed_ms=_ms())
            else:
                result = search_slide(result)
                result = decide_search(result)
        if (result.get("needs_web_search") and not is_research) and not web_ran:
            yield status_event("searching_arxiv", elapsed_ms=_ms())
            result = search_online(result)
            yield status_event("reading_paper", elapsed_ms=_ms())
        yield status_event("answering", elapsed_ms=_ms())
        envelope = build_envelope(result)

        # Stream final answer
        question = result["user_question"]
        slide_result = result.get("slide_search_result", "") or ""
        web_result = result.get("web_search_result", "") or ""
        current_page = result.get("current_page", 1)
        slide_title = result.get("slide_title", "")
        result_citations = result.get("citations", [])
        result_citation_details = result.get("citation_details", [])
        needs_web = result.get("needs_web_search", False)
        history = result.get("messages", [])

        # Build context (same logic as answer.py)
        if not slide_result.strip() or "SLIDE_NOT_ENOUGH_INFO" in slide_result:
            if web_result:
                prompt = WEB_PROMPT
                context = web_result
                result_citations = without_slide_citations(
                    result_citations
                )
            else:
                yield f"data: {json.dumps({'token': 'Rất tiếc, nội dung slide hiện tại không có đủ thông tin để trả lời câu hỏi này.'})}\n\n"
                yield f"data: {json.dumps({'done': True, 'trace_id': trace_id, 'citations': result_citations, **envelope})}\n\n"
                remember_turn(result, envelope)
                finish_trace()
                return
        else:
            prompt = SLIDE_PROMPT
            context = slide_result
            if web_result and needs_web:
                context = (
                    f"{slide_result}\n\nKết quả research:\n{web_result}"
                )

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

        # A-06 — context từ Memory (reload browser vẫn nhớ khái niệm đã hỏi)
        memory_text = ""
        if result.get("memory_context"):
            memory_text = (
                "THÔNG TIN HỌC VIÊN (từ memory):\n"
                + result["memory_context"]
                + "\n\n"
            )

        active_context = (
            (
                f'Người dùng yêu cầu focus vào paper: "{req.paper_source}".'
                if req.paper_source
                else (
                    "Research tự động tìm paper ArXiv liên quan để mở rộng "
                    "kiến thức của bài học."
                )
            )
            if is_research
            else (
                f'Học viên đang xem trang {current_page} của tài liệu '
                f'"{slide_title}".'
            )
        )
        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=f"""{history_text}{memory_text}<user_question>
{question}
</user_question>

<slide_research_result>
{context}
</slide_research_result>

<active_context>
{active_context}
</active_context>"""),
        ]

        full_text = ""
        try:
            for chunk in llm.stream(messages):
                token = (
                    chunk.content
                    if hasattr(chunk, "content")
                    else str(chunk)
                )
                if token:
                    full_text += token
                    yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception:
            result_citations = citations_used_in_answer(
                result_citations,
                full_text,
            )
            result_citation_details = citation_details_used_in_answer(
                result_citation_details,
                full_text,
            )
            if not full_text:
                yield (
                    "data: "
                    + json.dumps(
                        {
                            "error": AI_UNAVAILABLE_MESSAGE
                        }
                    )
                    + "\n\n"
                )
            yield (
                "data: "
                + json.dumps(
                    {
                        "done": True,
                        "trace_id": trace_id,
                        "citations": result_citations,
                        "citation_details": result_citation_details,
                        "full_answer": full_text,
                    }
                )
                + "\n\n"
            )
            finish_trace(answer_text=full_text, error=AI_UNAVAILABLE_MESSAGE if not full_text else None)
            return

        result_citations = citations_used_in_answer(
            result_citations,
            full_text,
        )
        result_citation_details = citation_details_used_in_answer(
            result_citation_details,
            full_text,
        )
        yield f"data: {json.dumps({'done': True, 'trace_id': trace_id, 'citations': result_citations, 'citation_details': result_citation_details, 'full_answer': full_text, **envelope}, ensure_ascii=False)}\n\n"
        remember_turn(result, envelope)
        finish_trace(answer_text=full_text)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    # uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
    uvicorn.run("server:app", host="0.0.0.0", port=8000)

