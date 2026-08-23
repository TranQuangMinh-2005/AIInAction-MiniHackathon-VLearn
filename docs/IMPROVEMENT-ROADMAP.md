# IMPROVEMENT-ROADMAP — VLearn Research Tutor

> **Tác giả:** Captain (dựa trên research web 2025–2026 + rà soát thực trạng repo) · **Ngày:** 23/08
> **Trạng thái:** Đề xuất — chờ user duyệt từng mục

---

## 0. Tóm tắt 30 giây

Dự án đã đạt nền rất tốt: multi-agent 11 mục xong, gate 20/20, refactor monorepo, docs/ hoàn chỉnh.
Các cải tiến còn lại được chia 3 nhóm ưu tiên:

- **P0 — Vá lỗ hổng đã biết (rẻ, làm ngay):** mã doc trùng D01/D02 · render misconceptions · CI GitHub Actions · notes persist · mini-dashboard cost/latency từ trace
- **P1 — Hardening production (chuẩn ngành 2026):** observability đúng chuẩn (Langfuse/OTel hoặc nâng trace hiện có) · rate-limiting + audit log + key rotation · model routing 2 tầng (flash cho retrieval / pro cho soạn thảo) · online evals (production → eval loop)
- **P2 — Giá trị sư phạm (edtech):** quiz cuối buổi · teacher/TA dashboard (bản đồ lỗ hổng lớp) · scaffolding/Socratic hints · multimodal (ảnh/minh hoạ) · xác thực fail-rate <15% bằng sample thật

---

## 1. P0 — Vá lỗ hổng đã biết (effort: S–M, 1–2 ngày)

| # | Mục | Lý do | Chi tiết |
|---|---|---|---|
| P0-1 | **Dedupe mã doc D01/D02** | Citation có thể nhảy nhầm doc (QA2 m-QA1, QC ghi nhận) | d1 (short) vs d3 (full Day1) cùng label D1 → thêm suffix/đổi label citation theo tên doc thật; cập nhật jump-to-page |
| P0-2 | **ChatPanel render misconceptions** | Lưu ý P2 còn lại trong AGENT-UPGRADE-PLAN (dòng 460): Tutor Coach đã detect nhưng UI chưa hiển thị | Hiện card misconception khi Coach gắn cờ, kèm nút "Giải thích lại" |
| P0-3 | **CI GitHub Actions** | Mọi bài research về production agent đều nhấn: "automated testing, version control, CI/CD applied to every layer" (mlflow.org); repo chưa có pipeline | Workflow: on PR → pytest apps/api + libs/rag → next build → **gate REAL/DRY 20 case** (gate bar chặn merge) → report artifact |
| P0-4 | **Notes persist** | Ghi chú hiện là localStorage bản thô, chưa đồng bộ; QC ghi chú "Lưu ghi chú" mock trước đây | Đồng bộ notes vào memory JSON (A-06) theo learner_id → có trên mọi thiết bị cùng browser; export/import |
| P0-5 | **Mini-dashboard cost/latency** | Trace JSONL đã có latency/tokens/cost nhưng chưa có view | `GET /api/admin/metrics` (5 phút, 1 giờ, hôm nay: avg latency, total cost, success/tool-fail rate, top concepts) + trang admin đơn giản (có thể reuse analytics UI) |
| P0-6 | **E2E chat test với key thật thành test tự động** | QA3 để lại: chat E2E chưa chạy với key thật | Test script chạy 3-5 câu chuẩn qua API + verify citation tồn tại; chạy CI gate |
| P0-7 | Cosmetic backlog | QC2: 2 nút ghost "Thử lại" 11px thiếu active:scale | Fix 2 dòng |

## 2. P1 — Hardening production (effort: M–L, 3–7 ngày)

