"""
VLearn Agent API Server.
Chạy lệnh: python server.py
"""

import json
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from agent.graph import build_graph, AgentState
from agent.rag import slide_index
from agent.security import validate_input
from agent.llm import llm
from langchain_core.messages import SystemMessage, HumanMessage

app = FastAPI(title="VLearn Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    slide_index.load()

class ChatRequest(BaseModel):
    question: str
    active_doc_id: str
    current_page: int
    history: list[dict] = []
    mode: str = "normal"

class ChatResponse(BaseModel):
    answer: str
    citations: list[str]
    current_page: int
    slide_title: str

@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    is_safe, reason = validate_input(req.question)
    if not is_safe:
        return ChatResponse(
            answer=f"⚠️ {reason}",
            citations=[],
            current_page=req.current_page,
            slide_title="",
        )

    slide_context, rag_citations = slide_index.retrieve_context(req.question, doc_id=req.active_doc_id, k=3)
    citations = rag_citations[:1] if rag_citations else []

    slide_title = (
        "Day 1 — AI & LLM Foundation" if req.active_doc_id == "d1"
        else "Day 2 — Xác định bài toán cho AI"
    )

    graph = build_graph()
    initial_state: AgentState = {
        "user_question": req.question,
        "slide_context": slide_context,
        "current_page": req.current_page,
        "slide_title": slide_title,
        "messages": req.history,
        "slide_search_result": None,
        "web_search_result": None,
        "final_answer": None,
        "citations": citations,
        "needs_web_search": False,
        "error": None,
        "mode": req.mode,
    }

    result = graph.invoke(initial_state)
    return ChatResponse(
        answer=result.get("final_answer", "Không thể tạo câu trả lời."),
        citations=result.get("citations", citations),
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

    slide_context, rag_citations = slide_index.retrieve_context(req.question, doc_id=req.active_doc_id, k=3)
    citations = rag_citations[:1] if rag_citations else []

    slide_title = (
        "Day 1 — AI & LLM Foundation" if req.active_doc_id == "d1"
        else "Day 2 — Xác định bài toán cho AI"
    )

    graph = build_graph()
    initial_state_stream: AgentState = {
        "user_question": req.question,
        "slide_context": slide_context,
        "current_page": req.current_page,
        "slide_title": slide_title,
        "messages": req.history,
        "slide_search_result": None,
        "web_search_result": None,
        "final_answer": None,
        "citations": citations,
        "needs_web_search": False,
        "error": None,
        "mode": req.mode,
    }

    async def event_stream():
        from agent.nodes.slide_search import search_slide, decide_search
        from agent.nodes.web_search import search_online
        from agent.nodes.answer import SYSTEM_PROMPT as SLIDE_PROMPT, SYSTEM_PROMPT_WEB as WEB_PROMPT

        # Run non-streaming nodes
        result = search_slide(initial_state_stream)
        result = decide_search(result)

        if result.get("needs_web_search"):
            result = search_online(result)

        # Stream final answer
        question = result["user_question"]
        slide_result = result.get("slide_search_result", "")
        web_result = result.get("web_search_result", "")
        current_page = result.get("current_page", 1)
        slide_title = result.get("slide_title", "")
        result_citations = result.get("citations", [])
        needs_web = result.get("needs_web_search", False)
        history = result.get("messages", [])

        # Build context (same logic as answer.py)
        if not slide_result.strip() or "SLIDE_NOT_ENOUGH_INFO" in slide_result:
            if web_result:
                prompt = WEB_PROMPT
                context = web_result
                result_citations = result_citations + ["Web search"]
            else:
                yield f"data: {json.dumps({'token': 'Rất tiếc, nội dung slide hiện tại không có đủ thông tin để trả lời câu hỏi này.'})}\n\n"
                yield f"data: {json.dumps({'done': True, 'citations': result_citations})}\n\n"
                return
        else:
            prompt = SLIDE_PROMPT
            context = slide_result
            if web_result and needs_web:
                context = f"{slide_result}\n\nKết quả research thêm từ web:\n{web_result}"
                result_citations = result_citations + ["Web search"]

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

        full_text = ""
        for chunk in llm.stream(messages):
            token = chunk.content if hasattr(chunk, "content") else str(chunk)
            if token:
                full_text += token
                yield f"data: {json.dumps({'token': token})}\n\n"

        yield f"data: {json.dumps({'done': True, 'citations': result_citations, 'full_answer': full_text})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
