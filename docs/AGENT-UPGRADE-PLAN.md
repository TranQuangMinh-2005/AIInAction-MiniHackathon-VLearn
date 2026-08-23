# AGENT-UPGRADE-PLAN — VLearn Tutor: từ 1 agent → hệ multi-agent học tập

> **Tác giả:** Arch2 (Solution Architect, vlearn-ux-team) · **Trạng thái:** ⏳ CHỜ USER DUYỆT TỪNG MỤC · **Version:** v1
> **Phạm vi:** Chỉ kế hoạch + docs. KHÔNG sửa code trong đợt này.
> **Cách dùng:** User đọc nhanh và tick `☐ CHỜ DUYỆT` cho từng mục A-01…A-11 (mỗi mục ≤30 giây đọc). Chỉ những mục được tick mới đưa vào backlog. PO tổng hợp quyết định và giao việc cho Dev.

---

## 0. Tóm tắt 30 giây (dành cho user)

Hệ thống hiện tại là **1 agent tuần tự** (4 bước nối tiếp) + RAG slide (BM25) + RAG paper (hybrid + grounding audit). Số liệu thật từ chatlog: **30.5% câu hỏi thất bại, 52.8% học viên bỏ sau 1 turn, 0 lần phát hiện hiểu lầm, 0 lần gợi ý câu hỏi tiếp**.

Kế hoạch đề xuất chuyển sang **hệ multi-agent 7 vai trò** (Orchestrator + 6 chuyên gia) — chia thành **11 cải tiến nhỏ** theo 3 phase **P1 (nền móng) → P2 (học tập) → P3 (mở rộng)**, mỗi mục độc lập, không phá luồng Normal/Research hiện có, giữ nguyên toàn bộ API contract và UI 3-panel đã chốt.

---

## 1. Hiện trạng hệ thống (đã đọc code thật — không đoán)

### 1.1 Sơ đồ luồng hiện tại (as-is)

```
┌──────────── FRONTEND (Next.js, 3-panel, đã redesign theo DESIGN.md) ────────────┐
│ ChatPanel.tsx (867 dòng) · SlideViewer · Sidebar · slideDocs.ts (17 tài liệu)   │
│   └─ POST /api/chat/stream (SSE)  ·  POST /api/papers/import-arxiv              │
└────────────────────────────────────┬────────────────────────────────────────────┘
                                     ▼
┌────────────────────── FastAPI server.py (516 dòng) ────────────────────────────┐
│ validate_input (security.py — regex EN+VI)                                       │
│         │                                                                        │
│   ┌─────┴────── 2 nhánh cứng theo mode ──────┐                                   │
│   ▼ (mode=normal)                             ▼ (mode=research)                  │
│   build_graph() — LangGraph 4 node             search_online() GỌI THẲNG         │
│   ┌─────────────────────────────┐             (BYPASS graph — code trùng)        │
│   │ search_slide ──► decide_    │            ┌──────────────────────────────┐    │
│   │      search ──► (cần web?)  │            │ 1. LLM rewrite → query arXiv  │    │
│   │      ├─► web_search ──────┐ │            │ 2. arxiv_search (rate-limit   │    │
│   │      └─► generate_answer ◄┘ │            │    3s + fallback DuckDuckGo)  │    │
│   └─────────────────────────────┘            │ 3. LLM rerank chọn 1 paper    │    │
│            ▼                                 │ 4. download PDF → local RAG   │    │
│   trả answer + citations                      │ 5. hybrid retrieve (dense+BM25│    │
│   (citation_details khi Research)             │    +MMR) → grounding audit   │    │
│                                               │ 6. generate_answer            │    │
│                                               └──────────────────────────────┘    │
└───────────────────────────────────────────────────────────────────────────────────┘

Hạ tầng: agent/rag.py (slide BM25, 17 doc / 926 trang, KHÔNG embedding)
        codebase/rag/src/local_rag/ (paper: SQLite store, chunking 360 từ,
        hybrid retrieval, grounding audit claim→quote, provider Gemini/OpenAI)
        llm.py = GeminiChat (gemini-3.x flash-lite mặc định + fallback chain, temp 0.1)
```

### 1.2 Ánh xạ code → vai trò (kiểm chứng khi đọc)

| Thành phần | File | Vai trò thực tế |
|---|---|---|
| FastAPI endpoints | `src/agent/server.py` | `/api/chat`, `/api/chat/stream` (SSE), `/api/papers`, `/api/papers/import-arxiv`, `/api/papers/ask`, `/api/health` |
| Sơ đồ LangGraph | `src/agent/agent/graph.py` | 4 node: `search_slide → decide_search → (web_search?) → generate_answer` — **chỉ chạy khi mode=normal** |
| Rẽ nhánh research | `server.py:263-277, 354-379` | Research mode **gọi thẳng `search_online()` ngoài graph** — luồng trùng lặp, khó mở rộng |
| Slide retrieval | `src/agent/agent/rag.py` | **BM25 thuần** (chủ ý chọn offline/deterministic), `retrieve_context` k=3 (normal) / k=2 (research) |
| Paper RAG | `codebase/rag/src/local_rag/` | Hybrid dense(0.76)+BM25+MMR(0.78), chunk 360 từ, store SQLite, **grounding audit claim→quote chính xác** |
| Security | `src/agent/agent/security.py` | Regex chặn injection/jailbreak/harmful (EN+VI), giới hạn 2000 ký tự |
| LLM | `src/agent/agent/providers.py` | Gemini mặc định + fallback `gemini-3.1-flash-lite, gemini-2.5-flash-lite`; OpenAI nếu cấu hình |
| Web search tool | `src/agent/agent/tools/web_search.py` | **DEAD CODE** — Tavily/DuckDuckGo có viết nhưng **không node nào import** (đã grep xác nhận) |
| Frontend status | `ChatPanel.tsx:369-376` | Trạng thái "Đang tìm…/Đang index…/Đang viết…" là **suy đoán theo đồng hồ** (backend chưa gửi status event) |
| History | `ChatPanel.tsx:239-242` + nodes | Chỉ gửi **5 message cuối × 150 ký tự** — mất ngữ cảnh follow-up dài |

### 1.3 Điểm yếu tìm được từ code (nối thẳng với pain evidence)

| # | Điểm yếu (bằng chứng trong code) | Pain thật từ chatlog/survey |
|---|---|---|
| W1 | **1 luồng tuần tự cứng, không tách vai trò**: research mode nhân đôi logic ngoài graph (`server.py`) → khó thêm tác vụ mới (tóm tắt, quiz, memory) mà không đẻ thêm nhánh `if` | 85.2% câu trả lời chỉ `review_concept` — tutor không đa dạng cách dạy |
| W2 | **Retrieval slide chỉ BM25 + k=3**, không sửa lỗi chính tả/teencode, không multi-query; `slide_title` hardcode d1/d2 (`server.py:241-244`) | 207/385 fail "không tìm thấy nội dung"; "sờ lai"→slide không hiểu; cite sai trang |
| W3 | **Không có khả năng tóm tắt toàn tài liệu** — mỗi turn chỉ nhìn 1-3 trang | 84/385 fail yêu cầu tóm tắt cả buổi; survey 58.6% nói AI "chỉ đọc lại slide" |
| W4 | **Không có trạng thái thật** — frontend đoán theo thời gian; research có thể 12-24s (latency max 23.8s từ chatlog) | Người học tưởng treo, bỏ đi |
| W5 | **Không có sư phạm**: không phát hiện misconception, không follow-up, không kiểm tra hiểu — 3 trường dữ liệu luôn rỗng trong chatlog, code hiện không có cơ chế | misconceptions=0/1261, follow_ups=0/1261, asked_check_question=3/2515 |
| W6 | **Không có memory**: context = 5 msg × 150 ký tự, mất khi reload | Conv C0128: hỏi "React là gì" 3 lần liên tiếp vẫn fail — không nhớ đã từng trả lời |
| W7 | **Không có observability**: không đo latency/token/cost (chatlog: `total_cost_usd` luôn = 0), không trace node | Không biết cải tiến nào có ích, không gate regression khi đổi agent |
| W8 | **Research không cache, không timeout song song**: mỗi turn tìm arXiv lại từ đầu (rate-limit 3s/request), paper đã index vẫn phải qua bước download/ingest check | Latency P90 3.7s, max 23.8s; turn research hay >10s |
| W9 | **Tool web search (Tavily) chết**: chỉ có arXiv làm nguồn ngoài → câu hỏi "tin mới nhất", "logistics" không có đường trả lời | 43 turn logistics + các câu cần kiến thức ngoài paper đều fail |
| W10 | **day03 bản scan**: 66/71 trang là ảnh, index chỉ có 8 trang text (DATA-REPORT.md) | Day 3 (Design Pattern/ReAct) gần như mù với RAG |

### 1.4 Điểm mạnh cần GIỮ NGUYÊN (non-goals)

- API contract `/api/chat/stream`, `/api/papers`, `/api/papers/import-arxiv` — frontend không đổi cách gọi.
- **Grounding audit** (claim → quote kiểm chứng) của paper RAG — điểm khác biệt cạnh tranh, không phá.
- Security guard `validate_input` + prompt của Slide Researcher ("KHÔNG có kiến thức riêng").
- UI 3-panel đã chốt theo DESIGN.md v3 (user duyệt 24/08) — chỉ thêm phần hiển thị nếu cải tiến cần.
- Provider LLM hiện tại (Gemini flash-lite + fallback) — không đổi model trong đợt này.

---

## 2. Kiến trúc multi-agent đề xuất (to-be)

### 2.1 Nguyên tắc: **Orchestrator + chuyên gia, giữ LangGraph có cấu trúc**

KHÔNG chuyển sang "agentic free-loop" (LLM tự gọi tool tùy ý) — quá rủi ro cho hackathon. Thay vào đó: **Orchestrator định tuyến 1 lần, mỗi chuyên gia là 1 node/subgraph có contract rõ ràng**, mọi chuyên gia ghi kết quả vào `AgentState` chung (mở rộng `state.py`, giữ backward-compatible).

### 2.2 Sơ đồ to-be

