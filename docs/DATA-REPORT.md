# DATA-REPORT — 15 slide bài giảng → data app VLearn

**Người thực hiện:** Data2 · **Task:** t9
**Trạng thái:** ✅ Hoàn tất — 15 PDF đã copy vào `src/frontend/public/`, index `rag.py` + `slideDocs.ts` đã đăng ký, module import PASS.

---

## 1. Bảng 15 file: nguồn → đích → số trang → text

| # | File nguồn (~/Downloads) | File đích (public/) | Số trang | Text extract |
|---|---|---|---|---|
| 1 | `Day01_AI&LLM-Model (1).pdf` | `day01_ai-llm-model.pdf` | 78 | ✅ OK (78/78 trang) |
| 2 | `Day02_Xac-bai-toan-AI (2).pdf` | `day02_xac-dinh-bai-toan-ai.pdf` | 57 | ✅ OK (57/57) |
| 3 | `Day03_Design-Pattern-ReAct (2).pdf` | `day03-design-pattern-react.pdf` | 71 | ⚠️ **SCAN-heavy — cần OCR** (chỉ 8/71 trang có text: p2,3,13,17,18,27,42,45; 66 trang ảnh) |
| 4 | `Day04_prompt-engineering-tool-calling (2).pdf` | `day04-prompt-engineering-tool-calling.pdf` | 132 | ✅ OK (132/132) |
| 5 | `Day05-lecture-slides-v2.pdf` | `day05-lecture-slides.pdf` | 52 | ✅ OK (50/52 text) |
| 6 | `Day05-reference-document.pdf` | `day05-reference-document.pdf` | 8 | ✅ OK (8/8) |
| 7 | `day06-lecture-slides.pdf` | `day06-lecture-slides.pdf` | 20 | ✅ OK (20/20) |
| 8 | `day07-lecture-slides.pdf` | `day07-lecture-slides.pdf` | 49 | ✅ OK (49/49) |
| 9 | `day08-rag-pipeline-v2.pdf` | `day08-rag-pipeline.pdf` | 53 | ✅ OK (53/53) |
| 10 | `day09-multi-agent-mcp-a2a-v3.pdf` | `day09-multi-agent-mcp-a2a.pdf` | 79 | ✅ OK (79/79) |
| 11 | `Day10 Data Pipeline and Data Observability.pdf` | `day10-data-pipeline-observability.pdf` | 46 | ✅ OK (46/46) |
| 12 | `day11-guardrails-ai-safety_E403_v2_linh.pdf` | `day11-guardrails-ai-safety.pdf` | 60 | ✅ OK (60/60) |
| 13 | `day13-monitoring-logging-observability.pdf` | `day13-monitoring-logging-observability.pdf` | 78 | ✅ OK (78/78) |
| 14 | `day14-ai-evaluation-benchmarking-v2.pdf` | `day14-ai-evaluation-benchmarking.pdf` | 115 | ✅ OK (115/115) |
| 15 | `day15-trien-khai-thuc-te-dinh-huong.pdf` | `day15-trien-khai-thuc-te.pdf` | 35 | ✅ OK (35/35) |

> `d1-slide-hackathon.pdf` / `d2-slide-hackathon.pdf` hiện có **không bị đè** (đã kiểm tra trước/sau).

---

## 2. Mapping doc_id (rag.py `PDF_FILES` ↔ `slideDocs.ts` id ↔ Sidebar code)

