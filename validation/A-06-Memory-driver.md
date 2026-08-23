# A-06 Driver — Memory anonymous per-browser (Dev2, t17)

> Backend: cổng tạm 8002 (đã kill sau đo) · store: `src/agent/agent/memory/data/{learner_id}.json` · không PII (chỉ doc/page/concepts/questions/misconceptions/notes).

## 1. Endpoint GET/PUT `/api/learners/{learner_id}/state`

| Bước | Gọi | Kết quả | PASS/FAIL |
|---|---|---|---|
| GET learner lạ | `GET /api/learners/test-learner-1/state` | `{"doc_id":null,"page":null,"concepts":[],…}` — state rỗng, không crash | ✅ |
| PUT upsert | `PUT … state {"doc_id":"d10","page":3,"concepts":["RAG","LLM"]}` | concepts có count=1, doc/page lưu | ✅ |
| GET lại | `GET …` | dữ liệu persist | ✅ |
| learner_id xấu | `GET /api/learners/""` + `a/b\c;d` | state rỗng an toàn | ✅ |

## 2. Script 3 turn liên tiếp (turn 2 = turn 1) — turn 3 không lặp y hệt

Cùng learner `demo-learner-02`, câu "embedding là gì?" (d9, p7):

| Turn | asked_check_question | move | Ghi chú |
|---|---|---|---|
| 1 | false | review_concept | trả lời bình thường |
| 2 | false | review_concept | (memory count=1 tại thời điểm envelope) |
| 3 | **true** | give_hint | count=2 ở memory → nhận diện lặp; follow-up "Bạn có thể mô tả mục đích chính của embedding…" + nhắc "đã giải thích trước đó + muốn đi sâu phần nào?" |

→ **turn 3 KHÔNG lặp nội dung y hệt** ✅ (acceptance #2) · memory sau đó: `questions: [{"name":"embedding là gì?","count":3,…}]` ✅

## 3. Reload browser giữ memory (acceptance #1)

- learner_id sinh client-side, lưu `localStorage["vlearn-learner-id"]` (crypto.randomUUID, fallback an toàn) — cùng browser reload → cùng token → cùng file memory.
- `build_context()` nạp "Khái niệm đã hỏi trước đây: …" vào prompt stream (THÔNG TIN HỌC VIÊN) + coach dùng memory cho dấu hiệu lặp/nhầm lẫn.
- Verified: ghi 2 turn bằng learner A → GET state A trả đủ; learner B state rỗng (cô lập per-browser) ✅

## 4. Backward-compat

- `learner_id` là field OPTIONAL của ChatRequest — frontend cũ không gửi → memory_context="" → nhánh cũ chạy y hệt (không đổi hành vi trả lời khi memory rỗng) ✅
- Memory endpoints là endpoint MỚI, không sửa endpoint cũ ✅

## 5. Không PII

Schema chỉ lưu: doc_id · page · concepts[] · misconceptions[] · questions[] (text câu hỏi học thuật) · notes[] · updated_at. Không lưu tên/email/địa chỉ.