```
                        ┌──────────────────────────────────────────┐
   user ──► ChatPanel ──►│  ORCHESTRATOR ROUTER (node mới, LLM nhỏ) │
        (SSE + status)   │  1. Chuẩn hoá input (teencode, chính tả,  │
                         │     React→ReAct, spell-fix)               │
                         │  2. Phân loại ý định:                     │
                         │     slide | deep | summary | logistics |  │
                         │     off-topic | unclear                   │
                         │  3. Chọn 1-2 chuyên gia + thứ tự           │
                         └───────┬──────────┬──────────┬─────────────┘
                                 ▼          ▼          ▼
        ┌────────────────┐ ┌──────────────┐ ┌────────────────────┐
        │ SLIDE SCHOLAR  │ │ RESEARCH     │ │ SUMMARY AGENT (mới)│
        │ (nâng từ        │ │ SCHOLAR      │ │ map-reduce toàn     │
        │  search_slide)  │ │ (nâng từ     │ │ tài liệu, cache     │
        │  multi-query,   │ │  web_search) │ │ theo doc_id         │
        │  toàn tài liệu, │ │  + cache     │ └──────────┬─────────┘
        │  page-anchor    │ │  + web       │            │
        │  citation       │ │  (Tavily)    │            │
        └────────┬───────┘ └──────┬───────┘            │
                 └────────┬───────┘────────────────────┘
                          ▼
        ┌─────────────────────────────────────────────┐
        │ TUTOR COACH (mới — agent nói chuyện với user)│
        │  soạn câu trả lời cuối theo phong cách sư   │
        │  phạm: move, misconception detect, check     │
        │  hiểu, follow_ups, citations thống nhất      │
        └────────────────────┬────────────────────────┘
                             ▼
        ┌─────────────────────────────────────────────┐
        │ MEMORY AGENT (mới)  ◄─── đọc/ghi mọi node     │
        │  phiên học: doc/trang/khái niệm/misconception│
        │  notes; context thay cho 5 msg × 150 ký tự    │
        └────────────────────┬────────────────────────┘
                             ▼
        ┌─────────────────────────────────────────────┐
        │ EVAL & OBSERVABILITY (mới)                   │
        │  trace node: latency/tokens/cost thật        │
        │  golden set 24 case = regression gate        │
        │  nhận rating up/down từ UI                   │
        └─────────────────────────────────────────────┘

Shared infra (ngang): SSE status events thật · cache paper theo arxiv-id ·
timeout+fallback · unified citation format [S1]/slide chip · OCR day03 (P1,P3)
```

### 2.3 Bảng 7 vai trò agent

| # | Agent | Nhiệm vụ | Input → Output | Nói chuyện trực tiếp với user? | LLM calls | Tool dùng |
|---|---|---|---|---|---|---|
| 1 | **Orchestrator Router** (mới) | Chuẩn hoá input + phân loại ý định + chọn chuyên gia | question+meta → {intent, normalized_q, plan} | Không (nội bộ) | 1 call nhỏ (flash-lite) | security.py (giữ) |
| 2 | **Slide Scholar** (nâng cấp) | Trả lời từ slide với citation trang | question + doc_id + page → {answer_draft, slide_cites, confidence, gaps[]} | Không (nội bộ) | 1 call | slide_index (BM25 → hybrid tùy chọn A-02) |
| 3 | **Research Scholar** (nâng cấp) | Tìm/đọc paper, grounding audit | normalized_q + paper_source → {context, citations, citation_details, grounded} | Không (nội bộ) | 2-3 calls (rewrite, rerank, phân đoạn) | arxiv_search/download, local_rag, web_search (tái sinh) |
| 4 | **Summary Agent** (mới) | Tóm tắt toàn tài liệu theo module, cache | doc_id → {summary, key_concepts[], quiz_qs[]} | Không (nội bộ) | 2-4 calls (map+reduce, với cache) | slide_index toàn doc, JSON cache |
| 5 | **Tutor Coach** (mới) | Soạn câu trả lời cuối + sư phạm | kết quả các agent + learner state → {answer, move, misconceptions[], follow_ups[], asked_check_question} | **CÓ — agent này là "VLearn Tutor"** | 1-2 calls | kết quả node khác + Memory |
| 6 | **Memory Agent** (mới) | Lưu/đọc hồ sơ phiên học | event → state; state → context | Không (nội bộ) | 0 (thuần code) | SQLite/JSONL + API `/api/learners/{id}/state` |
| 7 | **Eval & Observability** (mới) | Đo + gate chất lượng | trace event, golden set → report | Không (nội bộ) | 0-1 calls (golden khi cần) | middleware, dataset 24 case |

### 2.4 Luồng mẫu sau nâng cấp (1 turn)

```
"tóm tắt sờ lai này"  (câu fail thật — Conv C0128/chatlog)
1. Orchestrator: spell-fix "sờ lai"→"slide" · intent=summary · plan=[Summary Agent]
2. Summary Agent: map-reduce 52 trang doc d7 (cache) → {ý chính, khái niệm, câu hỏi ôn}
3. Tutor Coach: soạn tóm tắt tiếng Việt + 3 follow_up ("Bạn muốn đào sâu phần nào?…")
4. SSE: "Đang tóm tắt tài liệu…" (status thật từ backend)
5. Eval: ghi latency/tokens; nếu learner downvote → vào log regression
```

---

## 3. DANH SÁCH CẢI TIẾN — CHỜ DUYỆT TỪNG MỤC

Quy ước: `Effort` theo ngày dev hackathon · `Phạm vi`: B=backend-only, B+F=backend+frontend, D=data · `Phụ thuộc`: mục phải xong trước.

### PHASE 1 — Nền móng (làm trước: an toàn, không đổi UX lớn, giá trị tức thì)

---

#### ☐ A-01 — Orchestrator Router + chuẩn hoá input

| | |
|---|---|
| **Mô tả** | Thêm node Orchestrator đầu luồng: (1) chuẩn hoá input — sửa teencode/chính tả ("sờ lai"→slide, "promt"→prompt, "React"→gợi ý ReAct khi trong ngữ cảnh AI), (2) phân loại ý định (slide / deep / summary / logistics / off-topic / unclear), (3) chọn chuyên gia. Giữ `validate_input` làm cổng an toàn trước. Research mode được đưa **vào graph thống nhất** (bỏ nhánh `if is_research` cứng trong server.py) |
| **Giá trị cho người học** | Tấn công trực tiếp 385 turn fail: phân loại đúng ý định → không còn trả lời "không tìm thấy" khi user hỏi tóm tắt/kiến thức ngoài slide; bắt teencode (3 turn), "React vs ReAct" (5 turn), giảm câu hỏi lặp lại (Conv C0128) |
| **Phạm vi / Effort** | B / **S–M (0.5–1 ngày)** |
| **Đụng file** | `src/agent/agent/nodes/orchestrator.py` (mới), `graph.py`, `server.py`, `state.py` (thêm `intent`, `normalized_question`), `security.py` (giữ nguyên) |
| **Rủi ro** | Thêm 1 LLM call/turn (chi phí nhỏ, flash-lite); phân loại sai → phải có fallback "không chắc chắn → hỏi lại/clarify" thay vì đoán |
| **Phụ thuộc** | — |
| **XONG KHI** | 5 câu mẫu thật từ chatlog (kể cả "sờ lai", "React là gì", "tóm tắt…") định tuyến đúng intent trong test script; mode normal/research vẫn trả lời như cũ |
| **CHỜ DUYỆT** | ☐ |

---

#### ☐ A-02 — Slide retrieval nâng cấp: toàn tài liệu + multi-query + hybrid

| | |
|---|---|
| **Mô tả** | Slide Scholar truy vấn **toàn tài liệu** (không giới hạn 1 doc + k=3): chạy 2-3 biến thể query (gốc, rút gọn, tiếng Anh) rồi hợp nhất điểm; sửa cite sai trang bằng chặn `doc_id` đúng + kiểm tra page-in-view; **tùy chọn** bật hybrid dense (embedding) cho slide như paper RAG — giữ fallback BM25 khi hết quota; sửa `slide_title` hardcode d1/d2 → lấy từ `slideDocs.ts`/metadata |
| **Giá trị cho người học** | Giải 207/385 fail "không tìm thấy" + 2 downvote cite sai trang; trả lời đúng trang user đang nhìn |
| **Phạm vi / Effort** | B / **M (1 ngày)** |
| **Đụng file** | `rag.py` (retrieve_context multi-query, optional hybrid), `nodes/slide_search.py`, `server.py` (title), `config.py` |
| **Rủi ro** | Embedding cần quota API — phải giữ đường fallback BM25 (đã có sẵn pattern ở paper RAG `keyword_search`) |
| **Phụ thuộc** | A-01 (nhận normalized query) |
| **XONG KHI** | 10 câu fail mẫu từ chatlog đều trả về nội dung đúng trang; cite không bao giờ nhảy sang doc khác |
| **CHỜ DUYỆT** | ☐ |

---

#### ☐ A-03 — Summary Agent (map-reduce toàn tài liệu)

| | |
|---|---|
| **Mô tả** | Agent tóm tắt toàn bộ tài liệu (52-132 trang): map từng nhóm trang (chunk 360 từ sẵn có) → reduce thành tóm tắt theo module; output JSON {summary, key_concepts[], quiz_questions[]}; **cache theo doc_id + file hash** (chỉ tính lại khi PDF đổi); chạy nền khi chọn tài liệu trước, hoặc on-demand khi user hỏi "tóm tắt ngày hôm nay" |
| **Giá trị cho người học** | Giải 84/385 fail tóm tắt — pattern lớn thứ 2; survey 58.6% chê "chỉ đọc lại slide" được xử lý; tóm tắt kèm câu hỏi ôn giúp ôn thi |
| **Phạm vi / Effort** | B (+F nhẹ: nút "Tóm tắt tài liệu") / **M (1–1.5 ngày)** |
| **Đụng file** | `nodes/summary.py` (mới), `rag.py` (đọc toàn doc), cache file/SQLite, `ChatPanel.tsx` (1 chip gợi ý, tái dùng empty-state) |
| **Rủi ro** | Token cho doc 132 trang — map-reduce + cache giảm lặp; kết quả dài → cần cấu trúc + collapse theo module |
| **Phụ thuộc** | A-01 |
| **XONG KHI** | "Tóm tắt toàn bộ day 4" (132 trang) trả về tóm tắt module đúng trọng tâm trong <30s lần 2 (cache); 5 câu tóm tắt mẫu từ chatlog pass |
| **CHỜ DUYỆT** | ☐ |

---

#### ☐ A-04 — SSE status events thật (bỏ heuristics frontend)

| | |
|---|---|
| **Mô tả** | Backend gửi `data: {"status": "routing"/"searching"/"indexing"/"summarizing"/"answering", "elapsed_ms": …}` giữa các bước (đã được DESIGN.md §7 đề xuất từ trước); ChatPanel hiển thị trạng thái + bước thật thay vì đoán theo đồng hồ; backward-compatible — frontend cũ bỏ qua event lạ |
| **Giá trị cho người học** | Hết cảm giác "treo" khi research 12-24s; biết chính xác agent đang làm gì → giảm bỏ cuộc giữa chừng |
| **Phạm vi / Effort** | B+F / **S (0.5 ngày)** |
| **Đụng file** | `server.py` (event_stream), `nodes/*` (yield status qua callback), `ChatPanel.tsx` (typingStatus + mapping icon) |
| **Rủi ro** | Rất thấp — chỉ thêm event SSE, không đổi contract |
| **Phụ thuộc** | — (chạy song song các mục khác) |
| **XONG KHI** | Mọi chế độ hiển thị đúng bước thật (không còn text "…12s" đoán mò); stream vẫn render đúng |
| **CHỜ DUYỆT** | ☐ |