### 2.1 Observability đúng chuẩn (ưu tiên cao nhất theo research)
Nguồn: [LLM Observability Best Practices 2025 (Maxim)](https://www.getmaxim.ai/articles/llm-observability-best-practices-for-2025/) · [LLM Evaluation & AI Observability (JetBrains)](https://blog.jetbrains.com/pycharm/2026/05/llm-evaluation-and-ai-observability-for-agent-monitoring/) · [Building Production-Ready AI Agents (MLflow)](https://mlflow.org/articles/building-production-ready-ai-agents-in-2026/) · [9 LLM Observability Tools (LangChain)](https://www.langchain.com/resources/llm-observability-tools)

Điểm mạnh hiện có: trace JSONL (latency/tokens/cost/tool routing/trace_id), feedback JSONL, golden gate 20 case. Điểm thiếu:

| Mục | Hiện tại | Chuẩn ngành | Gợi ý |
|---|---|---|---|
| P1-1 | Trace file JSONL local | Distributed tracing chuẩn (OTel) + dashboard + alert | Tích hợp **Langfuse** (self-host/Python, open source) hoặc nâng trace hiện có thêm: session tree, tool args/results, score | 
| P1-2 | Chưa có | Đo liên tục: hallucination rate, drift, latency P50/P90/P99, cost/turn, error rate | Metric registry + alert ngưỡng (vd P90 > 45s → alert; cost/turn > $0.05 → alert) |
| P1-3 | Chưa có | **Online evaluation**: production traces → eval cases ("A production issue should become an eval case") | Script: trace có rating -1 hoặc tool-fail → tự đề xuất case vào golden set rồi con người duyệt |
| P1-4 | Manual test | Offline evals trước deploy + online evals trên live traffic | Gate đã có offline; thêm `LLM-as-judge` đánh giá chất lượng câu trả lời (faithfulness/helpfulness) trên 20 câu mẫu mỗi release |

### 2.2 Security hardening
Nguồn: [AI Agent Security (DigitalApplied, OWASP ASI Top 10 2026)](https://www.digitalapplied.com/blog/ai-agent-security-best-practices-2025) · [AI Agent Observability 2026 (Atlan)](https://atlan.com/know/ai-agent-observability/)

| Mục | Hiện tại | Cần làm |
|---|---|---|
| P1-5 | security.py regex + validate_input | **Rate limiting** (per IP/learner, vd 20 req/phút) — FastAPI middleware; **audit log** bất biến (mọi agent activity + who/when/what, ASI-02); CORS chỉ localhost dev |
| P1-6 | Key trong .env | **Quản lý key rota**: hỗ trợ env per-provider override, cảnh báo khi key sắp hết hạn/quota; không log key (verify trace không chứa secret) |
| P1-7 | Chưa kiểm tra | **PII check**: nhắc nhở prompt không đưa tên thật; kiểm tra trace/memory không lưu PII (đã ẩn danh đầu vào, verify đầu ra) |
| P1-8 | 0 | **OWASP ASI threat model**: prompt injection qua paper content (paper từ arXiv chứa prompt độc hại → không đưa raw vào LLM system prompt — hiện evidence vào user message, đánh giá mức rủi ro), cascading failures giữa các node (đã có retry một phần) |

### 2.3 Cost & latency (model routing)
Nguồn: [Fora Soft — AI teacher copilot reference architecture](https://www.forasoft.com/blog/article/ai-generated-educational-resources-teachers) · [MLflow key takeaway "cache intermediate reasoning, context window budgets, monitor tokens per step"](https://mlflow.org/articles/building-production-ready-ai-agents-in-2026/)

| Mục | Mô tả |
|---|---|
| P1-9 | **Route retrieval/classify → flash model** (gemini-flash hoặc gpt-4o-mini), **final drafting → model tốt hơn** (khả năng đã có: GGEMINI_FALLBACK; tạo `RAG_DRAFT_MODEL` env + build_chat_model hỗ trợ 2 tầng) |
| P1-10 | Context budget per node: cap slide context per turn (đã k=3), cap history (đã 4 msg), thêm token budget cho research evidence |
| P1-11 | Cache mở rộng: cache summary theo (doc_id, mtime) đã có; thêm cache embedding query cho câu lặp (lru) |

### 2.4 Kiến trúc hoàn thiện
| Mục | Mô tả |
|---|---|
| P1-12 | Tách `server.py` → `api/routers/*` theo [fastapi-best-practices](https://github.com/zhanymkanov/fastapi-best-practices) (đã ghi nhận lệch ở t20, làm vòng sau khi demo xong) |
| P1-13 | Version hoá API (prefix /v1) khi có consumer bên ngoài; hiện giữ ổn định contract |

## 3. P2 — Giá trị sư phạm & sản phẩm (effort: M–L)

Nguồn: [AI Tutors in Higher Education Guide (LearnWise)](https://www.learnwise.ai/guides/ai-tutors-in-higher-education-the-complete-institutional-guide-2025) · [Training Specialist AI Tutors (Medium)](https://medium.com/@gwrx2005/training-specialist-ai-tutors-integrating-pedagogy-model-design-and-industry-insights-bdaf22ab4d31) · Khanmigo (Khan Academy dataset)

| # | Mục | Giá trị | Ghi chú |
|---|---|---|---|
| P2-1 | **Quiz kiểm tra hiểu cuối buổi** (đề bài gợi ý!) | Đo hiểu thật; tạo ôn tập chủ động | Sinh 5 câu trắc nghiệm từ slide/transcript theo Bloom's taxonomy, chấm điểm + giải thích + nối misconceptions; lưu vào gaps |
| P2-2 | **Teacher/TA dashboard** (bản đồ lỗ hổng lớp) | Insight cho giảng viên: "nhiều học viên kẹt ở khái niệm X" (LearnWise: Westminster insight vào student behavior) | Aggregate from gaps/traces (ẩn danh): top concepts khó, top câu fail, rating distribution |
| P2-3 | **Scaffolding / Socratic hints** | Không đưa đáp án ngay — hướng dẫn từng bước (Khanmigo pattern, best practice edtech: "avoid simply giving answers") | Mode "Hướng dẫn" cho câu hỏi bài tập: hint 1 → hint 2 → đáp án |
| P2-4 | **Xác thực fail-rate <15%** | Mục tiêu P1 trong plan chưa được đo | Chạy 20 câu fail mẫu từ chatlog trên hệ mới → bảng so sánh trước/sau; lưu validation/ |
| P2-5 | **Multimodal** | Học viên chụp ảnh code/đoạn sách hỏi AI | Upload ảnh → OCR/vision → vào graph research |
| P2-6 | **Personalization sâu hơn** | Memory đã có; thêm thích ứng level | Điều chỉnh độ sâu giải thích theo learner lịch sử (câu trả lời ngắn/dài) |
| P2-7 | **Dark mode + i18n** | UX (đã để P2 từ đầu) | Tailwind dark variant + tokens; i18n tiếng Việt/English |
| P2-8 | **Logistics KB (A-09)** | Trả lời deadline/bài tập đúng nguồn | Cần user cấp dữ liệu chính thức — **bỏ khi không có** (quyết định cũ) |

## 4. Các mục không nên làm (theo research)

| Mục | Lý do |
|---|---|
| Fine-tune model riêng | Chi phí cao, data ít; nghiên cứu cho thấy tinh chỉnh data dialogue tốt, nhưng đợi khi có hàng nghìn turn thật (hackathon chưa đủ) |
| Rewrite PDF day03 | Sidecar đã đủ tốt — keep viewer ổn định |
| Vector DB riêng (Qdrant/pgvector) | SQLite + 989 trang là đủ tải; migrate khi >10k chunks |
| Multi-tenant/auth đầy đủ | Ngoài phạm vi prototype; cần khi có user thật tập trung |

## 5. Tiêu chí duyệt (dùng như checklist)

Mỗi mục: ☐ CHỜ DUYỆT (user tick) → PO giao Dev → xong kèm test + CHANGELOG.

---

*Tham khảo chính: MLflow Agent Production 2026 · JetBrains LLM Eval/Observability · Maxim LLM Observability 2025 · LangChain observability tools · OWASP ASI Top 10 (2026.1) · LearnWise AI Tutors HE 2025 · Fora Soft teacher copilot · EdTechHub/WorldBank (teacher role) · arXiv 2503.06424 (tutor reward) · Khan Academy dataset*