# A-07 Gate REAL — phân tích tool-match sau t18 (Dev2)

> Gate: `src/eval/gate_run.py --real --api http://localhost:8002` (golden 24 case, gốc `benchmark_result_slide_tools_v1_20260731.md` — Lab Coach, gpt-4.1-mini).
> Kết quả cuối: **6/24 PASS · 18 FAIL · 0 TOOL_INFO_MISSING** (trace.tool đã expose — infrastructure A-07 hoạt động).

## 1. Tool routing đã expose (trước t18: 24/24 TOOL_INFO_MISSING)

- `trace.tool` = alias golden-vocabulary (mapping `observability/trace.py::_GOLDEN_TOOL_MAP`):
  `slide_search→lookup · web_search_arxiv→papers · web_search_tavily→fetch · summarize_doc→format · refuse_off_topic→no_tool · khác→giữ tên`.
- `trace.tools` = tool thật của hệ. `trace_id` trong /api/chat + SSE done + header `X-VLearn-Trace-Id`.

## 2. PASS (6/24): toàn bộ case thuộc skill HỆ THỰC SỰ CÓ

| Case | Expected | Actual (tool_match) |
|---|---|---|
| TC11 · TC17 · TC22 | papers | papers ✓ (route mới: normal + keyword "paper/bài báo/arxiv" → research path) |
| TC13 · TC18 · TC21 | lookup | lookup ✓ |

## 3. FAIL — phân loại trung thực (18 case)

| Nhóm | Case | Lý do không match (KHÔNG phải bug routing) |
|---|---|---|
| **Skill không tồn tại ở sản phẩm mới** (9) | TC04/TC14 social_search, TC05/TC15 timeline, TC06/TC16 policy, TC12/TC23 paper_text (đọc từ URL), TC24 send(confirmed) | Golden set là tool của sản phẩm CŨ (Lab Coach). Hệ vlearn-ux không có skill social/timeline/policy/đọc-URL/send — match trung thực là bất khả thi, không nên map giả |
| **news/lookup ngoài khóa học** (2) | TC01, TC10 ("xu hướng giá API 2026", "tin model mới trong tuần") | Orchestrator chặn off_topic (đúng chính sách khóa học) → no_tool ≠ lookup |
| **clarify** (2) | TC07, TC19 (chủ đề mơ hồ) | A-01 fallback CHỦ ĐÍCH: unclear → xử lý như slide (không hỏi lại) → lookup ≠ clarify |
| **no_tool/format** (3) | TC08, TC09, TC20 (soạn nháp/format dữ liệu) | Không có khái niệm draft/format-doc trong UX hỏi-đáp này → lookup/no_tool ≠ format |
| **fetch** (1) | TC03 ("Doc URL…") | arXiv thường CÓ paper khớp → papers ≠ fetch (web fallback chỉ chạy khi arXiv rỗng) |
| **Flaky LLM** (1) | TC02 (papers) | Probe lại độc lập: intent=deep, tool=papers, trả lời paper thật (nnterp…) — lần chạy gate bị LLM rewrite khác → arXiv rỗng → fetch. Không phải code bug |

## 4. Kết luận & khuyến nghị

- **Infrastructure A-07 đạt**: trace mỗi turn (latency/tokens/cost est) + tool routing + feedback JSONL; gate REAL chạy được, 0 missing.
- **21/24 gate bar KHÔNG đạt được trung thực** với golden này: 9 case dùng skill không tồn tại + 2 case chặn-chính-sách + 2 case fallback chủ đích → trần trung thực ≈ 6-7/24 (không phải regression — là khác biệt taxonomy sản phẩm).
- **Đề xuất (cần PO/captain quyết):** rebase golden set cho hệ vlearn-ux (20 case gắn intent/tool thật: lookup/papers/fetch/summary/refuse/clarify) ở vòng sau; giữ gate cũ làm "smoke tool-match" (không chặn).
- Kết quả gate đầy đủ: `src/eval/gate_results_20260823_0128.md` (runs trước: _0117/_0119).

## 5. QUYẾT ĐỊNH PO (24/08): REBASE golden set — ghi vào đây làm chuẩn chung

**Chốt: VIẾT GOLDEN SET MỚI theo taxonomy vlearn-ux — KHÔNG giữ gate cũ làm bar chặn.**

1. **Golden cũ (24 case Lab Coach)** → hạ cấp thành **smoke tool-match** (giữ chạy mỗi thay đổi graph, KHÔNG chặn release; ghi rõ giới hạn: 9 case skill không tồn tại + 2 policy + 2 fallback chủ đích → trần ~6-7/24). Lý do: dùng nó làm gate chặn sẽ ép "map giả" để đạt số — Dev2 đã đúng khi KHÔNG map giả; giữ role smoke để vẫn bắt lỗi infra (tool expose/missing).
2. **Golden mới** (làm vòng sau, không chặn): **20 case** bám hệ thật — mỗi case `{question (từ chatlog thật), expected_intent, expected_tool (lookup/papers/fetch/summarize/refuse/clarify), policy_ok}`; ≥5 câu mẫu mỗi nhóm tool; gate REAL chạy khi có key thật; **bar = 18/20 PASS (90%)** trở lên → mới chặn.
3. QA2 verify expected-tool bằng cách chạy probe độc lập (như TC02) trên ít nhất 5 case khó; ghi kết quả vào `validation/A-07-gate-vlearn-ux.md`.
4. Trước khi có golden mới, báo cáo user ghi thẳng: **gate cũ 6/24 = khác biệt taxonomy (KHÔNG regression) — hạ cấp smoke; golden mới là việc vòng sau**.

*PO2 — điều phối: giao QA2 khi captain mở task; không chặn t19 (landing) hay P3.*