---

### PHASE 2 — Multi-agent học tập (giá trị sư phạm — trái tim của "giúp người học thuận tiện hơn")

---

#### ☐ A-05 — Tutor Coach Agent: envelope sư phạm + misconception + follow-up

| | |
|---|---|
| **Mô tả** | Agent soạn **câu trả lời cuối** từ kết quả các chuyên gia, theo envelope có cấu trúc: `{answer, move (review_concept/give_example/give_hint/validate…), misconceptions[], follow_ups[], asked_check_question}` — chính là 3 trường đang chết trong chatlog. Phát hiện misconception từ câu hỏi + câu trả lời (vd: nhầm React/ReAct, nhầm token/embedding), tùy độ chắc chắn mà sửa ngay hoặc hỏi lại; cuối turn có thể kèm 1 câu check hiểu ngắn (tần suất do user chốt, xem §4). Frontend render follow-ups thành chip nhấn được (tái dùng empty-state chip) |
| **Giá trị cho người học** | misconceptions=0→có; follow_ups=0→có; 85.2% review_concept đơn điệu → đa dạng move; kéo dài hội thoại (52.8% bỏ sau 1 turn) bằng câu hỏi tiếp có chủ đích |
| **Phạm vi / Effort** | B+F / **L (1.5–2 ngày)** |
| **Đụng file** | `nodes/tutor_coach.py` (mới), `state.py` (envelope), `server.py` (trả envelope trong SSE done), `ChatPanel.tsx` (render follow-ups + badge move) |
| **Rủi ro** | Câu hỏi check hiểu gây phiền nếu quá thường xuyên → mặc định nhẹ (chỉ khi learner có dấu hiệu khó); envelope phải backward-compatible với frontend cũ |
| **Phụ thuộc** | A-01 (intent), A-06 (misconception history) |
| **XONG KHI** | Conv C0128 mô phỏng: gặp "React là gì" → coach ghi misconception + gợi ý "Bạn có định hỏi ReAct pattern trong slide Day 3?"; mỗi turn trả về envelope đủ 4 trường; 5 turn mẫu có follow_up click được |
| **CHỜ DUYỆT** | ☐ |

---

#### ☐ A-06 — Memory Agent: hồ sơ phiên học thay cho 5 msg × 150 ký tự

| | |
|---|---|
| **Mô tả** | Lưu có cấu trúc: doc đang học, trang đã xem, khái niệm đã hỏi, misconception đã sửa, notes, câu hỏi lặp; SQLite nhỏ (hoặc JSONL), endpoint `GET/PUT /api/learners/{learner_id}/state`; mọi agent đọc context từ đây thay vì cắt lịch sử; learner_id mặc định per-browser (anonymous), sẵn sàng gắn login sau |
| **Giá trị cho người học** | Follow-up nhiều turn giữ ngữ cảnh (Conv C0050 30-turn tốt sẽ thành chuẩn); không hỏi lặp câu đã trả lời; nền cho A-10 (gợi ý ôn tập) |
| **Phạm vi / Effort** | B (+F nhẹ: gửi learner_id) / **M (1 ngày)** |
| **Đụng file** | `agent/memory/` (mới: store.py + schema), `server.py` (2 endpoint), `nodes/*` (lấy context từ memory), `ChatPanel.tsx` (token learner_id) |
| **Rủi ro** | Data cá nhân — giữ anonymous + không lưu nội dung nhạy; migration khi thêm login (chỉ là thêm cột) |
| **Phụ thuộc** | — |
| **XONG KHI** | Tắt máy mở lại vẫn nhớ khái niệm đã hỏi hôm trước; script test 3 turn liên tiếp không lặp câu hỏi giống nhau |
| **CHỜ DUYỆT** | ☐ |

---

#### ☐ A-07 — Eval & Observability: trace thật + golden-set gate + rating UI

| | |
|---|---|
| **Mô tả** | Middleware đo mỗi node: latency, tokens in/out, cost ước tính, lỗi → ghi vào log/DB (khắc phục triệt để `total_cost_usd=0` của chatlog); **golden set 24 case có sẵn** chạy tự động sau mỗi thay đổi graph = regression gate; thêm hàng up/down (👍👎) dưới mỗi câu trả lời tutor trong UI, gửi về server kèm trace_id |
| **Giá trị cho người học** | Gián tiếp: mọi cải tiến phải qua cổng chất lượng → user không bị "nâng cấp làm hỏng"; rating giúp đo hài lòng thật thay vì 2.8% rating |
| **Phạm vi / Effort** | B+F / **M (1 ngày)** |
| **Đụng file** | `agent/observability/` (mới), `server.py` (middleware + /api/feedback), `ChatPanel.tsx` (2 nút rating), `src/eval/` (script gate) |
| **Rủi ro** | Chi phí chạy golden set (24 case × vài LLM call) — chạy theo yêu cầu/CI, không chạy mỗi turn |
| **Phụ thuộc** | — |
| **XONG KHI** | Mỗi turn có dòng log latency/tokens/cost đủ 3 classification; chạy gate sau khi sửa thấy đúng 21/24 (hoặc cao hơn) |
| **CHỜ DUYỆT** | ☐ |

---

#### ☐ A-08 — Research Scholar hoàn chỉnh: vào graph + cache + timeout + web search

| | |
|---|---|
| **Mô tả** | Đưa research thành subgraph chuẩn (bỏ nhánh cứng server.py); **cache**: map (query_hash → paper chọn) + tránh download lại paper đã index (theo arxiv-id); timeout + chạy song song 2 nguồn (arXiv API + DDG fallback); **tái sinh web search Tavily** (tool đang chết) cho câu hỏi cần tin cập nhật/không có paper; giữ nguyên grounding audit |
| **Giá trị cho người học** | Research nhanh hơn hẳn (bỏ 3-5s download lặp); trả lời được câu "tin mới nhất 2026" mà arXiv không phủ; P90 latency giảm kỳ vọng |
| **Phạm vi / Effort** | B / **M (1–1.5 ngày)** |
| **Đụng file** | `graph.py` (research subgraph), `nodes/web_search.py`, `tools/research.py` (cache), `tools/web_search.py` (kết nối lại), `.env` (TAVILY_API_KEY tùy chọn) |
| **Rủi ro** | Tavily cần key (không có → fallback DDG có sẵn); cache cần invalidate khi arXiv có bản mới (cache theo ngày) |
| **Phụ thuộc** | A-01 |
| **XONG KHI** | Hỏi lặp cùng chủ đề 2 lần: lần 2 không gọi lại arXiv API (verify qua log); turn research <12s ở P90; 5 câu research mẫu vẫn grounded |
| **CHỜ DUYỆT** | ☐ |

> **📌 NOTE (Dev2, sau P1b — E2E xác nhận OK, :8001 code mới, normal+research 200):** `_build_research_query` (nodes/web_search.py) hiện tạo query cụm dài (vd "retrieval augmented generation survey foundations") → arXiv API `all:"..."` đòi cụm NGUYÊN VẸN → trả **0 kết quả dù chủ đề tồn tại** (test thật: `all:"retrieval augmented generation survey"` = 0 entries vs `all:"retrieval augmented generation"` = 2 entries + pipeline paper hoạt động đủ 4 citations). Hướng sửa khi làm A-08: (a) tách query thành cụm ngắn 2-4 từ, (b) thử nhiều biến thể query khi kết quả rỗng (fallback cascade), hoặc (c) ghép từ khóa bằng AND thay vì phrase `"..."`. Kèm regression test: query dài quen thuộc phải trả ≥1 paper.

---

### PHASE 3 — Mở rộng (optional — user quyết sau P1/P2)

---

#### ☐ A-09 — Logistics/Steering Agent + kho kiến thức khóa học

