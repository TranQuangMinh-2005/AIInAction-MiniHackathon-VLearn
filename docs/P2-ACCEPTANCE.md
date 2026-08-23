# P2-ACCEPTANCE.md — Tiêu chí nghiệm thu PHASE 2 (PO, 24/08)

> **Nguồn:** AGENT-UPGRADE-PLAN.md §3/P2 + §4 (lộ trình & tiêu chí chung). User đã duyệt 10 mục A-01→A-08, A-10, A-11 (bỏ A-09). P2 gồm: **A-05 · A-06 · A-07 (phần còn lại) · A-08**.
> **2 quyết định user đã chốt cho P2:** ① Tutor Coach **chỉ kèm câu check hiểu khi learner có dấu hiệu khó/lặp câu hỏi** (không luôn kèm); ② Memory **anonymous per-browser** (không cần login).

---

## Tiêu chí nghiệm thu CHUNG (mọi mục P2 — kế thừa plan §4)

1. **Không phá golden set 24 case** (eval gate t16 đã có: `src/eval/gate_run.py`, TC01–TC24) — regress <87.5% (21/24) = chặn, phải có giải trình.
2. **Backward-compatible:** API contract cũ + frontend cũ vẫn chạy (SSE event lạ bị bỏ qua, envelope thiếu trường không vỡ render).
3. UI đụng frontend phải theo **DESIGN.md v3** tokens (1 accent navy, Geist, radius/shadow/motion chuẩn).
4. Mỗi mục có **≥5 câu test mẫu từ chatlog thật** + kết quả PASS/FAIL ghi vào `../validation/`.

---

## A-05 — Tutor Coach Agent · Effort L (1.5–2 ngày)

**Phạm vi:** node `tutor_coach.py` (mới) soạn câu trả lời cuối theo envelope;
`state.py` (envelope); `server.py` (gửi envelope trong SSE done); `ChatPanel.tsx` (render follow-up chips + badge move — tái dùng pattern empty-state chip).

**Envelope bắt buộc đủ 5 trường:** `answer` · `move` (review_concept/give_example/give_hint/validate/…) · `misconceptions[]` · `follow_ups[]` (2–3 câu) · `asked_check_question` (bool — mặc định **false**, chỉ true khi: learner lặp câu hỏi, trả lời sai/bối rối, hoặc dấu hiệu nhầm lẫn; KHÔNG gắn tự động mỗi turn).

**Acceptance (từ plan "XONG KHI" + quyết định user):**
1. **Conv C0128 mô phỏng:** user hỏi "React là gì" (trong ngữ cảnh AI khóa học) → coach ghi nhận misconception nhầm React/ReAct + gợi ý: "Bạn có định hỏi ReAct pattern trong slide Day 3?" (follow-up click được).
2. Envelope đủ 5 trường ở **mọi turn** (miss = FAIL), giá trị hợp lệ theo enum move.
3. **5 turn mẫu có follow_up hiển thị + click được** trên UI (click → điền vào composer, không gửi ngay).
4. Check hiểu: **tối đa khi turn không có dấu hiệu khó** — driver script 10 turn mẫu (5 bình thường + 5 khó/lặp): 0/5 turn thường có asked_check_question=true; ≥3/5 turn khó có.
5. Không phá luồng Normal/Research hiện có (golden gate + regression t5-style).

**Đụng file hints:** `nodes/tutor_coach.py`, `state.py`, `server.py`, `ChatPanel.tsx`, `../validation/*.md`.

---

## A-06 — Memory Agent · Effort M (1 ngày)

**Phạm vi:** `agent/memory/` (store.py + schema); `server.py` (2 endpoint `GET/PUT /api/learners/{learner_id}/state`); các node đọc context từ memory (thay 5 msg × 150 ký tự); `ChatPanel.tsx` (sinh + gửi learner_id).

**Quyết định user:** **anonymous per-browser** — learner_id = token ngẫu nhiên sinh ở client (localStorage), gửi kèm mỗi request; KHÔNG lưu thông tin nhận dạng/nội dung nhạy; migration login sau này = thêm cột, không phá.

**Dữ liệu lưu (có cấu trúc):** doc đang học · trang đã xem · khái niệm đã hỏi (+ lần hỏi) · misconception đã sửa · notes · câu hỏi lặp.

**Acceptance (từ plan "XONG KHI"):**
1. **Reload/tắt trình duyệt mở lại** → vẫn nhớ khái niệm đã hỏi hôm trước (cùng browser); context turn sau dùng memory thay vì cắt lịch sử.
2. **Script 3 turn liên tiếp** (trong đó câu 2 trùng câu 1): turn 3 không lặp lại nội dung y hệt — hệ thống nhận diện "đã trả lời" và đi sâu hoặc nhắc lại ngắn + hỏi hướng tiếp.
3. Endpoint: `PUT` upsert + `GET` trả state JSON; sai learner_id → state rỗng (không crash); không lưu nội dung ngoài schema đã định.
4. Golden gate không giảm (không đổi hành vi trả lời khi memory rỗng).

**Đụng file hints:** `agent/memory/store.py`, `server.py`, `nodes/*` (context assembly), `state.py`, `ChatPanel.tsx` (token), `../validation/`.

---

## A-07 — Eval & Observability (phần còn lại sau t16) · Effort M

**Đã có (t16):** eval gate golden set 24 case (`src/eval/gate_run.py`, TC01–TC24, DRY/REAL mode; REAL cần API key thật).

**Còn lại:** middleware trace node (latency/tokens in/out/cost/lỗi) · log mỗi turn đủ 3 classification · rating UI 👍👎 dưới câu trả lời · endpoint `/api/feedback`.

**Acceptance:**
1. Mỗi turn có 1 dòng log `{latency_ms, tokens_in, tokens_out, cost_usd}` (cost không còn = 0).
2. Rating 👍👎 hiển thị dưới mọi câu trả lời tutor (DESIGN.md tokens), gửi kèm trace_id về `/api/feedback`, lưu được.
3. `gate_run.py --real` chạy được với key thật → **≥21/24 PASS** (87.5%).
4. Trace không làm chậm turn đáng kể (<50ms overhead) và không phá SSE stream.

---

## A-08 — Research Scholar hoàn chỉnh · Effort M (1–1.5 ngày)

**Phạm vi:** research thành subgraph chuẩn (bỏ nhánh cứng server.py); cache query_hash → paper chọn; tránh download lại paper đã index (theo arxiv-id); timeout + song song arXiv + DDG fallback; tái sinh web search Tavily (tùy chọn key, không có → DDG); giữ grounding audit.

**Acceptance (từ plan "XONG KHI"):**
1. Hỏi lặp cùng chủ đề 2 lần → lần 2 **không gọi lại arXiv API** (verify qua log cache hit).
2. Research P90 < 12s (đo 10 turn mẫu, cùng chủ đề đã cache → nhanh hơn nữa).
3. 5 câu research mẫu vẫn **grounded** (grounding audit giữ nguyên, claim→quote khớp).
4. Không phá golden gate; API contract cũ vẫn chạy.

---

## Nhắc P2 mục tiêu tổng (plan §4)

- follow_ups & misconceptions xuất hiện **≥80% turn mẫu** (trên 20 câu mẫu chatlog).
- Golden set **≥21/24** → gate mở.
- Mỗi turn có **trace đầy đủ** (A-07).
- P1 mục tiêu cũ: fail rate câu mẫu <15% (từ 30.5%) — xem như điều kiện nền trước khi vào P2.

*Soạn: PO2 · dùng làm checklist nghiệm thu khi Dev2 báo xong từng mục P2; kết quả → báo cáo user vòng 2.*