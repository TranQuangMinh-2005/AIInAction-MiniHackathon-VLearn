# VLearn — AI Thực Chiến

> Nền tảng học AI kiểu **học bằng thực chiến**: workspace 3-panel (học liệu · slide PDF · AI Tutor) với multi-agent có nguồn kiểm chứng — mọi câu trả lời đều kèm citation `[Trang X]` (slide) hoặc `[S1]` (paper arXiv, trích nguyên văn).

![Stack](https://img.shields.io/badge/FastAPI-0.141-009688) ![Stack](https://img.shields.io/badge/Next.js-16.2-Turbopack) ![Stack](https://img.shields.io/badge/LangGraph-1.2-1C3C3C) ![Tests](https://img.shields.io/badge/tests-153%20pass-15803D) ![Docker](https://img.shields.io/badge/Docker-ready-2496ED)

---

## 🚀 Quickstart — Chạy bằng Docker (nhanh nhất)

Chỉ cần **Docker** (+ Docker Compose). Không cần cài Python/Node riêng.

```bash
# 1. Clone repo
git clone https://github.com/TranQuangMinh-2005/AIInAction-MiniHackathon-VLearn.git
cd AIInAction-MiniHackathon-VLearn

# 2. Cấu hình env (điền ít nhất 1 API key thật)
cp .env.example .env

# 3. Build + chạy (lần đầu ~3-6 phút: pip + npm + build)
docker compose up -d --build
```

**Mở trình duyệt:**
- 🌐 **Web:** http://localhost:3000 → landing (**"/"**) → vào học (**"/app"**) → admin (**"/admin"**)
- 🔌 **API docs:** http://localhost:8001/docs · **health:** http://localhost:8001/api/health

```bash
# Kiểm tra nhanh
curl http://localhost:8001/api/health
# {"status":"ok","slide_pages":989,"paper_rag":{...}}
```

### ⚠️ Sau khi `up` mà web báo "Không thể kết nối AI server"

Backend đang **parse 989 trang slide lúc khởi động** (đặc biệt chậm trên máy yếu) — chờ tới khi log api hiện:

```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8001
```

rồi refresh trang. Xem log: `docker compose logs -f api`.

### Cách dừng / chạy lại

```bash
docker compose down      # dừng (giữ volume data)
docker compose up -d     # chạy lại nhanh (không rebuild)
```

---

## 🧪 Chạy local (phát triển) — không bắt buộc

```bash
# Backend (Python 3.12+)
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
PYTHONPATH=apps/api:libs/rag/src .venv/bin/python -m uvicorn server:app --app-dir apps/api --port 8001

# Frontend (Node 22+)
cd apps/web && npm ci && npm run dev   # http://localhost:3000

# Test + build
PYTHONPATH=apps/api:libs/rag/src .venv/bin/python -m pytest apps/api/tests libs/rag/tests   # 153 test, offline
cd apps/web && npm run build
```

> Mẹo: `make` có sẵn các mục `install/test/dev-api/dev-web/build`.

---

## 📁 Cấu trúc thư mục

Monorepo production: `apps/*` (ứng dụng), `libs/*` (thư viện dùng chung), `evals/` (kiểm chứng chất lượng), `docs/` (tài liệu), `render.yaml` (blueprint Render).

```
vlearn/
├── apps/
│   ├── api/                    # FastAPI backend (Python)
│   │   ├── server.py           #   app entry: /api/chat, /api/chat/stream (SSE), /api/papers, /api/learners, /api/feedback, /api/admin/metrics, /api/health
│   │   ├── agent/              #   LangGraph multi-agent (A-01 → A-11)
│   │   │   ├── graph.py        #     graph thống nhất: orchestrator → experts → tutor_coach
│   │   │   ├── nodes/          #     orchestrator · slide_search · web_search · answer · summary · examples · tutor_coach
│   │   │   ├── tools/          #     paper/ (arXiv) · research (cache + web) · web_search (Tavily/DDG)
│   │   │   ├── memory/         #     A-06: hồ sơ phiên học anonymous per-browser (JSON/learner) + notes
│   │   │   ├── observability/  #     A-07: trace mỗi turn (latency/tokens/cost) + feedback JSONL + metrics
│   │   │   ├── analytics/      #     A-10: gaps (top khái niệm cần ôn)
│   │   │   ├── rag.py          #     slide retrieval: doc-first + corpus fallback + multi-query + hybrid tùy chọn
│   │   │   └── security.py     #     validate input (injection/jailbreak/harmful, EN+VI)
│   │   └── tests/              # pytest (offline, autouse fixtures — ít nhất 1 key giả để collection)
│   └── web/                    # Next.js 16 + Tailwind v4 (landing + 3-panel + /admin)
│       └── src/
│           ├── app/            #   routing only: "/" landing · "/app" workspace · "/admin" dashboard
│           └── components/     #   Sidebar · SlideViewer · PDFViewer · ChatPanel · Reveal
├── libs/
│   └── rag/                    # Paper RAG library (local_rag) — hybrid dense+BM25+MMR + grounding audit
│       ├── src/local_rag/      #   retrieval · chunking · grounding · service · store (SQLite)
│       └── tests/
├── evals/eval/                 # gate_run.py — golden set 20 case tool-routing vlearn-ux (DRY/REAL)
├── docs/                       # DESIGN.md · AGENT-UPGRADE-PLAN.md · MVP_RUN.md · IMPROVEMENT-ROADMAP.md …
├── validation/                 # driver kết quả nghiệm thu (A-05/A-06/A-07 + gate)
├── .env.example · docker-compose.yml · Dockerfile (multi-stage) · docker-entrypoint.sh
├── Makefile · pyproject.toml · requirements.txt
├── render.yaml                 # Render Blueprint (2 service + persistent disk)
└── .github/workflows/ci.yml    # CI: pytest + web build + gate DRY (chặn merge)
```

## 🏗️ Kiến trúc

```
┌─ apps/web (Next.js) ───────────────┐   ┌─ apps/api (FastAPI) ────────────────────────────────┐
│  Landing "/" · Workspace "/app"     │   │                                                    │
│  └─ POST /api/chat/stream (SSE) ────┼──►│ /api/chat · /api/chat/stream · /api/papers · ...  │
│     status events từng phase         │   │                                                    │
└──────────────┬───────────────────────┘   │  LangGraph · Orchestrator Router (A-01)            │
               │                            │   ├─ slide intent → Slide Scholar (17 doc/989 trang)│
        proxy /api/* hoặc absolute URL     │   ├─ research    → Research Scholar (A-08:        │
               │                            │   │                 arXiv cache · Tavily fallback) │
┌─ libs/rag (local_rag) ──────────────┐   │   ├─ summary     → Summary Agent (map-reduce + cache,│
│ hybrid dense+BM25+MMR · grounding    │◄──┼───┤                 page-scope "trang này")          │
│ audit claim→quote · SQLite store     │   │   ├─ example     → Example Teacher (ví dụ thật +    │
│ slide RAG: BM25 + optional hybrid    │   │   │                 câu hỏi ôn tập)                  │
└──────────────────────────────────────┘   │   └─ mọi turn    → Tutor Coach (envelope:          │
                                           │                     move · misconceptions · follow_ups)│
                                           │   ├─ Memory per-browser (A-06) · Notes · Trace (A-07)│
                                           │   └─ Analytics gaps (A-10) · /admin metrics         │
                                           └────────────────────────────────────────────────────┘
```

## 🔌 API

| Endpoint | Mô tả |
|---|---|
| `POST /api/chat` | Trả lời đồng bộ (answer + citations + citation_details + envelope `move/misconceptions/follow_ups/asked_check_question` + `trace_id`) |
| `POST /api/chat/stream` | SSE: `{"status": phase, "elapsed_ms"}` theo từng bước + token + `done` (kèm envelope + trace_id) |
| `GET /api/papers` · `POST /api/papers/import-arxiv` · `POST /api/papers/ask` · `GET /api/papers/{source}/pdf` | Paper RAG + phục vụ PDF paper (citation nhảy trang) |
| `GET/PUT /api/learners/{id}/state` · `GET/PUT /api/learners/{id}/notes` · `GET /api/learners/{id}/gaps` | Memory anonymous + ghi chú + analytics |
| `POST /api/feedback` | Rating 👍(1)/👎(-1) gắn `trace_id` |
| `GET /api/admin/metrics?window=1h\|24h\|7d` | Dashboard cost/latency từ trace (UI tại `/admin`) |
| `GET /api/health` | slide_pages + paper_rag status |

SSE event lạ / field optional đều backward-compatible.

## ⚙️ Cấu hình env

Copy `.env.example` → `.env` (gốc repo). **Bắt buộc:** 1 trong 2 key chat provider + model.

| Biến | Bắt buộc | Ghi chú |
|---|---|---|
| `OPENAI_API_KEY` | 1 trong 2 | Provider khuyến nghị kèm `RAG_PROVIDER=openai` |
| `GEMINI_API_KEY` / `GOOGLE_API_KEY` | 1 trong 2 | Provider Gemini (thay `RAG_PROVIDER` = `gemini`) |
| `RAG_PROVIDER` | ✓ | `openai` hoặc `gemini` (mặc định auto theo key) |
| `RAG_CHAT_MODEL` | ✓ | `gpt-4o-mini` (openai) / `gemini-3.6-flash` (gemini) |
| `RAG_EMBEDDING_MODEL` | ✓ | `text-embedding-3-large` / `gemini-embedding-2` |
| `TAVILY_API_KEY` | tùy chọn | Web search khi arXiv không đủ |
| `SLIDE_MULTI_QUERY` | mặc định `1` | Multi-query cho slide retrieval |
| `SLIDE_HYBRID` | mặc định `0` | Hybrid dense+BM25 cho slide (`1` cần embedding API) |
| `NEXT_PUBLIC_AGENT_API_URL` | tùy chọn | Để trống = relative `/api/*` (proxy 1-container); set URL khi tách web/backend |
| `CORS_ORIGINS` | tùy chọn | Comma-separated origin bổ sung (VD: domain Vercel) |

> ℹ️ **Đổi provider/model embedding → chạy lại `paper-rag ingest --reset`** (vector 2 provider không tương thích). Paper tự tải từ arXiv sẽ được index tự động khi research.

## 🧪 Test & Eval

```bash
# Unit/integration (offline — không cần key thật)
PYTHONPATH=apps/api:libs/rag/src .venv/bin/python -m pytest apps/api/tests libs/rag/tests   # 153 pass

# Golden set tool-routing (20 case vlearn-ux) — DRY không cần key / REAL cần backend + key
python3 evals/eval/gate_run.py --dry
python3 evals/eval/gate_run.py --real --api http://localhost:8001
```

Mọi thay đổi agent phải giữ: **pytest PASS + Next build PASS + gate không giảm** (CI `.github/workflows/ci.yml` tự chặn merge).

## 🚢 Deploy

| Nền tảng | Cách |
|---|---|
| **Docker compose (local/demo)** | `docker compose up -d --build` — api `:8001` + web `:3000` |
| **Render** | Blueprint `render.yaml` (2 service + persistent disk `/var/lib/vlearn-data`) — chi tiết mục dưới |
| **Vercel (web) + HF Spaces (api)** | Web: root `apps/web`, env `NEXT_PUBLIC_AGENT_API_URL=https://<space>.hf.space`; API: Space Docker (entrypoint tự nhận `VLEARN_HF=1`/`PORT=7860`, data tại `/data`) |

### Render (Blueprint)

```bash
cp .env.example .env   # điền key thật
```
- Push repo (có `render.yaml`) → Render → **New + → Blueprint** → chọn repo → tạo.
- Điền secrets (`OPENAI_API_KEY`, `TAVILY_API_KEY`) + `CORS_ORIGINS` = URL web → Redeploy.
- ⚠️ **Persistent disk chỉ có ở gói trả phí** (`plan: starter`) — free thì index paper/memory reset mỗi deploy (slide + landing luôn ổn — nằm trong image).
- Dữ liệu local trỏ mount qua env: `RAG_INDEX_PATH` / `RAG_PDF_DIR` / `VLEARN_MEMORY_DIR` / `VLEARN_OBS_DIR` (code + `docker-entrypoint.sh` đã hỗ trợ).

## 🧭 Quyết định kiến trúc (đọc trước khi đụng code)

- **Không phá API contract cũ** — mọi cải tiến thêm field optional, SSE event lạ bị bỏ qua (`docs/AGENT-UPGRADE-PLAN.md` §1.4 non-goals).
- **Orchestrator 1 lần, không agent-free-loop** — LangGraph có cấu trúc, mỗi expert là node/subgraph có contract rõ (A-01).
- **Memory anonymous per-browser** — learner_id do client sinh (localStorage), không PII; login sau = thêm layer (A-06).
- **Retrieval có nguồn kiểm chứng** — slide cite `[D? - Trang N]`, paper cite `[S1]` trang/dòng/quote (grounding audit claim→quote exact).
- **Giới hạn tool-routing**: golden set 24 case gốc thuộc sản phẩm cũ — đọc `validation/A-07-Gate-analysis.md`; golden mới 20 case vlearn-ux tại `evals/eval/golden_vlearn_ux.json`.

## 🗺️ Roadmap

- ✅ **P1** — Orchestrator (A-01) · slide retrieval nâng cấp (A-02) · Summary + page-scope (A-03) · SSE status thật (A-04)
- ✅ **P2** — Tutor Coach + envelope (A-05) · Memory + Notes (A-06) · Eval/trace/feedback/metrics (A-07) · Research cache + Tavily (A-08)
- ✅ **P3** — Example Teacher (ví dụ + câu hỏi ôn tập) · OCR day03 (A-11) · Analytics + admin (A-10)
- ⏳ **Sau** — observability nâng cao (Langfuse/OTel) · rate-limit/audit (OWASP ASI) · model routing 2 tầng · CI gate REAL (xem `docs/IMPROVEMENT-ROADMAP.md`)

Chi tiết từng mục + changelog: `docs/AGENT-UPGRADE-PLAN.md`.

## 👥 Đội ngũ dự án (Hackathon)

| STT | Họ và tên            | Mã học viên | Vai trò trong nhóm (Đã tối giản)  | Đóng góp (% công việc) |
| --- | -------------------- | ----------- | --------------------------------- | ---------------------- |
| 1   | Nguyễn Hoàng Anh     | 01186       | Làm tool & Frontend               | 20%                    |
| 2   | Trần Quang Minh      | 01210       | Tạo Ai Agent                      | 20%                    |
| 3   | Ngô Văn Nam          | 01340       | Kiểm tra benchmark                | 20%                    |
| 4   | Phạm Khắc Khương Duy | 01982       | Testcase và tổng hợp tài liệu     | 20%                    |
| 5   | Đào Kiều Thịnh Quang | 01014       | Tạo RAG                           | 20%                    |

## 📚 Tài liệu liên quan

`docs/DESIGN.md` (design system) · `docs/AGENT-UPGRADE-PLAN.md` (kế hoạch + CHANGELOG) · `docs/MVP_RUN.md` (demo 5 phút) · `docs/IMPROVEMENT-ROADMAP.md` (backlog nghiên cứu) · `docs/P2-ACCEPTANCE.md` · `validation/` (driver kết quả).