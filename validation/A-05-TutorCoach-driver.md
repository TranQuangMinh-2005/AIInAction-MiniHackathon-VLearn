# A-05 Driver — Tutor Coach check-hiểu theo dấu hiệu khó (Dev2, t17)

> Backend: cổng tạm 8002 (đã kill sau đo) · LLM thật (OpenAI gpt-4o-mini) · driver: 10 turn (5 bình thường + 5 khó/lặp), mỗi turn gọi `/api/chat/stream` với `learner_id` riêng.

## Kết quả (rút gọn từ `/tmp/t17-driver.json`)

| # | Câu hỏi | Loại | asked_check_question | move | PASS/FAIL |
|---|---|---|---|---|---|
| 1 | RAG khác gì Fine-tuning? | normal | false | review_concept | ✅ |
| 2 | token là gì? | normal | false | review_concept | ✅ |
| 3 | attention mechanism giải thích | normal | false | review_concept | ✅ |
| 4 | vector store dùng để làm gì? | normal | false | review_concept | ✅ |
| 5 | prompt engineering là gì? | normal | false | review_concept | ✅ |
| 6 | **React là gì?** (Conv C0128) | hard | **true** | give_hint | ✅ |
| 7 | mình không hiểu RAG cho lắm, giải thích dễ hiểu hơn… | hard | **true** | give_hint | ✅ |
| 8 | giải thích lại lần nữa token là gì? | hard | **true** | give_hint | ✅ |
| 9 | chưa hiểu embedding là gì, nói rõ hơn | hard | **true** | give_hint | ✅ |
| 10 | (lặp lần 3) token là gì? | hard | **true** | give_hint | ✅ |

**Tổng kết:** normal = **0/5** true (acceptance: 0/5) ✅✅ · hard = **5/5** true (acceptance: ≥3/5) ✅✅

## Conv C0128 chi tiết (turn 6)

- `misconceptions`: `["Nhầm React (framework JS) với ReAct (pattern agent trong slide Day 3)"]`
- `follow_ups`: (1) check-question LLM: "ReAct là một phương pháp hay công cụ gì trong lĩnh vực nào?" · (2) "Bạn muốn mình đào sâu hơn về ReAct không?" · (3) "Bạn có định hỏi **ReAct pattern** trong slide Day 3 (Design Pattern & ReAct cho Agent) — khác với React framework JavaScript nhé?"
- Envelope đủ 5 trường ở mọi turn (answer · move · misconceptions[] · follow_ups[] 2-3 · asked_check_question bool) ✅

## Repeat từ Memory (A-06 nối A-05)

3 turn liên tiếp "embedding là gì?" cùng learner: turn 1 asked=false · turn 2 asked=false · **turn 3 asked=true** + follow-up "Bạn có thể mô tả mục đích chính của embedding trong học máy…" → hệ thống nhận diện "đã trả lời" và đi sâu/hỏi hướng tiếp ✅ (acceptance A-06 #2)

## Ghi chú

- Check-hiểu chỉ phát sinh LLM call khi có dấu hiệu khó (turn bình thường: 0 LLM call thêm).
- UI: follow_ups render thành chip click được (click → điền composer, không gửi) + badge move (Ôn khái niệm / Ví dụ thực tế / Gợi ý / Xác nhận hiểu) — ChatPanel.tsx.