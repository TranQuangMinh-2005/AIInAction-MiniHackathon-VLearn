# VLearn — AI Thực Chiến

> Nền tảng học AI kiểu **học bằng thực chiến**: workspace 3-panel (học liệu · slide PDF · AI Tutor) với multi-agent có nguồn kiểm chứng — mọi câu trả lời đều kèm citation `[Trang X]` (slide) hoặc `[S1]` (paper arXiv, trích nguyên văn).

![Stack](https://img.shields.io/badge/FastAPI-0.141-009688) ![Stack](https://img.shields.io/badge/Next.js-16.2-Turbopack) ![Stack](https://img.shields.io/badge/LangGraph-1.2-1C3C3C) ![Tests](https://img.shields.io/badge/tests-115%20pass-15803D)

---

## Quickstart (3 bước)

```bash
# 1. Cài backend (Python 3.12+)
pip install -r requirements.txt

# 2. Cài frontend
cd apps/web && npm ci && cd ../..

# 3. Chạy
make dev-api     # FastAPI tại http://localhost:8000 (docs: /docs)
make dev-web     # Next.js tại http://localhost:3000 → mở "/" (landing) rồi "/app"
```

Key API bắt buộc trong `.env` (xem [Cấu hình env](#-cấu-hình-env)): `GEMINI_API_KEY` hoặc `OPENAI_API_KEY` + `RAG_CHAT_MODEL` + `RAG_EMBEDDING_MODEL` (+ `TAVILY_API_KEY` cho web search).

---

## Cấu trúc thư mục

Monorepo production: `apps/*` (ứng dụng), `libs/*` (thư viện dùng chung), `evals/` (kiểm chứng chất lượng), tài liệu ở gốc repo.

```
vlearn/
├── apps/
│   ├── api/                    # FastAPI backend (Python)
│   │   ├── server.py           #   app entry: /api/chat, /api/chat/stream (SSE), /api/papers, /api/learners, /api/feedback, /api/health
│   │   ├── agent/              #   LangGraph multi-agent (A-01 → A-08)
│   │   │   ├── graph.py        #     graph thống nhất: orchestrator → experts → tutor_coach
│   │   │   ├── state.py        #     AgentState (TypedDict, backward-compatible)
│   │   │   ├── nodes/          #     orchestrator · slide_search · web_search · answer · summary · tutor_coach
│   │   │   ├── tools/          #     paper/ (arXiv) · research (cache + web) · web_search (Tavily/DDG)
│   │   │   ├── memory/         #     A-06: hồ sơ phiên học anonymous per-browser (JSON/learner)
│   │   │   ├── observability/  #     A-07: trace mỗi turn (latency/tokens/cost) + feedback JSONL
│   │   │   ├── rag.py          #     slide retrieval: doc-first + corpus fallback + multi-query + hybrid tùy chọn
│   │   │   ├── security.py     #     validate input (injection/jailbreak/harmful, EN+VI)
│   │   │   ├── providers.py    #     Gemini/OpenAI adapter + embedding
│   │   │   └── config.py       #     paths + env loading
│   │   └── tests/              # 90 pytest (offline, autouse fixtures)
│   └── web/                    # Next.js 16 + Tailwind v4 (3-panel + landing)
│       └── src/
│           ├── app/            #   routing only: "/" = landing · "/app" = workspace
│           └── components/     #   Sidebar · SlideViewer · PDFViewer · ChatPanel · Reveal
├── libs/
│   └── rag/                    # Paper RAG library (local_rag) — hybrid dense+BM25+MMR + grounding audit
│       ├── src/local_rag/      # retrieval · chunking · grounding · service · store (SQLite)
│       └── tests/              # 25 pytest
├── evals/
│   └── eval/                   # gate_run.py — golden set 24 case tool-routing (DRY/REAL)
├── data/                       # tooling scripts (vlearn-pack)
├── validation/                 # driver kết quả nghiệm thu (A-05/A-06/A-07)
├── .env.example                # template biến môi trường
├── docker-compose.yml          # api (:8001) + web (:3000)
├── Makefile                    # install/test/dev-api/dev-web/build
├── pyproject.toml              # metadata + pytest config
└── requirements.txt
```

## Kiến trúc

```
┌─ apps/web (Next.js) ───────────────┐   ┌─ apps/api (FastAPI) ────────────────────────────────┐
│  Landing "/"  ·  Workspace "/app"   │   │                                                    │
│  └─ POST /api/chat/stream (SSE) ────┼──►│ /api/chat · /api/chat/stream · /api/papers · ...  │
│     status events từng phase         │   │                                                    │
└──────────────────────────────────────┘   │  LangGraph · Orchestrator Router (A-01)            │
                                          │   ├─ slide intent  → Slide Scholar (17 doc/926 trang)│
─ libs/rag (local_rag) ────────────────┐  │   ├─ research      → Research Scholar (A-08:        │
│ hybrid dense+BM25+MMR · grounding    │◄─┼──┤   arXiv cache · Tavily fallback)                 │
│ audit claim→quote · SQLite store    │  │   ├─ summary       → Summary Agent (map-reduce+cache)│
│ slide RAG: BM25 offline + optional  │  │   └─ mọi turn      → Tutor Coach (envelope:          │
│ hybrid (SLIDE_HYBRID=1)             │  │      move · misconceptions · follow_ups · check hiểu)│
└──────────────────────────────────────┘  │   └─ Memory (per-browser anonymous) · Trace + Eval  │
                                          └────────────────────────────────────────────────────┘
```

## API

| Endpoint | Mô tả |
|---|---|
| `POST /api/chat` | Trả lời đồng bộ (answer + citations + envelope `move/misconceptions/follow_ups/asked_check_question` + `trace`) |
| `POST /api/chat/stream` | SSE: `{"status": phase, "elapsed_ms"}` theo từng bước + token + `done` (kèm envelope + trace_id) |
| `GET /api/papers` · `POST /api/papers/import-arxiv` · `POST /api/papers/ask` | Paper RAG |
| `GET/PUT /api/learners/{id}/state` | Memory anonymous (A-06) |
| `POST /api/feedback` | Rating 👍(1)/👎(-1) gắn `trace_id` |
| `GET /api/health` | slide_pages + paper_rag status |

SSE event lạ sẽ bị frontend cũ bỏ qua (backward-compatible); envelope/trace là field optional.

## Cấu hình env

Copy `.env.example` → `.env` (gốc repo; backend còn đọc `apps/api/.env` và `libs/rag/.env` theo thứ tự, không đè nhau). Biến chính:

| Biến | Bắt buộc | Ghi chú |
|---|---|---|
| `GEMINI_API_KEY` | 1 trong 2 | Provider mặc định (Gemini flash-lite + fallback chain) |
| `OPENAI_API_KEY` | 1 trong 2 | Bật khi `RAG_PROVIDER=openai` + `RAG_CHAT_MODEL=gpt-4o-mini` |
| `RAG_CHAT_MODEL` / `RAG_EMBEDDING_MODEL` | ✓ | Model chat + embedding cho paper RAG |
| `TAVILY_API_KEY` | tùy chọn | Web search fallback khi arXiv không có paper |
| `SLIDE_MULTI_QUERY` | mặc định `1` | Multi-query expansion cho slide retrieval (LLM, fail → deterministic) |
| `SLIDE_HYBRID` | mặc định `0` | Hybrid dense+BM25 cho slide (embedding; lỗi → fallback BM25) |
| `NEXT_PUBLIC_AGENT_API_URL` | mặc định `http://localhost:8000` | Frontend → backend URL (`apps/web/.env.local`) |

## Test

```bash
make test                 # 90 (apps/api) + 25 (libs/rag) pytest, offline
make build                # Next.js production build
python3 evals/eval/gate_run.py --dry                # parse golden 24 case (không cần key)
python3 evals/eval/gate_run.py --real --api http://localhost:8001   # tool-match thật
```

Mọi thay đổi agent phải giữ: 115 pytest PASS + Next build PASS + golden gate không giảm (hoặc có giải trình).

## Deploy

```bash
cp .env.example .env       # điền key thật
docker compose up --build  # api :8001 + web :3000
```

Container đơn (Dockerfile): `start.sh` chạy backend (`PYTHONPATH=apps/api:libs/rag/src`) + frontend (`npm run start`).

## Deploy lên Render (Blueprint)

Đã chuẩn bị sẵn `render.yaml` (2 Web Service: `vlearn-api` + `vlearn-web`, Docker multi-stage, persistent disk).

**Các bước:**
1. Push code có `render.yaml` lên GitHub (branch `main`).
2. Render Dashboard → **New + → Blueprint** → chọn repo → tạo.
3. Điền **OpenAI/Tavily key** vào Secrets của `vlearn-api`, set `NEXT_PUBLIC_AGENT_API_URL` = URL api thật (vd `https://vlearn-api.onrender.com`) + thêm origin đó vào `CORS_ORIGINS` → **Redeploy**.
4. Mở `https://<vlearn-web>.onrender.com` — landing + `/app` + `/admin`.

⚠️ **Persistent disk chỉ có ở gói trả phí** (`plan: starter` cho api) — không có disk thì index paper/memory sẽ reset mỗi lần deploy (slide vẫn OK). Dữ liệu local (RAG SQLite, papers PDF, memory/traces JSONL) trỏ về mount `/var/lib/vlearn-data` qua env `RAG_INDEX_PATH` / `RAG_PDF_DIR` / `VLEARN_MEMORY_DIR` / `VLEARN_OBS_DIR` (code đã hỗ trợ env này).

## Quyết định kiến trúc (đọc trước khi đụng code)

- **Không phá API contract cũ** — mọi cải tiến thêm field optional, SSE event lạ bị bỏ qua (docs/AGENT-UPGRADE-PLAN.md §1.4 non-goals).
- **Orchestrator 1 lần, không agent-free-loop** — LangGraph có cấu trúc, mỗi expert là node/subgraph có contract rõ (A-01).
- **Memory anonymous per-browser** — learner_id do client sinh (localStorage), không PII; migration login sau = thêm cột (A-06).
- **Giới hạn tool-routing**: golden set 24 case gốc thuộc sản phẩm cũ (social/timeline/policy…) — đọc `validation/A-07-Gate-analysis.md` trước khi đánh giá gate.

## Roadmap

- ✅ P1 — nền móng: Orchestrator (A-01) · slide retrieval nâng cấp (A-02) · Summary (A-03) · SSE status thật (A-04)
- ✅ P2 — đa-agent: Tutor Coach + envelope (A-05) · Memory (A-06) · Eval & trace + feedback (A-07) · Research cache + Tavily (A-08)
- ⏳ P2 còn lại / P3: OCR day03 (A-11) · gợi ý ôn tập (A-10) · logistics KB (A-09, đã bỏ theo user)

Chi tiết từng mục + changelog theo bước triển khai: `docs/AGENT-UPGRADE-PLAN.md`.

## Đội ngũ dự án (Hackathon)

| STT | Họ và tên            | Mã học viên | Vai trò trong nhóm (Đã tối giản)  | Đóng góp (% công việc) |
| --- | -------------------- | ----------- | --------------------------------- | ---------------------- |
| 1   | Nguyễn Hoàng Anh     | 01186       | Làm tool & Frontend               | 20%                    |
| 2   | Trần Quang Minh      | 01210       | Tạo Ai Agent                      | 20%                    |
| 3   | Ngô Văn Nam          | 01340       | Kiểm tra benchmark                | 20%                    |
| 4   | Phạm Khắc Khương Duy | 01982       | Testcase và tổng hợp tài liệu     | 20%                    |
| 5   | Đào Kiều Thịnh Quang | 01014       | Tạo RAG                           | 20%                    |

## Tài liệu liên quan

`docs/DESIGN.md` (design system + landing §10) · `docs/AGENT-UPGRADE-PLAN.md` (kế hoạch 11 cải tiến + CHANGELOG) · `docs/P2-ACCEPTANCE.md` (tiêu chí nghiệm thu P2) · `validation/` (driver kết quả) · `docs/MVP_RUN.md` (hướng dẫn chạy MVP).