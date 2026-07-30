"""
VLearn Agent API Server.
Chạy lệnh: python server.py
"""

import json
import re
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from agent.graph import build_graph, AgentState
from agent.rag import slide_index
from agent.security import validate_input
from agent.llm import llm
from langchain_core.messages import SystemMessage, HumanMessage
from local_rag.agent_tool import ask_research_papers
from local_rag.service import RAGService
from agent.tools.paper.paper import arxiv_download_pdf, arxiv_search

app = FastAPI(title="VLearn Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def citations_used_in_answer(
    citations: list[str],
    answer: str,
) -> list[str]:
    used: list[str] = []
    unlabeled: list[str] = []
    for citation in citations:
        labels = re.findall(r"\[([^\]]+)\]", citation)
        if not labels:
            unlabeled.append(citation)
            continue
        if any(f"[{label}]" in answer for label in labels):
            used.append(citation)
    return unlabeled + used


def citation_details_used_in_answer(
    details: list[dict],
    answer: str,
) -> list[dict]:
    return [
        detail
        for detail in details
        if f"[{detail.get('label', '')}]" in answer
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
        matches = arxiv_search(query, max_results=1)
        if not matches:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy paper phù hợp trên arXiv.",
            )
        paper = matches[0]
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

@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
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
    if is_research:
        # Research has its own fast router; do not spend an embedding + LLM
        # decision on slides before looking at the selected paper/arXiv.
        slide_context, citations = "", []
    else:
        slide_context, rag_citations = slide_index.retrieve_context(
            req.question,
            doc_id=req.active_doc_id,
            k=3,
        )
        citations = rag_citations[:1] if rag_citations else []

    slide_title = (
        "Day 1 — AI & LLM Foundation" if req.active_doc_id == "d1"
        else "Day 2 — Xác định bài toán cho AI"
    )

    initial_state: AgentState = {
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
    }

    if is_research:
        from agent.nodes.answer import generate_answer
        from agent.nodes.web_search import search_online

        result = search_online(initial_state)
        if result.get("citations"):
            result = generate_answer(result)
        else:
            result = {
                **result,
                "final_answer": result.get(
                    "web_search_result",
                    "Không tìm thấy paper phù hợp trên arXiv.",
                ),
            }
    else:
        result = build_graph().invoke(initial_state)
    answer = result.get("final_answer", "Không thể tạo câu trả lời.")
    return ChatResponse(
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
    if is_research:
        slide_context, citations = "", []
    else:
        slide_context, rag_citations = slide_index.retrieve_context(
            req.question,
            doc_id=req.active_doc_id,
            k=3,
        )
        citations = rag_citations[:1] if rag_citations else []

    slide_title = (
        "Day 1 — AI & LLM Foundation" if req.active_doc_id == "d1"
        else "Day 2 — Xác định bài toán cho AI"
    )

    initial_state_stream: AgentState = {
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
    }

    async def event_stream():
        from agent.nodes.slide_search import search_slide, decide_search
        from agent.nodes.web_search import search_online
        from agent.nodes.answer import (
            SYSTEM_PROMPT as SLIDE_PROMPT,
            SYSTEM_PROMPT_WEB as WEB_PROMPT,
            without_slide_citations,
        )

        # Research mode skips two LLM calls (slide answer + routing).
        if is_research:
            result = search_online(initial_state_stream)
            if not result.get("citations"):
                message = result.get(
                    "web_search_result",
                    "Không tìm thấy paper phù hợp trên arXiv.",
                )
                yield f"data: {json.dumps({'token': message})}\n\n"
                yield (
                    "data: "
                    + json.dumps(
                        {
                            "done": True,
                            "citations": [],
                            "citation_details": [],
                        }
                    )
                    + "\n\n"
                )
                return
        else:
            result = search_slide(initial_state_stream)
            result = decide_search(result)
        if result.get("needs_web_search") and not is_research:
            result = search_online(result)

        # Stream final answer
        question = result["user_question"]
        slide_result = result.get("slide_search_result", "")
        web_result = result.get("web_search_result", "")
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
                yield f"data: {json.dumps({'done': True, 'citations': result_citations})}\n\n"
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

        active_context = (
            f'Paper duy nhất được phép dùng: "{req.paper_source}".'
            if is_research
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
                            "error": (
                                "Gemini đang chạm giới hạn tạm thời. "
                                "Vui lòng thử lại sau vài giây."
                            )
                        }
                    )
                    + "\n\n"
                )
            yield (
                "data: "
                + json.dumps(
                    {
                        "done": True,
                        "citations": result_citations,
                        "citation_details": result_citation_details,
                        "full_answer": full_text,
                    }
                )
                + "\n\n"
            )
            return

        result_citations = citations_used_in_answer(
            result_citations,
            full_text,
        )
        result_citation_details = citation_details_used_in_answer(
            result_citation_details,
            full_text,
        )
        yield f"data: {json.dumps({'done': True, 'citations': result_citations, 'citation_details': result_citation_details, 'full_answer': full_text})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