| doc_id (rag.py) | PDF | Code Sidebar | Title (sidebar) |
|---|---|---|---|
| `d3` | `day01_ai-llm-model.pdf` | D01 | Day 1 — AI & LLM: Nền tảng mô hình ngôn ngữ (bản full) |
| `d4` | `day02_xac-dinh-bai-toan-ai.pdf` | D02 | Day 2 — Xác định bài toán cho AI (bản full) |
| `d5` | `day03-design-pattern-react.pdf` | D03 | Day 3 — Design Pattern & ReAct cho Agent |
| `d6` | `day04-prompt-engineering-tool-calling.pdf` | D04 | Day 4 — Prompt Engineering & Tool Calling |
| `d7` | `day05-lecture-slides.pdf` | D05 | Day 5 — Thiết kế sản phẩm AI cho sự không chắc chắn |
| `day05-ref` | `day05-reference-document.pdf` | D05R | Day 5 — Tài liệu tham khảo: Thiết kế sản phẩm AI |
| `d8` | `day06-lecture-slides.pdf` | D06 | Day 6 — Hackathon: SPEC → Prototype → Demo |
| `d9` | `day07-lecture-slides.pdf` | D07 | Day 7 — Data Foundations: Embedding & Vector Store |
| `d10` | `day08-rag-pipeline.pdf` | D08 | Day 8 — RAG Pipeline |
| `d11` | `day09-multi-agent-mcp-a2a.pdf` | D09 | Day 9 — Multi-Agent, MCP & A2A |
| `d12` | `day10-data-pipeline-observability.pdf` | D10 | Day 10 — Data Pipeline & Data Observability |
| `d13` | `day11-guardrails-ai-safety.pdf` | D11 | Day 11 — Guardrails & AI Safety |
| `d14` | `day13-monitoring-logging-observability.pdf` | D13 | Day 13 — Monitoring, Logging & Observability |
| `d15` | `day14-ai-evaluation-benchmarking.pdf` | D14 | Day 14 — AI Evaluation & Benchmarking |
| `d16` | `day15-trien-khai-thuc-te.pdf` | D15 | Day 15 — Triển khai thực tế, chi phí & định hướng |

## 3. Kiểm chứng index

```bash
PYTHONPATH=src/agent:codebase/rag/src python3 -c "from agent.rag import slide_index; slide_index.load(); print(len(slide_index.page_texts))"
# → 926 page texts (17 doc_ids: d1..d16 + day05-ref; trước đây chỉ 58 = d1+d2)
```

- retrieve/retrieve_context chạy OK (BM25, không cần backend/embedding).
- `slideDocs.ts` là nguồn duy nhất mà `Sidebar.tsx` + `SlideViewer.tsx` import (`slideDocuments`) → đã cập nhật tại đó (không sửa trực tiếp Sidebar.tsx vì nó chỉ render từ array này).

## 4. Ghi chú bất thường

1. **day03 là bản scan** — 66/71 trang là ảnh, chỉ 8 trang text (hoạt động nhóm/discord). Index chỉ có 8 trang text cho d5. Nếu cần RAG đầy đủ cho Day 3 → cần OCR (vd. OCRmyPDF) trước khi load index.
2. **Số doc_id vượt dự kiến**: task ghi "d3..d15" (13 slot) nhưng có 15 file → đã dùng **d3..d16** + `day05-ref` (đủ 15), giữ thứ tự ngày. Day01/Day02 là bản full (78/57 trang) — trùng nội dung với d1/d2-slide-hackathon (29 trang) nhưng được giữ làm tài liệu riêng đúng yêu cầu.
3. Day05 có 2 tài liệu: slide bài giảng (52 trang, d7) + reference doc (8 trang, `day05-ref`) — code sidebar D05 / D05R.
4. Không có slide Day12 trong danh sách user tải (ngày 12 không có file) — không thêm.
5. CHƯA build / CHƯA restart backend :8001 — đúng yêu cầu, captain sẽ rebuild + restart.
6. pypdf 6.14.2 dùng sẵn trên máy, không thêm dependency.
7. **Fix integration nhỏ (2 chỗ, không build):**
   - `page.tsx`: `handleJumpToDocPage` trước đây hardcode d1/d2 (29 trang) → giờ tra `slideDocuments` theo docId, đúng path + số trang cho cả 17 tài liệu (trước đây click citation tới d3..d16 sẽ mở nhầm d2).
   - `ChatPanel.tsx`: regex citation `(D\d)` chỉ khớp 1 chữ số → mở rộng `(D\d{1,2}|DAY05-REF)` để D10–D16 và DAY05-REF nhảy đúng tài liệu.
   - Cả 2 chỉ là thay đổi dữ liệu/ánh xạ doc, không đụng logic stream hay UI shell.