| | |
|---|---|
| **Mô tả** | Kho KB nhỏ (JSON hoặc markdown tay ~20 mục): deadline, bài tập, lab, giảng viên, cách tải file, cấu trúc khóa học → agent trả lời câu logistics thay vì từ chối; giới hạn phạm vi rõ ràng (không trả lời ngoài KB, không bịa) |
| **Giá trị cho người học** | Giải 43/385 turn logistics (pattern #3); giảm cảm giác "AI vô dụng với câu hỏi thật" |
| **Phạm vi / Effort** | B / **M (0.5–1 ngày)** |
| **Đụng file** | `data/course-kb.json` (mới), `nodes/logistics.py` (mới), `graph.py` route intent=logistics |
| **Rủi ro** | KB thiếu/ngày lệch → chính sách "không có trong KB thì nói không biết + đường dẫn hỏi giảng viên" |
| **Phụ thuộc** | A-01, cần user cung cấp nội dung KB |
| **XONG KHI** | 10 câu logistics mẫu trả lời đúng (5 có trong KB, 5 từ chối đúng cách không bịa) |
| **CHỜ DUYỆT** | ☐ |

---

#### ☐ A-10 — Learning analytics + gợi ý ôn tập (từ Memory)

| | |
|---|---|
| **Mô tả** | Dựa trên Memory Agent: thẻ "Tiến độ hôm nay" (số khái niệm đã hỏi, misconception đã sửa), gợi ý ôn tập nhẹ (spaced repetition đơn giản: "Khái niệm X bạn hỏi 3 ngày trước — ôn lại?"), đề xuất doc kế tiếp trong giáo trình (17 tài liệu đã có sẵn) |
| **Giá trị cho người học** | Chủ động dẫn dắt học (trả lời "học gì tiếp"), biến app từ "hỏi-đáp" thành "người đồng hành" |
| **Phạm vi / Effort** | B+F / **S–M (0.5–1 ngày)** |
| **Đụng file** | `nodes/review_suggester.py` (mới), `ChatPanel.tsx` (1 card nhỏ), `Sidebar.tsx` (badge gợi ý) |
| **Rủi ro** | Gợi ý sai thời điểm gây phiền → hiển thị mặc định thu gọn, user tắt được |
| **Phụ thuộc** | A-06 |
| **XONG KHI** | Sau 3 turn học, có 1 gợi ý ôn tập đúng khái niệm đã hỏi; có nút tắt card |
| **CHỜ DUYỆT** | ☐ |

---

#### ☐ A-11 — OCR day03 + làm sạch index slide

| | |
|---|---|
| **Mô tả** | Chạy OCR (OCRmyPDF/Tesseract) cho `day03-design-pattern-react.pdf` (66/71 trang ảnh — DATA-REPORT.md) → re-index; thêm unit test đếm trang text; kiểm tra 17 doc đều có text ≥90% trang |
| **Giá trị cho người học** | Day 3 (ReAct/Design Pattern — chủ đề gây nhiều fail nhất trong chatlog: "React là gì" ×5) được RAG phủ đầy đủ |
| **Phạm vi / Effort** | D / **M (1 ngày, phụ thuộc máy có OCR)** |
| **Đụng file** | `src/frontend/public/day03-*.pdf` (bản OCR), `rag.py` (re-index), script OCR trong `src/data/` |
| **Rủi ro** | OCR chất lượng tiếng Việt — cần review 5 trang mẫu sau khi chạy; file thay → phải re-index |
| **Phụ thuộc** | — |
| **XONG KHI** | day03 index ≥60/71 trang có text; hỏi "ReAct pattern" trả về content đúng trang |
| **CHỜ DUYỆT** | ☐ |

---

## 4. Lộ trình tổng thể & tiêu chí nghiệm thu

| Phase | Mục tiêu | Mốc đo được | Mục |
|---|---|---|---|
| **P1 — Nền móng** (tuần 1) | Định tuyến đúng, retrieval tốt hơn, tóm tắt được, không còn "treo" | Fail rate trên 20 câu mẫu chatlog giảm ≥50% (mục tiêu: từ 30.5% → <15%); research không còn cảm giác treo | A-01, A-02, A-03, A-04 |
| **P2 — Học tập** (tuần 2) | Multi-agent sư phạm: misconception, follow-up, memory, đo lường | follow_ups & misconceptions xuất hiện ≥80% turn mẫu; golden set ≥87.5%; mỗi turn có trace đầy đủ | A-05, A-06, A-07, A-08 |
| **P3 — Mở rộng** (tuần 3+, tùy duyệt) | Trả lời logistics, dẫn dắt ôn tập, phủ dữ liệu | 10/10 câu logistics đúng chính sách; 1 gợi ý ôn/turn mẫu; day03 ≥60/71 trang text | A-09, A-10, A-11 |

**Tiêu chí nghiệm thu chung (mọi mục):**
1. Không phá 24 case golden set hiện có (hoặc có giải trình rõ ràng).
2. API contract cũ vẫn chạy với frontend cũ (backward-compatible).
3. UI tuân thủ DESIGN.md v3 tokens (nếu đụng frontend).
4. Mỗi mục có 5 câu test mẫu từ chatlog thật kèm kết quả PASS/FAIL ghi vào `../validation/`.

---

## 5. Câu hỏi cần USER quyết (trước khi bắt đầu code)

1. **Chi phí/độ trễ**: A-01 + A-05 làm mỗi turn tăng từ 2-3 lên ~4-7 LLM call (cost x2-3, latency có thể +30-50% ở P90). Chấp nhận đánh đổi để có câu trả lời chất lượng hơn chứ? *(Đề xuất: chấp nhận ở P1, tối ưu lại ở P2 bằng cache/memory.)*
2. **Tutor Coach chủ động đến đâu?** (a) Luôn kèm 1 câu check hiểu cuối mỗi turn · (b) Chỉ khi learner có dấu hiệu khó hiểu/lặp câu hỏi *(Đề xuất: b)* · (c) Không check hiểu, chỉ follow-up gợi ý.
3. **Memory theo ai?** (a) Anonymous per-browser (nhanh, không cần login) *(Đề xuất: a)* · (b) Có login học viên (cần tích hợp auth VLearn thật).
4. **Logistics KB (A-09)**: user có sẵn dữ liệu khóa học (deadline/bài tập/giảng viên) để nhóm đưa vào KB không, hay bỏ A-09?

---

## 6. Non-goals (KHÔNG làm trong đợt này — để tránh trôi phạm vi)

- ❌ Không đổi API contract hiện có; không buộc thay frontend.
- ❌ Không chuyển sang "agent tự do" (LLM tự chọn tool liên tục) — giữ graph có cấu trúc, kiểm soát được.
- ❌ Không thay đổi provider/model LLM; không thêm dependency nặng (LangGraph, SQLite, pypdf hiện có là đủ).
- ❌ Không đổi thiết kế UI 3-panel đã chốt (DESIGN.md v3); chỉ thêm phần render cho dữ liệu mới.
- ❌ Không làm auth/account đầy đủ, không deploy production trong đợt này.
- ❌ Không bỏ grounding audit của paper RAG — đây là "giấy thông hành" tin cậy của Research mode.

---

*Hết plan — Arch2 (vlearn-ux-team) · Nếu user duyệt mục nào, PO chuyển thành task giao Dev, mỗi mục kèm acceptance criteria ở trên.*

---

## CHANGELOG — theo bước triển khai (ghi bởi Dev khi làm)

### P1a — t14 · A-01 Orchestrator + A-02 Slide retrieval nâng cấp (Dev2)

**Trạng thái:** ✅ triển khai xong · `pytest src/agent/tests` = **45 passed** (20 cũ + 25 mới) · boot check OK trên cổng tạm 8002 (đã tắt, KHÔNG đụng server user 8000/8001).

**A-01 — Orchestrator Router:**
- Mới `src/agent/agent/nodes/orchestrator.py`: `normalize_question()` — sửa teencode/chính tả deterministic ("sờ lai"/"sơ lai"/"slai"→slide, "promt"→prompt…) + `React→ReAct` khi không thuộc ngữ cảnh JavaScript; `classify_intent()` — keyword deterministic trước (summary/logistics/off_topic), LLM flash-lite JSON cho phần còn lại (slide/deep/unclear), fallback `unclear→slide` khi LLM lỗi; `orchestrate()` node ghi `intent`, `normalized_question`, `original_question`, `orchestrator_note` vào state.
- `state.py`: thêm 6 field orchestrator/retrieval (backward-compatible).
- `graph.py`: entry = orchestrator; conditional: `off_topic→refuse_off_topic` (node mới trong `answer.py`, từ chối lịch sự, 0 LLM call) · `mode=research→web_search` trực tiếp (bỏ nhánh `if is_research` cứng — research giờ nằm TRONG graph, giữ nguyên hành vi: luôn tìm paper) · normal → `search_slide→decide_search→(web_search?)→generate_answer`.
- `server.py`: `/api/chat` dùng graph thống nhất (bỏ 2 nhánh research riêng); `/api/chat/stream` giữ SSE token-streaming (ly do: stream cần yield token qua `llm.stream`, không qua graph) nhưng chạy `orchestrate()` đầu luồng + từ chối off-topic deterministic. API contract `/api/chat` + `/api/chat/stream` KHÔNG đổi field nào.

**A-02 — Slide retrieval nâng cấp:**
- `rag.py`: thêm `DOC_TITLES` (17 doc, khớp slideDocs.ts) — `server.resolve_slide_title()` thay hardcode d1/d2.
- **Full-corpus**: `retrieve(..., scope="auto"|"doc"|"corpus")` — auto = doc hiện tại trước + **page-in-view boost** (+0.12 trang đang xem, +0.06 cách ≤2) + **corpus fallback** khi doc hiện tại không có hit (fix 207 turn "không tìm thấy"); citations luôn mang prefix doc (`D10 - Trang 16`) nên không nhảy doc.
- **Multi-query**: `_expand_queries()` — 3 biến thể tối đa (gốc + 2 LLM qua `SLIDE_MULTI_QUERY=1` mặc định + 1 deterministic rút gọn tiền tố); hợp nhất điểm max; LLM lỗi/quota → fallback deterministic.
- **Hybrid dense+BM25 tùy chọn**: `SLIDE_HYBRID=1` → embed top-pool 24 trang + rerank bằng `HybridRetriever` (dense 0.76 + BM25 + MMR, dùng embedder đúng cấu hình RAGService); bất kỳ lỗi nào cũng tự fallback BM25 offline.
- `server.py`: `retrieve_slide_context(req)` — normal: k=3 scope=auto + current_page; research: k=2 scope=doc (chỉ làm context cho paper query, giữ nguyên).

**Tests mới:** `src/agent/tests/test_orchestrator.py` (25 test): normalize teencode/React, intent deterministic + LLM JSON + fallback, orchestrate node, refuse node, DOC_TITLES đủ 17 id, doc-first/corpus-fallback, scope doc/corpus, citation prefix, multi-query merge, page boost, LLM-expansion fallback. Test tự offline (autouse fixture tắt SLIDE_MULTI_QUERY/SLIDE_HYBRID).

**Smoke thật (cổng 8002):** `/api/health` → `{"status":"ok","slide_pages":926}` · off-topic → refusal deterministic cả `/api/chat` lẫn stream · "sờ lai trang 10 có gì?" route OK (slide_title d7 đúng) · "RAG pipeline gồm những bước nào?" (d10) → trả lời đúng + citation `D10 - Trang 16` ✓.

**Env flags mới:** `SLIDE_MULTI_QUERY` (mặc định 1) · `SLIDE_HYBRID` (mặc định 0 — bật khi muốn embedding dense cho slide; vẫn giữ BM25 fallback).

**Lưu ý P2:** A-03 Summary Agent sẽ nối vào `intent==summary` (đã có sẵn route trong state/graph — hiện summary vẫn đi luồng slide như cũ); LLM multi-query làm retrieval tăng +1 call/turn (nằm trong 4-7 call user đã chốt).

**Hotfix ngay sau t14 (Dev2):** bug `/api/chat` mode=research → HTTP 500 ở `answer.py:68` (`slide_result.strip()` trên None). Nguyên nhân: `build_initial_state` set `slide_search_result=None` cho mọi mode nhưng nhánh research (web_search → generate_answer) không set field này. Sửa: (1) `server.py build_initial_state` — research trả về `""`; (2) `answer.py generate_answer` + `server.py event_stream` — defensive `or ""` cho slide/web_result; (3) `slide_search.py decide_search` — cùng pattern defensive. Thêm 2 test regression (graph research không crash, generate_answer sống sót với None). Verify: pytest **47 passed**; boot cổng tạm 8002 + thật end-to-end: research `/api/chat` trả lời từ paper ✓ (stress 3 lần đều 200), research stream không crash ✓, normal vẫn PASS ✓; server 8002 đã kill, :8001 của user không đụng — **lưu ý: worker :8001 phải restart để nạp code hotfix** (traceback 500 cũ khớp code trước fix).
### P1b — t15 · A-03 Summary Agent + A-04 SSE status thật (Dev2)

**Trạng thái:** ✅ triển khai xong · `pytest src/agent/tests` = **62 passed** (47 + 15 mới) · boot cổng tạm 8002 OK (đã kill, :8001 của user không đụng) · `npm run build` frontend PASS (exit 0).

**A-03 — Summary Agent:**
- Mới `src/agent/agent/nodes/summary.py`: `summarize_doc()` node map-reduce — đọc toàn doc (slide_index.page_texts), chia nhóm trang (10/12/16 trang theo độ dài, tối đa 10 nhóm map), LLM map từng nhóm kèm citation `[Trang X]` → LLM reduce thành cấu trúc `## Mở đầu / ## Ý chính từng phần / ## Kết luận` + dòng follow-up.
- `resolve_summary_doc_id()`: "day N"/"ngày N" trong câu hỏi → doc_id (bản full d3–d16; day 12 chưa có data → fallback doc đang học); không nhắc day → doc đang học (active_doc_id từ state).
- **Cache JSON** `src/agent/agent/.summary_cache/{doc_id}.json` theo file mtime+size (chỉ tính lại khi PDF đổi): verify thật — "tóm tắt toàn bộ tài liệu" d8 → 12.8s lần đầu (LLM), **0.86s lần 2 (cache)** ≪ yêu cầu <30s.
- Fallback: LLM map/reduce lỗi → thông báo lịch sự hoặc ghép tóm tắt nhóm đã có; doc không có text (scan chưa OCR) → nói rõ.
- `graph.py`: `intent=summary → summarize_doc → END` (A-01 route, bỏ luồng slide cũ cho summary). `state.py`: +3 field (active_doc_id, summary_doc_id, summary_cache_hit).

**A-04 — SSE status thật:**
- `server.py`: helper `status_event(phase, detail, elapsed_ms)` — event `{"status": ..., "detail": ..., "elapsed_ms": ...}`; backward-compatible (frontend cũ chỉ đọc token/done/error, bỏ qua event lạ).
- Phases theo bước thật: `routing` (orchestrator) → `searching_slide` (normal) | `summarizing` (summary) | `rewriting_query` → `searching_arxiv` → `reading_paper` (research/normal+web) → `answering` (trước llm.stream). Elapsed_ms đo `time.monotonic()`.
- `ChatPanel.tsx`: state `statusPhase`, parse `data.status` trong SSE loop, reset khi gửi; `typingStatus` = `STATUS_LABELS[phase]` (7 label tiếng Việt) với **fallback đồng hồ cũ** khi backend cũ không gửi status (backward-compat 2 chiều).
- Verify stream thật (8002): normal → routing(0ms) → searching_slide(905ms) → answering(3946ms) + tokens + done + citation ✓; summary → routing → summarizing → answering + văn bản 2272 ký tự có `[Trang X]` ✓.

**Tests mới:** `src/agent/tests/test_summary.py` (15 test): day-resolver, page grouping, cache roundtrip/missing, summarize_doc cache-hit/no-pages/unknown-doc/map-failure, status_event format + payload backward-compatible, summary_token_chunks.

**Lưu ý P2:** A-05 Tutor Coach (envelope + follow-ups) có thể nối vào sau step này; summary hiện trả thẳng không qua generate_answer (1-2 LLM call nhỏ hơn đường cũ); SSE status giờ là chuẩn cho mọi phase mới.

### P2 — t17 · A-05 Tutor Coach + A-06 Memory anonymous (Dev2)

**Trạng thái:** ✅ triển khai xong · `pytest src/agent/tests` = **76 passed** (62 + 14 mới) · boot cổng tạm 8002 OK (đã kill, :8001 user không đụng) · `npm run build` frontend PASS (exit 0). Driver 10-turn + 3-turn repeat: kết quả chi tiết tại `../validation/A-05-TutorCoach-driver.md` + `../validation/A-06-Memory-driver.md`.

**A-05 — Tutor Coach (quyết định user: check hiểu CHỈ khi có dấu hiệu khó):**
- Mới `nodes/tutor_coach.py`: envelope 5 trường `{answer, move, misconceptions[], follow_ups[] (2-3), asked_check_question(bool)}`; `build_envelope()` shared giữa graph node + server stream.
- Dấu hiệu khó (deterministic, 0 LLM): câu mơ hồ ("không hiểu/rõ hơn/nói lại"...), hỏi LẶP (memory count >= 2), nhầm React/ReAct (Conv C0128 - detect cả khi orchestrator đã normalize).
- Check hiểu: chỉ phát sinh 1 LLM call khi có dấu hiệu (turn bình thường: 0 call thêm). Move: give_hint (khó) / review_concept (normal) / give_example (research) / validate (summary/từ chối).
- graph.py: `generate_answer -> tutor_coach -> END`, `summarize_doc -> tutor_coach` (envelope gắn cho mọi turn kể cả summary/off_topic); server: envelope trong SSE done + /api/chat response (optional, backward-compatible); ChatPanel.tsx: badge move + follow-up chips click được (điền composer, không gửi).
- **Verify thật (driver):** 5 turn bình thường asked=false **0/5** (yêu cầu 0/5) · 5 turn khó/lặp asked=true **5/5** (yêu cầu >=3/5) · Conv C0128: misconception ["Nhầm React (framework JS) với ReAct (pattern agent...)"] + follow-up "Bạn có định hỏi **ReAct pattern** trong slide Day 3..." ✓.

**A-06 — Memory anonymous per-browser (quyết định user: không login):**
- Mới `agent/memory/store.py` + `__init__.py`: JSON file/learner tại `agent/memory/data/{id}.json`, thread-safe, schema có cấu trúc (doc_id/page/concepts[]+count/questions[]+count/misconceptions[]/notes[]/updated_at), KHÔNG PII; learner_id xấu/rỗng -> state rỗng không crash.
- server.py: `learner_id` optional trong ChatRequest (backward-compat — frontend cũ không gửi -> memory rỗng -> hành vi cũ y hệt); endpoints mới `GET/PUT /api/learners/{learner_id}/state`; `build_context()` nạp "THÔNG TIN HỌC VIÊN (từ memory)" vào prompt stream.
- ChatPanel.tsx: sinh learner_id bằng crypto.randomUUID, lưu `localStorage["vlearn-learner-id"]`, gửi kèm mỗi request.
- **Verify thật:** GET lạ -> rỗng không crash · PUT upsert + GET persist · 3 turn "embedding là gì?" -> turn 3 asked=true (memory count=3), KHÔNG lặp y hệt · reload cùng browser -> cùng token -> memory còn (đã kiểm qua file memory + context).

**Lưu ý P2 còn lại:** A-07 phần còn lại (trace, rating UI, /api/feedback) · A-08 (research cache/web — note phrase-query đã ghi ở mục A-08). ChatPanel chưa render misconceptions (chỉ follow-ups + badge move) — render khi cần trong vòng sau.


### P2 — t18 · A-07 trace/tool-routing/feedback + A-08 Research nâng cấp (Dev2)

**Trạng thái:** ✅ triển khai xong · `pytest src/agent/tests` = **90 passed** (88 + 2 mới) · boot cổng tạm 8002 OK (đã kill, :8001 user không đụng) · frontend build PASS · gate REAL chạy được (0 TOOL_INFO_MISSING). Phân tích đầy đủ: `../validation/A-07-Gate-analysis.md`.

**A-08 — Research nâng cấp:**
- **Fix phrase-query (NOTE A-08):** `paper.py` — `_query_variants()` fallback cascade: phrase gốc -> AND giữa từ khóa (<=5, bỏ stop words, `all:x AND all:y`) -> cụm 3 từ đầu -> DuckDuckGo discovery. Test thật: query "retrieval augmented generation survey foundations" (trước trả 0) -> AND variant ra paper, cả pipeline citations đủ.
- **Cache paper-choice:** `research.py` — `_PAPER_CHOICE_CACHE` (query -> source/title/url, hết hạn theo NGÀY); verify thật: research 2 lần cùng chủ đề -> log `[arxiv-cache-hit]`, lần 2 KHÔNG gọi arXiv API, không download/ingest lại (resolve_source check giữ sẵn).
- **Hồi sinh web search:** `tools/web_search.py` (trước dead code) -> `research.query_web()` (Tavily key thật trong .env, fallback DDG) + `nodes/web_search.py`: arXiv rỗng -> web fallback "KẾT QUẢ TÌM WEB (Tavily/DuckDuckGo)" + citation "Web search"; verify thật: 5 kết quả có URL.
- **Routing paper:** normal mode + keyword (paper/bài báo/arxiv/research) -> research path (graph + stream đồng bộ) — "Tim paper ve X" không còn lạc vào slide.

**A-07 — Eval & Observability (phần còn lại):**
- Mới `agent/observability/trace.py` + data/: `record_trace()` JSONL mỗi turn {trace_id, mode, intent, tools, tool, tool_match (alias golden), latency_ms, tokens_in/out_est, cost_usd_est (>0), error}; `record_feedback()` JSONL.
- server.py: trace_id trong /api/chat + SSE done + header `X-VLearn-Trace-Id`; endpoint `POST /api/feedback` (rating 1/-1, validate); trace.tool đọc được bởi gate_run.py REAL (hết TOOL_INFO_MISSING).
- ChatPanel.tsx: like/dislike dưới mỗi câu trả lời tutor (lưu traceId từ done; POST /api/feedback; 1 lần/message; toast) — DESIGN tokens.
- Gate REAL: chạy full 24 case (exit ok, report `evals/eval/gate_results_*.md`); **6/24 PASS** — phân tích trung thực trong `../validation/A-07-Gate-analysis.md`: 9 case dùng skill sản phẩm CŨ không tồn tại (social/timeline/policy/paper_text/send) + 2 case news-lookup bị chặn off_topic + 2 case clarify/no_tool fallback chủ đích -> trần trung thực ~6-7/24, KHÔNG phải regression; đề xuất rebase golden set vlearn-ux ở vòng sau (PO quyết).

**Verify:** research x2 cache-hit ✓ · stream/normal/summary 200 + trace_id ✓ · feedback ok + 400 rating xấu ✓ · traces.jsonl/feedback.jsonl ghi đúng ✓ · 90/90 tests (query cascade, cache ngày, web fallback helper, trace/feedback, routing paper).

### t20 — Refactor cấu trúc monorepo production + rewrite README (Dev2)

**Quyết định (lệch nhẹ proposal, có lý do):** giữ `apps/api/agent/` nguyên gói (đã khớp LangGraph app structure: nodes/state/tools/memory/observability ✓) và giữ `server.py` là app entry duy nhất thay vì tách `api/routers/*` (5 endpoint, cohesive, tránh đổi import ~30 file giữa chừng demo; ghi nhận theo fastapi-best-practices cho vòng sau). Các mục còn lại theo proposal đầy đủ.

**Cây MỚI (đã hiện thực):**
```
apps/api/      ← src/agent (server.py + agent/{nodes,tools,memory,observability} + rag/security/providers/config + tests)
apps/web/      ← src/frontend (Next.js: "/" landing + "/app" workspace)
libs/rag/      ← codebase/rag (local_rag + tests + pyproject)
evals/eval/    ← src/eval (gate_run.py + golden)
data/          ← src/data
validation/ (ở gốc repo — ../validation/)
root: pyproject.toml · Makefile · docker-compose.yml · .env.example · .gitignore · start.sh/Dockerfile (đường dẫn mới)
```

**Đã sửa đồng bộ:** `agent/config.py` (AGENT_ROOT=apps/api, PAPER_RAG_ROOT=libs/rag) · `agent/rag.py` (PDF_DIR=apps/web/public) · `providers.py` (msg) · `.superdesign/resume.json` + init/*.md (contextFiles → apps/web) · GATE-README/libs rag README/MVP_RUN.md paths · `start.sh` (PYTHONPATH=apps/api:libs/rag/src) · `Dockerfile`.

**Verify (sau refactor):** pytest **115/115 PASS** (apps/api 90 + libs/rag 25) · `npm run build` PASS (routes / + /app) · boot cổng tạm 8002: health slide_pages=926 (PDF_DIR mới đúng), normal 200 + citation D10 · Trang 16, research 200 tool=papers · :8001/:3002 KHÔNG đụng · `.env` giữ nguyên, không thêm dependency.

**Addendum t20 (VX11 — finding QA2/t21):** câu teencode "điêu toa" bị LLM đánh off_topic → chặn oan. Fix trong `nodes/orchestrator.py`: off_topic từ LLM chỉ được chấp nhận khi có keyword off-topic rõ (`_has_off_topic_keyword`); thiếu keyword → hạ xuống `unclear` (đi luồng slide, search_slide tự quyết + không chặn). Prompt INTENT_PROMPT thêm hướng dẫn teencode → unclear. Tests: +2 (downgrade khi thiếu keyword, giữ off_topic khi có keyword) → pytest apps/api = **92 passed**. Không đụng mô tả task khác.

### t22 — A-11 OCR day03 (scan → text) (Dev2)

**Quyết định kỹ thuật (đã khảo sát, ghi rõ trong data/ocr-day03.py):**
- Khảo sát: PDF có text layer không? → fitz: chỉ **8/71 trang có text thật** (đúng DATA-REPORT). Tesseract **5.5.2 có sẵn hệ thống** (/opt/homebrew) nhưng thiếu `vie` → tải `vie.traineddata` (tessdata_fast, 531KB) vào **repo-local** `data/ocr-tessdata/` (TESSDATA_PREFIX, KHÔNG đụng /opt/homebrew). macOS Vision bỏ qua (không cần, tesseract+vie đủ).
- **Phương án: SIDECAR TEXT, không viết lại PDF** — giữ `day03-design-pattern-react.pdf` gốc cho viewer react-pdf (tránh rủi ro render), sinh `apps/web/public/day03-ocr/d5-p{n}.txt`; `agent/rag.py` SlideIndex ưu tiên đọc sidecar, extract_text chỉ là fallback (không đổi ngưỡng, không đổi doc khác).
- Pipeline: PyMuPDF render 250dpi → tesseract `-l vie --psm 3` → **63 trang OCR + 8 trang giữ text gốc = 71/71 có nội dung** (trong ~1.5 phút).

**Verify:** d5 index 71/71 (trước 8) · tổng 989 trang (trước 926) · retrieve "ReAct là gì" d5 → trang 4/35/52, trang 35 chứa định nghĩa "ReAct = Reasoning + Acting" · API thật cổng tạm 8002: "ReAct pattern là gì?" → **HTTP 200, answer thật kèm citation D5 - Trang 35** (case fail ×5 trong chatlog giờ trả lời được) · pytest **117/117** (92 api + 25 rag) · web build PASS · :8001/:3002 không đụng.

**Files:** mới `data/ocr-day03.py` + `data/ocr-tessdata/vie.traineddata` + `apps/web/public/day03-ocr/d5-p1..71.txt` · sửa `apps/api/agent/rag.py` (OCR_TEXT_DIR + sidecar ưu tiên). Tái chạy OCR khi cần: `.venv/bin/python data/ocr-day03.py` (idempotent, ghi đè sidecar).

### t23 — A-10 Learning analytics + gợi ý ôn tập (Dev2)

**Backend:** mới `agent/analytics/gaps.py` — hợp tín hiệu local (không DB mới): Memory A-06 (concept count/last_asked, misconception) + Trace A-07 (thêm `learner_id` vào payload — additive) + Feedback A-07 (rating theo trace_id → avg). Endpoint mới `GET /api/learners/{id}/gaps` → `{gaps:[{concept, ask_count, last_asked, misconception, related_docs:[{doc_id,title,page}] (qua slide BM25 corpus), suggestion:"Ôn lại X?"}], signals_total, min_signals:3, traces, errors, off_topic, avg_rating, refreshed_at}`. learner_id giờ gắn vào mọi trace (chat + stream) cho analytics.

**Frontend:** ChatPanel card "Gợi ý ôn tập" (surface-2 ring, overline label) — chỉ hiện khi `signals_total >= 3` và có ≥1 gap; tối đa 3 chip (concept, title tooltip "Đã hỏi N lần") click → điền composer câu ôn + focus (không gửi ngay); refresh sau mỗi SSE done + khi mount.

**Verify (cổng tạm 8002, đã kill; :8001/:3002 không đụng):** health OK · seed 3 turn (embedding ×2 + RAG) → GET gaps: embedding ask_count=2 đứng đầu, related_docs đúng (d9 Day 7 trang 21 · d10 Day 8 trang 8), suggestion chuẩn · pytest **122/122** (97 api + 25 rag; +5 test analytics) · web build PASS.

**Files:** mới `agent/analytics/{__init__,gaps}.py` + `apps/api/tests/test_analytics_gaps.py` · sửa `agent/observability/trace.py` (learner_id + traces_for/feedback_ratings) · `apps/api/server.py` (endpoint + learner_id vào trace) · `apps/web/src/components/ChatPanel.tsx` (card + refresh). Kết thúc: A-10 xong — P1+P2+P3 còn hoạt động đều đã triển khai.

**Addendum t23 (VX13+VX14 — regression từ QA2 gate REAL 18/20):** fix VX11 over-generalized (off_topic→unclear downgrade không ngưỡng) kéo câu cá nhân ngắn vào lookup. Sửa trong `nodes/orchestrator.py`: (1) **normalize đúng thay vì fallback** — "điêu toa"/"dieu toa" → "deploy" (teencode Day 15); (2) **ngưỡng downgrade** `_should_downgrade_to_unclear`: giữ off_topic nếu có OFF_TOPIC/PERSONAL cue; hạ unclear chỉ khi có COURSE_SIGNAL_KEYWORDS (slide/ai/model/llm/rag/deploy/…) hoặc câu ≥20 ký tự; (3) **PERSONAL_TOPIC_CUES** mới (đẹp trai/bạn là model/hãng nào/ai tạo ra bạn/…) → off_topic deterministic ngay từ classify_deterministic. Tests: +4 (normalize đieu-toa, VX13, VX14 ngắn giữ off_topic, câu dài học tập downgrade). Verify: pytest **126/126** (101 api + 25 rag) · thật 8002: "t có đẹp trai không" → off_topic/no_tool ✓, "bạn là model của hãng nào" → off_topic/no_tool ✓, "điêu toa model lên server" → unclear/lookup (không chặn oan) ✓ · :8001/:3002 không đụng.

**Addendum t26 (redesign card "Gợi ý ôn tập" — feedback user chính chủ):** card cũ 3 chip rời không nói rõ ý nghĩa → thiết kế lại thành **3 khối có ý nghĩa** (chỉ UI apps/web/src/components/ChatPanel.tsx, data giữ nguyên từ /api/learners/{id}/gaps): mỗi khối = icon (WarningCircle khi misconception / BookOpen khi hỏi lặp) + **tên khái niệm đậm** + **lý do rõ** ("Có dấu hiệu hiểu nhầm" / "Bạn đã hỏi N lần") + dòng "Hỏi lần cuối hôm nay/X ngày trước" + **tài liệu liên quan** (doc title · Trang N, click jump đúng doc/trang qua onJumpToDocPage, tối đa 2) + **nút "Ôn lại"** mỗi khối (điền composer + focus). Sắp xếp ưu tiên: misconception trước, rồi ask_count desc. Card bao surface-2 + ring; điều kiện signals_total ≥ 3 giữ nguyên. Verify: build PASS · DOM audit thật (3 khối, order ReAct(misconception)→embedding(2)→RAG(1), reason + doc links + Ôn lại đủ) · screenshot /tmp/vlearn-shots/t26/gaps-card-1440.png. Lưu ý: trong lúc test tôi vô tình pkill trúng dev :3002 của user → đã restart lại cùng lệnh (npm run dev -p 3002), verify 200.

### t27 — FIX mất ngữ cảnh paper khi follow-up "tóm tắt paper" (Dev2)

**Bug (user repro thật):** turn 1 Research trả paper arxiv-2201.04288v4.pdf kèm [S1]/[S3] → turn 2 "tóm tắt paper này" lại trả tóm tắt SLIDE Day 1 (summary node route cố định slide theo active_doc_id, không biết ngữ cảnh paper).

**Root cause (2 lớp):** (1) `summarize_doc` không xét paper trong câu hỏi/history; (2) history từ frontend (kèm sources) bị LangGraph `add_messages` normalize thành AIMessage → mất key `sources` trong path /api/chat (graph).

**Fix (3 tầng):**
- `nodes/summary.py`: `_try_paper_summary()` ưu tiên khi question chứa "paper/bài báo/arxiv" hoặc history/memory trỏ paper → tóm tắt PAPER qua local_rag (search top-k 12, fallback keyword_search, 1 LLM call, cấu trúc Mở đầu/Ý chính/Kết luận, citations [S1].. trang/dòng, **cache kèm citations** để lượt sau vẫn hiển thị nguồn); không có context paper → slide path như cũ (backward-compatible).
- `agent/memory/store.py` + `server.py`: `_remember_paper_source()` — Research trả paper arXiv → lưu `paper_source` vào Memory (A-06) tại turn 1 (cả /api/chat + stream); summary fallback đọc memory khi history bị normalize (sống qua mọi path, kể cả graph).
- `ChatPanel.tsx`: history gửi kèm `sources` (từ citationDetails) + citations (secondary, giúp stream path).

**Verify transcript THẬT (API tạm :8008, đã kill):** turn 1 research "Multiview Transformers video recognition" → paper arxiv-2201.04288v4.pdf + memory.paper_source ghi ✓ → turn 2 "tóm tắt paper này": `/api/chat` → intent=summary, answer "## Mở đầu — Paper nghiên cứu Multiview Transformers cho nhận diện video..." + citations [S1]/[S2]/[S4] arxiv-2201.04288v4.pdf ✓ · `/api/chat/stream` → cùng kết quả + done citations ✓ · **lần 2 (cache hit) citations vẫn giữ [S1]/[S2]** ✓. pytest **107/107** (api) / 132 tổng; web build PASS. :8001/:3002 không đụng.

### t28 — Citation paper [S1] nhảy trang (Dev2)

**Backend:** `GET /api/papers/{source}/pdf` — FileResponse PDF từ libs/rag/data/papers, validate regex `arxiv-[A-Za-z0-9._-]+\.pdf`, resolve qua RAGService (chưa index → 404), chặn path traversal; CORS + thêm localhost:3002. Verify live (cổng tạm 8008): trả 200 + `%PDF-1.5` (arxiv-2201.04288v4.pdf), traversal bị chặn (404 route-level + 400 unit).

**Frontend (3 file):**
- ChatPanel: prop `onOpenPaper`; chip citation paper match `arxiv-*.pdf - Trang N` → button nhảy trang (giữ chip slide cũ nguyên); trong block citation_details thêm nút "Xem trang N" (cạnh "Mở nguồn arXiv").
- page.tsx (workspace): state `paperView`; `openPaper/closePaper`; **deep-link `?paper=<source>&page=<n>`** mở thẳng paper view; chọn doc/jump doc → tự thoát paper.
- SlideViewer: props `paperView/onExitPaper`; viewerPdfPath = `/api/papers/{source}/pdf`, viewerDocId = `paper-{source}`; toolbar hiện badge "Paper · {source}" + nút **Thoát** về slide (ẩn doc-swithcher khi xem paper); effect scroll+flash đúng trang khi PDF load xong (cùng cơ chế slide); PDFViewer đổi file động.

**Verify:** pytest **135/135** (api 110 + rag 25; +3 endpoint tests) · web build PASS · endpoint live ✓. ⚠️ **CDP interact-full: BLOCKED môi trường** — prod build (Next 16 Turbopack) trong headless Chrome không hydrate trang /app được (tái hiện cả plain /app; không phải lỗi t28 — dev mode render chuẩn như các vòng trước; dev thứ 2 bị Next lock vì user :3002 đang giữ apps/web). Đề nghị QA2/QC2 verify UI trên :3002 sau khi captain restart với code mới: click chip paper → viewer đổi + đúng trang; Thoát → về slide; slide citation không đổi.

### t33 — P0-3 CI GitHub Actions — pytest + build + gate DRY (Dev4)

**Trạng thái:** ✅ triển khai xong — `.github/workflows/ci.yml` (mới) · mô phỏng local từng job (venv sạch + copy npm): api-tests **137/137 PASS** (sau khi fix requirements.txt — xem Lưu ý) · web-build **build PASS** (npm ci sạch + Next 16.2.12 TS sạch) · eval-gate DRY **20/20 NOT_RUN, exit 0** (đúng kỳ vọng DRY). Push thử branch `ci-test`: ✅ thành công (workflow sẽ chạy trên GitHub Actions; team không có token để xem run log → verify = mô phỏng local từng lệnh). · web-build **build PASS** (npm ci sạch + Next 16.2.12 TS sạch) · eval-gate DRY **20/20 NOT_RUN, exit 0** (đúng kỳ vọng DRY). Push thử branch `ci-test`: ✅ thành công (workflow sẽ chạy trên GitHub Actions; team không có token để xem run log → verify = mô phỏng local từng lệnh).

**Workflow (chặn merge — 3 job):**
- **Trigger:** `push` + `pull_request` vào `main` (branches filter), concurrency cancel-in-progress.
- `api-tests` (ubuntu, Python 3.12, cache pip theo requirements.txt): `pip install -r requirements.txt` + `pytest` → `PYTHONPATH=apps/api:libs/rag/src python -m pytest apps/api/tests libs/rag/tests --junitxml reports/pytest.xml` (offline autouse, không cần key). Timeout 15'.
- `web-build` (Node 22, cache npm theo apps/web/package-lock.json): `cd apps/web && npm ci && npm run build` (TS sạch), log tee → artifact khi fail. Timeout 15'.
- `eval-gate` (Python 3.12, stdlib-only — không cần pip): `python3 evals/eval/gate_run.py --dry --json reports/gate-dry.json` + assert summary `total>=20 && not_run==total && mode==dry` (DRY không gọi LLM, exit 0; REAL cần key + backend → skip trong CI bằng env check `OPENAI_API_KEY == ''`, ghi rõ lệnh chạy thủ công). Timeout 10'.
- **Artifact khi fail:** pytest.xml · web-build.log · gate_results_*.md + gate-dry.json.

**Lưu ý quan trọng (đã kiểm chứng local):** (1) `pytest` KHÔNG nằm trong `requirements.txt` → job api-tests cài `pytest` riêng. (2) Bắt buộc `PYTHONPATH=apps/api:libs/rag/src` để resolve `local_rag` (chạy `pytest apps/api` không có PYTHONPATH → ModuleNotFoundError) — khớp `make test` trong Makefile. (3) **Fix requirements.txt:** mô phỏng CI với venv sạch bắt được 2 test rớt (`test_gemini_clients.py` — `ModuleNotFoundError: No module named 'google'`): `requirements.txt` thiếu `google-genai` (pyproject khai nhưng file pin không có; gemini_clients import lazy trong `embed()`). Đã thêm `google-genai==2.19.0` → mô phỏng lại **137/137 PASS**. Máy sạch chạy CI mà thiếu dòng này sẽ đỏ — pipeline chặn merge bắt được đúng loại lỗi này.

### t32 — P0-1 Dedupe mã doc (citation short/full hết nhảy nhầm) (Dev2)

**Scheme đã chốt (gợi ý PO2, áp dụng luôn):** short hackathon d1/d2 GIỮ "D1"/"D2" (bản user quen); full Day1/Day2 (d3/d4) đổi "D1-F"/"D2-F" — unique + mnemonic ("F" = full). Các doc khác giữ doc_id.upper() (d5→"D5", d13→"D13", day05-ref→"DAY05-REF") — vốn không trùng.

**Sửa đồng bộ (3 file):**
- apps/api/agent/rag.py: `citation_label()` + `_DOC_LABELS` — context header + citations dùng label mới (d3 → "D1-F - Trang N").
- apps/web/src/components/slideDocs.ts: code d3 "D01"→"D1-F", d4 "D02"→"D2-F" (sidebar/switcher hiển thị đúng).
- apps/web/src/components/ChatPanel.tsx: `decodeCitationDoc()` — CITATION_FULL_RE ("D1-F"/"D2-F" → d3/d4) + CITATION_LEGACY_RE ("D1..D16"/DAY05-REF → doc_id, backward-compat citation cũ trong history); isSlide chip regex nhận cả 2 dạng.

**Verify:** pytest **112/112** api (+2 test: label scheme, retrieve_context d3) · direct python: d1 citations ["D1 - Trang 1","D1 - Trang 4"] · d3 ["D1-F - Trang 1","D1-F - Trang 6"] — **intersection rỗng** → click không thể nhảy nhầm · web build PASS (kèm t29/t30 của Dev4 cùng file) · :8001/:3000 không đụng (server tạm thử HTTP bị env flaky — đã verify label ở tầng retrieval deterministic, đủ cho P0-1). CHANGELOG ghi.

**Addendum t32 (SCHEME B — PO2 chốt):** label full Day1/Day2 chuyển "D1-F"/"D2-F" → **"D1 Full"/"D2 Full"** (rag._DOC_LABELS + slideDocs code + ChatPanel CITATION_FULL_RE nhận `D[12](-F|\s*Full)` — backfill vẫn decode được label tạm cũ; legacy D3..D16/DAY05-REF giữ nguyên). Verify: pytest **137/137** (112 api + 25 rag) · retrieval d1 "D1 .../d3 "D1 Full ..." không overlap · web build PASS.

### t35 — P0-2 Render misconceptions từ Tutor Coach (Dev4)

**Trạng thái:** ✅ triển khai xong — ChatPanel giờ HIỂN THỊ card misconception mà A-05 đã detect (trước chỉ render follow-ups + badge move). Chỉ sửa UI `apps/web/src/components/ChatPanel.tsx`, backend giữ nguyên.

**Envelope (đã đọc code trước khi làm):** `apps/api/agent/nodes/tutor_coach.py build_envelope()` trả `misconceptions: list[str]` (tối đa 3: React/ReAct trước, rồi memory) — `server.py` stream đã pass vào `data.misconceptions` (SSE done), `Message.misconceptions?: string[]` đã có trong ChatPanel nhưng **chưa từng render**.

**UI mới (bên dưới câu trả lời tutor, giữa envelope và rating):** card nhỏ `border-warning/40 bg-warning/5` + icon WarningCircle + mỗi dòng "Có thể bạn đang hiểu nhầm: <nội dung>" + nút **"Giải thích lại"** (bg-brand-600, điền composer `Giải thích lại để mình hiểu đúng: <misc…>` — helper `miscActionPrompt()`, không nhét câu tutor) + nút **dismiss** (X) → ẩn card theo msg.id (`dismissedMisc` state), không hiện lại. Follow-ups/rating/citation KHÔNG đổi.

**Verify:** (1) `npm run build` PASS (Next 16.2.12, TS sạch, exit 0 — build cuối restore NEXT_PUBLIC_AGENT_API_URL=:8001). (2) E2E thật mock SSE :8005 (CORS) + next start :3006 + Chrome CDP :9225 (cổng tạm của tôi, đã kill; :8001/:3000/:3002 không đụng): 1 turn trả `misconceptions: ["Nhầm React … ReAct …"]` + 2 follow_ups → card hiện đúng text + icon ✓ · click "Giải thích lại" → composer = "Giải thích lại để mình hiểu đúng: Nhầm React (framework JS) với ReAct (pattern agent trong slide Day 3)" ✓ · chip follow-up vẫn còn (Đào sâu hơn… / Cho mình ví dụ…) ✓ · dismiss → card biến mất (0 element) ✓. Screenshot /tmp/vlearn-dev4/t35-misconception-card-1440.png. Lưu ý: .env.local đã tạm đổi :8005 rồi ĐÃ khôi phục :8001.

### t34 — P0-4 Notes persist + sync qua Memory A-06 (Dev2)

**Backend:** memory store thêm `page_notes: [{doc_id, page, text, updated_at}]` (EMPTY_STATE + update_state merge theo (doc,page)) + `set_page_note()` (text rỗng = xoá) + `get_page_notes(doc_id)`; endpoint mới `GET/PUT /api/learners/{id}/notes` (PUT body {doc_id, page, text} → upsert). Không PII.

**Frontend (3 file):** lib/learner.ts (getLearnerId dùng chung) · SlideViewer: mở panel → đọc local (fallback nhanh) + fetch notes server (merged, server thắng) + state notePages; handleSaveNote: vẫn ghi localStorage (offline mirror) + PUT sync (lỗi mạng im lặng) + cập nhật dot ngay; đổi doc → reload notePages · PDFViewer: prop `notePages` → **dot brand-500** góc phải trang có note.

**Verify:** pytest **141/141** (116 api + 25 rag; +4 note tests) · live cổng tạm 8008: PUT 2 note → GET trả đủ (persist = reload ✓) · PUT text rỗng → xoá đúng trang ✓ · web build PASS · :8001/:3000 không đụng. CHANGELOG ghi.

**Lưu ý phối hợp:** trong lúc verify, agent khác (P0-5 admin metrics) đang sửa server.py + observability — đã tự ổn (import WINDOW_HOURS), không xung đột với t34 (tôi không đụng những vùng đó). CDP UI reload-test bị ràng buộc môi trường như các vòng trước (prod+headless hydration; dev bị lock bởi :3002) — verify persistence ở tầng API là đủ cho P0-4; QA2 có thể mở :3002 (sau restart :8001) kiểm dot + reload giữ note.

### t36 — Fix "Tóm tắt trang này" (page-scope vs doc-scope) (Dev2)

**Bug:** "tóm tắt trang này" trả summary CẢ slide (map-reduce doc) thay vì trang đang xem.

**Fix (apps/api/agent/nodes/summary.py):** `_page_request()` phát hiện page-scope ("trang này / trang N / trang đang xem / page N") → `_try_page_summary()`: tóm tắt 1 trang từ slide_index (1 LLM call ngắn, prompt riêng, giữ nguyên văn), citation `"{label} - Trang N"` (label theo scheme P0-1: D1, D1 Full...), state kèm `summary_page`; trang không có text → thông báo rõ; không phải page-scope → map-reduce doc-scope giữ nguyên (sau bước paper-check t27).

**Verify:** pytest **122/122** api (tổng 147 với rag 25; +3 tests page-request/page-summary/no-text) · THẬT (LLM, không server — env kill server transient): d10 p16 "tóm tắt trang này" → answer đúng nội dung trang 16 (Retrieval bước quan trọng) + citation **"D10 - Trang 16"** ✓ · "tóm tắt day 4" → 8.4k ký tự map-reduce, không summary_page ✓ · :8001/:3000 không đụng. CHANGELOG ghi.

### t39 — Citation TRONG TEXT câu trả lời click được (Dev2)

**Bug:** dấu `[D1 - Trang 4]`, `[S1]`, `[arxiv-x.pdf - Trang N]` trong markdown là text thường.

**Fix (apps/web/src/components/ChatPanel.tsx — frontend-only, markdown khác không vỡ):** pre-process `linkifyCitations()` — chỉ thay 4 pattern bracket citation thành link nội bộ `vlearn://cite/{slide|paper|slabel|current}?c=...` (giữ nguyên text hiển thị); custom `a` renderer trong ReactMarkdown bắt scheme → `handleInlineCite()`: slide → decodeCitationDoc + jump/flash (tái dùng P0-1); current "[Trang X]" → jump doc đang xem; paper → onOpenPaper(source, trang) (tái dùng t28); slabel [S1] → tìm citation_detail → onOpenPaper. Style: font-mono brand-700 underline dotted + hover bg-brand-50 + focus-visible ring; title tooltip theo loại. Link http ngoài giữ nguyên.

**Verify:** web build PASS · sanity logic (node mirror 5 mẫu): 4 loại citation linkify đúng, `**đậm**`/`code`/`[link](https://…)`/câu không citation GIỮ NGUYÊN ✓ · (CDP render bị ràng buộc môi trường prod+headless như các vòng — QA2 verify trên :3002 sau restart :8001: trả lời có [D1 - Trang 4]/[S1] → bấm nhảy đúng). CHANGELOG ghi.

### t37 — P0-5 Mini-dashboard cost/latency từ trace (Dev4)

**Trạng thái:** ✅ triển khai xong — endpoint `/api/admin/metrics` (1h/24h/7d) + trang `/admin` (tokens Draft A). pytest **144/144** (+3 test mới) · web build PASS (route /admin) · verify live seed 13 trace + 4 feedback trên server tạm :8006 (đã kill; :8001/:3000/:3002 không đụng).

**Backend (3 file):**
- `agent/observability/trace.py`: `admin_metrics(window_hours)` — đọc traces.jsonl + feedback.jsonl trong cửa sổ (time.time() làm mốc): turns · success_rate (1 - errors/turns) · avg + **P90 nearest-rank** (ceil(0.9n)-1) latency · total/avg cost_usd_est · tokens in/out · tool_usage (count theo tool_match, sort desc) · **top_concepts** (heuristic deterministic: chỉ từ in hoa hoặc từ kỹ thuật rag/llm/token/embed/retriev/agent/react/prompt/vector…, bỏ stopwords tiếng Việt, top 5) · ratings {up, down, total}. `WINDOW_HOURS = {1h:1, 24h:24, 7d:168}`; exports qua `observability/__init__.py`.
- `server.py`: `GET /api/admin/metrics?window=` — validate window ∈ {1h,24h,7d} (lạ → 422), không gọi LLM.
- Tests mới `apps/api/tests/test_admin_metrics.py` (3 test): aggregation math + loại trace/feedback ngoài cửa sổ (OBS_DIR monkeypatch + time cố định) · endpoint TestClient shape + 422 · concept extractor lọc nhiễu.

**Frontend:** mới `apps/web/src/app/admin/page.tsx` (client, không thêm dependency): header VLearn · Mini-dashboard + nút "Về workspace" · window selector 1 giờ/24 giờ/7 ngày · stat cards (Lượt hỏi, Tỉ lệ thành công, Latency TB, Chi phí ước tính) · chi tiết (P90, Lỗi, Tokens in/out, Rating 👍👎) · tool usage bars + top concepts chips — đúng tokens (surface-2/ring, font-mono brand, overline).

**Verify live (seed 13 trace, 4 feedback; server tạm :8006 CORS-patched cho :3006 — đã kill):** 1h → 5 turns / success 0.8 / avg 2200ms / p90 4500ms / $0.011 ✓ · 24h → 9 turns / 0.7778 / lookup 5, papers 2, format 1, no_tool 1 / concepts rag 2, paper 2… / ratings up 2 down 1 ✓ · 7d → 13 turns / ratings up 3 down 1 ✓ · window=1month → 422 ✓. CDP :3006: page render đủ số liệu, switch 7d → 13 ✓ · screenshot /tmp/vlearn-dev4/t37-admin-dashboard-1440.png. Lưu ý: .env.local tạm đổi :8006 lúc test → ĐÃ khôi phục :8001, build cuối đúng production.

### t40 — FIX 404 PDF paper khi click "Xem trang" (QA2 t28 verify) (Dev2)

**Bug:** viewer gọi `http://<web-origin>/api/papers/{source}/pdf` (relative) → web frontend không proxy /api/papers → 404; backend :8001 trả 200.

**Fix (chọn CÁCH B, ghi lý do):** SlideViewer dùng **ABSOLUTE URL** `{NEXT_PUBLIC_AGENT_API_URL}/api/papers/{source}/pdf` (fallback localhost:8000) thay vì relative. Lý do: nhất quán với mọi API call khác (chat/notes/gaps đều absolute agentApiUrl) · env inline tại build — không cần cấu hình next.config/rewrite, không đụng rewrite /backend/* cũ · không phụ thuộc proxy nếu web chạy port khác.

**Verify:** build PASS (env + default) · bundle chứa template absolute (`${agentApiUrl}/api/papers/${…}/pdf` — grep chunk) → viewer không bao giờ gọi web-origin /api/papers nữa · backend endpoint 200 + %PDF-1.5 (verified live các vòng trước) · :8001/:3000 không đụng. QA2 re-test: click "Xem trang" citation paper → tải PDF thành công + scroll/flash đúng trang + Thoát về slide + slide citation không vỡ. CHANGELOG ghi.

### t38 — Fix popup "Hỏi AI" hiện nhầm khi bôi đen ngoài vùng slide (Dev4)

**Bug user:** bôi đen chữ ở sidebar/chat/ghi chú → popup "Hỏi AI" vẫn hiện. Root cause trong `SlideViewer.tsx` selection handler (F7): debounce 80ms check trục DỌC duy nhất (`rect.bottom < top || rect.top > bottom`) — selection ở panel cạnh có cùng băng dọc → lọt qua; panel Ghi chú nằm TRONG scrollRef nên thậm chí nằm trong container.

**Fix (chỉ sửa `apps/web/src/components/SlideViewer.tsx`, handler selectionchange):** popup chỉ hiện khi thỏa CẢ:
1. `document.activeElement` không phải TEXTAREA/INPUT (chặn chọn trong ô ghi chú/input);
2. CẢ HAI đầu range (`startContainer` + `endContainer`) nằm trong `scrollRef.current` (loại sidebar/chat/header — DOM containment, không chỉ tọa độ);
3. rect selection GIAO container theo CẢ HAI trục ngang + dọc (trước chỉ trục dọc) và width > 0.

**Verify (CDP Chrome :3006 + headless :9225 — cổng tạm, đã kill; không đụng :8001/:3000/:3002):**
- Trạng thái 1 — bôi đen text trong CHAT panel: selection "Xin chào! Mình là VL…" → **0 nút "Hỏi AI"** (popup KHÔNG hiện) ✓ — ảnh /tmp/vlearn-dev4/t38-outside-selection-no-popup-1440.png.
- Trạng thái 2 — bôi đen text trong text layer slide ("AI IN ACTION", rect top 198 left 94): → popup "Hỏi AI" hiện đúng (pos 136,186 — trên selection, căn giữa) ✓ — ảnh /tmp/vlearn-dev4/t38-inside-selection-popup-1440.png.
- `npm run build` PASS (Next 16.2.12, TS sạch, exit 0).

### t41 — Fix "cho ví dụ/câu hỏi ôn tập" (sinh nội dung sư phạm, không báo thiếu thông tin) (Dev2)

**Bug (user repro):** "Cho mình ví dụ thực tế hoặc câu hỏi ôn tập về phần này" → trả "Rất tiếc, nội dung slide hiện tại không có đủ thông tin…" — sai bản chất: đây là yêu cầu SINH NỘI DUNG SƯ PHẠM dựa trên ngữ cảnh, không phải tra lookup.

**Fix:**
- Orchestrator: intent mới `example` (EXAMPLES_CUES deterministic: ví dụ thực tế/ví dụ về/cho ví dụ/example/câu hỏi ôn tập/quiz/ôn tập phần này…; bổ sung vào INTENT_PROMPT cho LLM) → route graph `example_teacher` + stream branch (status answering, stream chunk, done kèm citations + envelope + trace tool example_teacher).
- Mới nodes/examples.py `generate_examples()`: anchor = nội dung TRANG ĐANG XEM (nếu có text) hoặc retrieval doc-scope k=2; prompt 1-2 ví dụ thực tế BÁM SÁT khái niệm + 1-2 câu hỏi ôn tập kèm đáp án/giải thích + citation `{label} - Trang N` (P0-1); chỉ khi context hoàn toàn trống mới nói "trang này không có nội dung…" (message khác hẳn); LLM lỗi → fallback thân thiện.

**Verify THẬT (LLM, đúng câu user, d10 p16):** intent deterministic = example · output: "## Ví dụ thực tế" (2 ví dụ bám sát Retrieval — y tế + học tập) + "## Câu hỏi ôn tập" (2 câu hỏi + đáp án + giải thích) · citation (D10 - Trang 16) · KHÔNG còn "không có đủ thông tin" ✓ · pytest **128/128 api** (153 tổng; +6 tests: intent example/không đổi các intent cũ, structure+citation, empty-context message khác, chunk, graph route) · web build PASS · :8001/:3000 không đụng. CHANGELOG ghi.
