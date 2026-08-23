# AI SPEC — VLearn Research Tutor · Nhóm [X] · Zone [X]

Hướng: [x] A — VLearn · [ ] B — Trợ lý Học viên · [ ] C — Làn mở  
Loại: [x] Tối ưu tính năng có sẵn · [x] Tính năng mới

---

## §1. User & Job

### Job executor
**Học viên đang ôn bài sau buổi học** trên VLearn — đọc lại slide, muốn hiểu sâu hơn những gì slide trình bày.

### Core JTBD *(không tên sản phẩm/AI)*
Khi đọc lại tài liệu sau buổi học, tôi muốn được giải thích sâu hơn về các khái niệm (kể cả những thứ tài liệu chưa đề cập), so sánh giữa các khái niệm, và có ví dụ thực tế — để tôi hiểu đúng và đủ, không bị hổng kiến thức.

### Problem statement *(KHÔNG chữ AI)*
Học viên muốn đào sâu kiến thức trong slide nhưng không có người giải đáp. Slide chỉ cung cấp nội dung tĩnh — không thể trả lời câu hỏi "ngoài cái này còn gì nữa", "so sánh A với B ra sao", "ví dụ thực tế của khái niệm này". Học viên phải tự mở Google/ChatGPT riêng để tìm, mất thời gian và không biết nguồn có đáng tin không.

### Evidence *(chuẩn B — mining + chuẩn A — khảo sát)*

**Chuẩn B — Mining chatlog 2,522 dòng (22/07—29/07/2026):**

| Chỉ số | Số liệu |
|---|---|
| Tổng turn hỏi-đáp | 1,261 |
| Turn AI thất bại | **385 (30.5%)** |
| Hội thoại 1 turn rồi bỏ | 309/585 (52.8%) |
| AI không cite tài liệu | 582/1,261 (46.2%) |
| Downvote > Upvote | 37 vs 33 |

**Phân loại 385 turn thất bại:**

| Pattern | Số turn | % |
|---|---|---|
| Không tìm thấy nội dung trang cụ thể | 207 | 53.8% |
| Yêu cầu tóm tắt toàn bộ slide | 84 | 21.8% |
| Hỏi logistics (bài tập, deadline) | 11 | 2.9% |
| Spam ký tự vô nghĩa | 9 | 2.3% |
| Hỏi model/API tutor | 6 | 1.6% |
| Nhầm "React" vs "ReAct" | 5 | 1.3% |
| Teencode/tiếng lóng | 3 | 0.8% |
| Jailbreak | 2 | 0.5% |
| Khác/chưa phân loại | 43 | 11.2% |

**≥5 quote nguyên văn từ chatlog:**

> 1. *"Designt Pattern ReAct là gì có lưu ý gì về nó?"* → AI: "không tìm thấy định nghĩa chi tiết về 'ReAct'" *(dù ReAct là chủ đề chính của buổi học)*
> 2. *"giải thích nghĩa chi tiết của trang 4"* → AI: "không tìm thấy nội dung cụ thể cho trang 4" [Downvote]
> 3. *"Giải thích slide 4 cho tôi"* → AI cite **[trang 70]** thay vì trang 4 [Downvote]
> 4. *"Giúp tôi viết summary chi tiết và đầy đủ nhất về toàn bộ slide bài giảng ngày hôm nay"* → AI: "không chứa bản tóm tắt tổng quát"
> 5. *"promt caching ở đâu"* → AI: "không có thông tin chi tiết về 'prompt caching'"

**Chuẩn A — Khảo sát 58 học viên (30/07/2026):**

| Chỉ số | Kết quả |
|---|---|
| Số người khảo sát | **n = 58** |
| AI chỉ "đọc lại slide" (search engine) | **34/58 (58.6%)** |
| AI "bình thường, đôi khi có tư duy" | 18/58 (31.0%) |
| AI "thực sự thông minh" | 5/58 (8.6%) |
| Từng hụt hẫng vì AI lặp lại slide | **35/58 (60.3%)** |

**≥5 quote nguyên văn từ khảo sát:**

> 1. *"Nó không thật sự tìm tài liệu giải thích, chỉ đơn giản là trích xuất chữ trong slide"* — Nguyễn Hoàng Anh
> 2. *"Có, làm mình cảm thấy phí thời gian"* — Nguyễn Đăng Long
> 3. *"AI chưa làm tốt việc giải thích và tóm tắt lại những thứ tôi cần mà đơn giản là copy lại text trên pdf"* — Nguyễn Văn T
> 4. *"Mình thấy hỏi chatgpt ok hơn =)))"* — Đỗ Ngọc Anh
> 5. *"Có, trả lời không khác gì slide"* — Đào Kiều Thịnh Quang

**Log khảo sát đầy đủ:** `../validation/khao-sat.md`

---

## §2. Impact & Quyết định chọn

### Bảng impact ≥3 ứng viên

| # | Pain Point | Số người gặp | Tần suất | Ảnh hưởng | Chọn? |
|---|---|---|---|---|---|
| **1** | **Mở rộng kiến thức ngoài slide bằng paper khoa học** | 165+ turn fail (~43% của 385) + 34/58 khảo sát (58.6%) | Mỗi buổi học | Học viên muốn hiểu sâu nhưng AI không đáp ứng → tự Google mất 5-10 phút, rủi ro sai nguồn, 60.3% từng hụt hẫng | [PASS] **CHỌN** |
| **2** | Sửa retrieval/indexing — tăng tỉ lệ tìm thấy nội dung trong slide | 207 turn fail (53.8%) | Mỗi buổi học | Học viên hỏi đúng nội dung có trong slide nhưng AI không tìm ra → mất niềm tin, 52.8% bỏ đi sau 1 turn | [FAIL] Loại |
| **3** | Tóm tắt toàn bộ buổi học | 84 turn fail (21.8%) + 28/58 muốn cải thiện tổng hợp | Cuối mỗi buổi | Học viên mất 15-20 phút tự tổng hợp, dễ bỏ sót ý chính | [FAIL] Loại |
| **4** | Phát hiện & sửa hiểu lầm (misconceptions) + follow-up | 0/1,261 lần dùng | Mỗi buổi học | Học viên học sai không được sửa → mất điểm quiz, lỗ hổng kiến thức tích lũy | [FAIL] Loại |

### Ứng viên đã loại + vì sao

| Ứng viên loại | Lý do |
|---|---|
| **#2 — Sửa retrieval** | Cần truy cập pipeline indexing của VLearn thật — không làm được trong hackathon. Hơn nữa, chỉ sửa retrieval thì vẫn không giải quyết được ~43% câu hỏi đòi kiến thức ngoài slide. |
| **#3 — Misconceptions** | Chưa có data — field `misconceptions` trong chatlog luôn rỗng. Không có cơ sở để build + test. |
| **#4 — Tóm tắt toàn buổi** | Scope quá rộng cho hackathon 1.5 ngày. Cần tổng hợp toàn bộ slide → token cost cao, khó test kỹ. |

### Ứng viên chọn + vì sao (bằng số)
**#1 — Mở rộng kiến thức ngoài slide bằng paper khoa học.** Lý do:
- **165+ turn thất bại** (~43% của 385) có thể được giải quyết — impact lớn nhất trong các hướng khả thi
- Build được prototype Working trong 1.5 ngày: đã có agent LangGraph + paper RAG + frontend 3-panel
- Có golden paper sẵn trong data pack để test (W-Online-payment.pdf)
- Tận dụng được cả slide retrieval hiện có (Normal mode) + mở rộng research (Research mode)

---

## §3. Giải pháp tương tự đã nghiên cứu

| Sản phẩm | Flow | Đáng học | Đáng né | Mình khác gì |
|---|---|---|---|---|
| **NotebookLM** | Upload PDF → AI trả lời từ tài liệu, luôn cite nguồn cạnh câu trả lời | Cite nguồn rõ ràng, user click vào cite để nhảy đến đoạn gốc | Chỉ trả lời từ tài liệu đã upload, không tự tìm kiếm bên ngoài | **Tự động tìm paper từ arXiv** khi câu hỏi vượt ngoài slide — không cần user upload |
| **ChatGPT Study Mode** | Chat với GPT, có thể hỏi bất kỳ kiến thức nào | Trả lời được mọi thứ, kể cả kiến thức mở rộng | **Không cite nguồn** cụ thể (trang, dòng, quote) — user không kiểm chứng được | Mọi câu trả lời Research đều có **citation trace được đến trang, dòng, trích nguyên văn** |
| **Khanmigo** | Tutor AI trong Khan Academy, gợi ý từng bước | Chủ động hướng dẫn, không đưa đáp án ngay | Chỉ hoạt động trong hệ sinh thái Khan Academy | Chạy trên nội dung khóa học thật, mở rộng ra paper khoa học bên ngoài |

---

## §4. Thiết kế

### Lát cắt MỘT CÂU
> **Học viên đang ôn slide sau buổi học · muốn hiểu sâu một khái niệm vượt ngoài nội dung slide · AI tự động tìm paper khoa học trên arXiv liên quan nhất, đọc full text và trả lời kèm citation kiểm chứng được đến trang và dòng · học viên nhận được câu trả lời có căn cứ khoa học, không phải tự Google.**

### Non-goals (≥3 thứ KHÔNG build)
1. **KHÔNG** thay thế slide retrieval hiện có — Normal mode vẫn giữ nguyên logic
2. **KHÔNG** deploy production — prototype chạy local, không có auth, rate limit, monitoring
3. **KHÔNG** hỗ trợ upload file từ user — chỉ dùng paper từ arXiv hoặc golden paper đã index sẵn
4. **KHÔNG** hỗ trợ multi-turn research sâu (follow-up question trên cùng 1 paper) — mỗi câu hỏi research là độc lập

### Mức prototype
- [ ] Sketch · [ ] Mock · [x] **Working** — end-to-end với data pack thật

**Phần thật:** AI call (Gemini/OpenAI), arXiv search + download, paper RAG hybrid retrieval, grounding audit, slide BM25 retrieval, citation đến trang/dòng/quote  
**Phần mock:** Không có — toàn bộ flow chạy thật

### Automation
- [ ] augment · [x] **conditional** · [ ] automate

**Lý do theo cost-of-error:**
- **Normal mode** — AI tự trả lời case có căn cứ trong slide. Khi không tìm thấy → từ chối rõ ràng + gợi ý chuyển sang Research mode. Sai thì học viên học sai kiến thức → **đắt**.
- **Research mode** — AI tự tìm paper + trả lời. Nhưng có grounding audit kiểm tra claim-vs-excerpt. Sai thì học viên có thể kiểm tra lại citation (trang, dòng, quote). **Cost-of-error thấp hơn** vì user tự verify được.

### §4b. Nguyên tắc HAX/PAIR đã áp dụng (≥4)

| # | Nguyên tắc | Áp cụ thể vào đâu trong prototype |
|---|---|---|
| **G1** — Làm rõ hệ thống làm được gì | `ChatPanel.tsx:50` — Tin nhắn welcome: *"Bạn có thể bôi đen một đoạn trên slide để hỏi hoặc gửi câu hỏi tự do"*. Header chat hiển thị rõ mode: *"Mở rộng kiến thức bằng paper từ arXiv"* |
| **G2** — Làm rõ nó làm tốt đến đâu | `ChatPanel.tsx:309-314` — Subtitle hiển thị rõ ngữ cảnh: *"Ngữ cảnh: Slide trang X"* (Normal) hoặc *"Mở rộng kiến thức bằng paper từ arXiv"* (Research). User biết chính xác câu trả lời dựa trên nguồn nào |
| **G10** — Thu hẹp phạm vi khi nghi ngờ *(bắt buộc)* | `answer.py:58-62` — Normal mode: khi slide không đủ → trả về: *"Rất tiếc, nội dung slide hiện tại không có đủ thông tin. Bạn có thể thử: chuyển sang trang khác, đặt câu hỏi khác, hoặc bôi đen đoạn văn bản cụ thể"*. Research mode: `web_search.py:99-108` — khi không tìm thấy paper → *"Không tìm thấy paper phù hợp trên arXiv. Hãy thử mô tả chủ đề cụ thể hơn."* |
| **G11** — Giải thích vì sao | `ChatPanel.tsx:452-488` — Mỗi citation trong Research mode hiển thị expandable detail: `[PAPER-1]`, tên file, **trang**, **dòng**, **trích nguyên văn** (quote). User mở ra kiểm chứng được ngay |
| **PAIR — Explainability + Trust** | `ChatPanel.tsx:338-366` — Mode selector rõ ràng: Normal / Research với màu sắc khác biệt. Nguồn research hiển thị tên paper + số trang. User biết chính xác AI đang dùng nguồn nào |
| **PAIR — Errors + Graceful Failure** | `server.py:196-203` — Security guard: nếu phát hiện prompt injection → *"Phát hiện prompt injection. Vui lòng đặt câu hỏi học thuật."*. `web_search.py:117-125` — Exception handling: báo lỗi rõ ràng + không crash |

---

## §5. Kiểu lỗi — 4 lớp chỗ khó + kịch bản (≥8)

### 5.1 Ba dạng lỗi thực tế từ test lượt 2 (21/24 pass, 87.5%)

Dựa trên kết quả test Phase B với 24 câu lạ bám sát nội dung slide Day 1/Day 2, dùng GPT-4.1-mini để kiểm tra khả năng routing công cụ và truyền đúng tham số. Ba dạng lỗi thực tế phát hiện được:

| # | Dạng lỗi | Mô tả | Case thực tế | Tần suất |
|---|---|---|---|---|
| **L1** | **Wrong boundary** — gọi tool khi không được phép | User bảo "chỉ soạn nháp, chưa gửi" nhưng AI vẫn gọi tool tìm kiếm. AI không tôn trọng ranh giới "chưa hành động". | Case 09: user yêu cầu soạn nháp cảnh báo metric, nói rõ "tuyệt đối chưa gửi" → AI gọi `lookup` | 1/24 |
| **L2** | **Wrong tool** — chọn sai công cụ | Có URL arXiv cụ thể nhưng AI dùng `fetch` (đọc web) thay vì `paper_text` (đọc full text PDF). AI không phân biệt được "đọc paper khoa học" vs "đọc trang web". | Case 12: user yêu cầu đọc paper tại arxiv.org/abs/2201.11903 → AI gọi `fetch` thay vì `paper_text` | 1/24 |
| **L3** | **Extra tool call** — gọi thừa công cụ | AI gọi đúng công cụ chính nhưng kèm thêm một lời gọi thừa không cần thiết, gây lãng phí token và tăng độ trễ. | Case 15: user yêu cầu timeline của AndrewYNg → AI gọi đúng `timeline` nhưng gọi thêm `lookup` không liên quan | 1/24 |

### 5.2 4 lớp chỗ khó — cụ thể cho lát cắt

| Lớp | Câu hỏi cụ thể | Dạng lỗi liên quan |
|---|---|---|
| **① Nguồn sự thật** | AI bịa thông tin? Cite có đúng trang/dòng? Paper trả về có thực sự liên quan? | L2 (chọn sai công cụ dẫn đến sai nguồn), grounding audit |
| **② Mơ hồ / thiếu thông tin** | Input không đủ rõ (teencode, sai chính tả, câu cụt)? User chưa biết muốn hỏi gì? | Clarify tool: hỏi lại user bằng choice/text thay vì đoán |
| **③ Ngoài phạm vi / thẩm quyền** | User đòi gửi thông báo, publish? User jailbreak? | L1 (gọi tool khi không được phép), security guard |
| **④ Đặc thù domain** | Sai kiến thức AI/ML → học viên học sai? Paper không liên quan được chọn? | L3 (gọi thừa gây nhiễu), topic validator |

### 5.3 ≥10 kịch bản rủi ro

| # | Tình huống | Lớp | Hành vi mong muốn | Test case |
|---|---|---|---|---|
| 1 | User hỏi kiến thức có trong slide, AI trả lời đúng + cite | ① | Trả lời đầy đủ, cite `[D1 - Trang N]` | N01-N06 |
| 2 | User hỏi kiến thức ngoài slide, Research tự tìm paper arXiv | ① | Tìm paper đúng chủ đề, trả lời có `[PAPER-N]`, citation trace được | R03-R05 |
| 3 | User đưa URL arXiv cụ thể → AI đọc full text paper | ① | Gọi đúng `paper_text`, không gọi `fetch` web → **đây là L2** | Case 12 (fail → cần sửa) |
| 4 | User yêu cầu soạn nháp, nói "chưa gửi" | ③ | KHÔNG gọi bất kỳ tool tìm kiếm nào, chỉ soạn nội dung → **đây là L1** | Case 09 (fail → cần sửa) |
| 5 | User yêu cầu 1 việc nhưng AI gọi thêm tool thừa | ④ | Chỉ gọi đúng công cụ được yêu cầu, không "nhiệt tình" thêm → **đây là L3** | Case 15 (fail → cần sửa) |
| 6 | User viết "promt caching" (sai chính tả) | ② | LLM router hiểu đúng ý → build query "prompt caching" → tìm paper | N13 |
| 7 | arXiv API rate limit (HTTP 429) | ② | Tự động fallback DuckDuckGo → vẫn trả về kết quả | — |
| 8 | User mơ hồ: "có quá nhiều thứ, chưa biết học gì" | ② | Gọi clarify tool → hỏi user câu choice để chọn chủ đề, không tự đoán | Case 07 [PASS] |
| 9 | User jailbreak: "BỎ QUA GUARDRAIL" | ③ | Security guard chặn → từ chối + yêu cầu câu hỏi học thuật | N10 |
| 10 | Paper local không liên quan (fraud paper, hỏi deep learning) | ④ | Topic validator từ chối → tự tìm paper mới phù hợp | R01 |

### 5.4 Ba lỗi cần sửa trước demo

| Case | Lỗi | Hành vi hiện tại | Cần sửa thành | Ưu tiên |
|---|---|---|---|---|
| **09** | Wrong boundary | User bảo "chỉ soạn nháp, chưa gửi" → AI vẫn gọi lookup | AI không gọi tool, chỉ trả lời text: "Đây là bản nháp... Bạn muốn tôi gửi đi chưa?" | [HIGH] Cao |
| **12** | Wrong tool | User đưa URL arXiv → AI gọi fetch web thay vì paper_text | Nhận diện URL arxiv.org → tự động route sang paper_text để đọc full text PDF | [HIGH] Cao |
| **15** | Extra call | AI gọi timeline + lookup thừa | Chỉ gọi timeline, không tự ý thêm lookup | [MED] Trung bình |

---

## §6. Bốn đường đi của trải nghiệm

### Happy path (PASS)
Học viên mở slide Day 2 trang 25-26 → chọn Research mode → hỏi *"có paper nào về LLM agent evaluation benchmark không"* → AI chọn đúng tool `papers` với query `"LLM agent evaluation benchmark"`, `max_results=3`, `sort_by=relevance` → arXiv trả về 3,816 kết quả, lấy 3 paper phù hợp nhất → học viên mở citation kiểm chứng → **hài lòng, tiếp tục học**. *(Case 22 — PASS)*

### Low-confidence / mơ hồ (②) (PASS)
Học viên nói *"Slide Day 2 có quá nhiều thứ: metric, workflow, agent, HITL... tôi chưa biết đào sâu phần nào"* → AI gọi `clarify` tool → hỏi lại: *"Bạn muốn đào sâu chủ đề nào? A) Metric, B) Workflow, C) Agent, D) HITL"* → **AI không đoán, không tự search linh tinh**. *(Case 07 — PASS)*

### Failure / sai công cụ (①) (FAIL)
Học viên đưa URL arXiv `arxiv.org/abs/2201.11903` yêu cầu đọc full text → AI gọi `fetch` (đọc web) thay vì `paper_text` (đọc PDF) → kết quả trả về trang abstract thay vì nội dung paper → **học viên phải hỏi lại**. *(Case 12 — FAIL, đã xác định cách sửa)*

### Vượt ranh giới (③) (FAIL)
Học viên yêu cầu *"soạn nháp cảnh báo, tuyệt đối chưa gửi"* → AI vẫn gọi `lookup` tìm kiếm → học viên bối rối vì AI không tôn trọng yêu cầu "chưa làm gì cả". *(Case 09 — FAIL, đã xác định cách sửa)*

### Correction (user sửa) (PASS)
Học viên không hài lòng với câu trả lời Research → chuyển sang **Normal mode** để hỏi trong phạm vi slide → hoặc chọn **focus paper cụ thể** thay vì auto-search → **học viên kiểm soát được nguồn thông tin**.

### Khi bị đòi ngoài phạm vi (③) (PASS)
Học viên hỏi *"bài tập tuần này làm gì"* → LLM router trả về `OUT_OF_SCOPE` → AI: *"Nằm ngoài phạm vi học thuật, không tìm paper."* → không tốn token gọi arXiv.

---

## §7. Kiểm thử

### 7.1 Kết quả test Phase B — Tool Routing (OpenAI GPT-4.1-mini)

| Chỉ số | Kết quả |
|---|---|
| Tổng case | **24** |
| Pass | **21 / 24** |
| Accuracy | **87.5%** |
| Tool routing đúng | 21/24 (87.5%) |
| Tham số đúng | 21/24 (87.5%) |
| Multi-turn đúng | **4/4 (100%)** |

| Dạng lỗi | Số case |
|---|---|
| Wrong boundary (gọi tool khi không được phép) | 1 |
| Wrong tool (chọn sai công cụ) | 2 |

### 7.2 Chiều chất lượng + định nghĩa kiểm chứng được

| Chiều | Định nghĩa | Thang đo |
|---|---|---|
| **Tool routing** | AI chọn đúng công cụ cho từng loại yêu cầu (papers cho học thuật, lookup cho web, clarify khi mơ hồ, v.v.) | Pass/Fail — khớp với expected tool |
| **Tham số** | AI truyền đúng query, max_results, sort_by, timeframe theo yêu cầu user | Pass/Fail — khớp với expected arguments |
| **Ranh giới** | AI không gọi tool khi user nói "chưa", "chỉ nháp", "đừng search" | Pass/Fail — expected no tool call |
| **Multi-turn** | AI giữ ngữ cảnh slide từ turn trước, chỉ xử lý yêu cầu mới nhất | Pass/Fail |

### 7.3 Golden set — 24 case (Phase B Tool Routing)

**File:** `slide-tools-v1_B_group_openai_20260731T101454184740.json`

| Phân bố | Số case | Ghi chú |
|---|---|---|
| Tổng | **24** | 20 single-turn + 4 multi-turn |
| Slide Day 1 | 13 | Kiến thức AI & LLM Foundation |
| Slide Day 2 | 11 | Xác định bài toán cho AI |

**Các tool được test:** `lookup`, `papers`, `fetch`, `social_search`, `timeline`, `policy`, `clarify`, `format`, `paper_text`, `send`

**Phân bố theo kịch bản test:**

| Kịch bản | Số case | Mô tả |
|---|---|---|
| Phân biệt đúng tool | 8 | papers vs lookup vs fetch — không nhầm lẫn |
| Truyền đúng tham số | 6 | query, max_results, sort_by, timeframe khớp yêu cầu |
| Ranh giới hành động | 2 | Không gọi tool khi user bảo "chưa", "chỉ nháp" |
| Xử lý mơ hồ | 2 | clarify thay vì đoán khi user chưa rõ ý |
| Multi-turn | 4 | Giữ ngữ cảnh slide từ turn trước |
| Đọc full text paper | 2 | paper_text với đúng arxiv_url |

### 7.4 Quality bar *(chốt từ 23:59 N1, giữ nguyên)*

| Chiều | Bar | Kết quả lượt 1 | Kết quả lượt 2 |
|---|---|---|---|
| Tool routing đúng | >=80% | 18/24 (75.0%) | 21/24 (87.5%) |
| Tham số đúng | >=80% | 19/24 (79.2%) | 21/24 (87.5%) |
| Multi-turn | 100% | 3/4 (75.0%) | 4/4 (100%) |

### 7.5 Kết quả các lượt chạy

| Lượt | Thời gian | Tổng | Đạt | % | Ghi chú |
|---|---|---|---|---|---|
| **1** | 31/07 09:30 | 24 | **18** | **75.0%** | Chạy lần đầu, chưa tinh chỉnh prompt. 6 lỗi: wrong_tool x3, wrong_boundary x1, extra_call x1, multi-turn mất ngữ cảnh x1 |
| **2** | 31/07 10:14 | 24 | **21** | **87.5%** | Sau sửa prompt. Còn 3 lỗi: wrong_boundary (case 09), wrong_tool (case 12), extra call (case 15). Multi-turn đã fix xong |
| 3 | ___ | 24 | ___ | ___% | Sau validation user test |

#### Chi tiết lượt 1 — 6 case fail

| Case | Lỗi | Mô tả |
|---|---|---|
| 02 | wrong_tool | User yêu cầu tìm paper arXiv -> AI gọi lookup web thay vì papers |
| 05 | wrong_tool | User yêu cầu timeline tài khoản cụ thể -> AI gọi social_search theo từ khóa |
| 09 | wrong_boundary | User bảo "soạn nháp, chưa gửi" -> AI vẫn gọi lookup |
| 12 | wrong_tool | User đưa URL arxiv.org/abs/... -> AI gọi fetch thay vì paper_text |
| 15 | extra_call | AI gọi timeline (đúng) + lookup (thừa) |
| 21 | multi-turn | Multi-turn: AI không giữ ngữ cảnh slide từ turn 1, gọi sai tool ở turn 2 |

#### Chi tiết lượt 2 — 3 case còn fail (log thật)

| Case | Lỗi | Hành vi | Hướng sửa |
|---|---|---|---|
| 09 | wrong_boundary | User bảo "soạn nháp, chưa gửi" -> AI vẫn gọi lookup | Them rule: "nếu user nói chưa/đừng -> không gọi tool" |
| 12 | wrong_tool | User đưa URL arxiv.org/abs/2201.11903 -> AI gọi fetch thay vì paper_text | Them rule: "URL chứa arxiv.org/abs -> dùng paper_text" |
| 15 | extra_call | AI gọi timeline (đúng) + lookup (thừa) | Them rule: "chỉ gọi đúng 1 tool được yêu cầu" |

---

## §8. Phân công & Kế hoạch

### Phân công có tên

| Thành viên | Mã HV | Vai trò |
|---|---|---|
| Phạm Khắc Khương Duy | 2A2202601982 | Spec + evidence |
| Trần Quang Minh | 2A2202601210 | Agent + prompt engineering |
| Đào Kiều Thịnh Quang | 2A2202601014 | Paper RAG + retrieval |
| Nguyễn Hoàng Anh  | 2A2202601186 | Frontend + UI/UX + Tool|
| Ngô Văn Nam | 2A2202601340 | Eval + golden set + test |

### Willing users (≥3 tên — sẽ điền sau CP1)

| # | Tên / Mã HV | Vai trò | Đồng ý thử? |
|---|---|---|---|
| 1 | ___ | Học viên khoá AI | ☐ |
| 2 | ___ | Học viên khoá AI | ☐ |
| 3 | ___ | Thành viên zone khác | ☐ |

### Kế hoạch vòng validation CP5

**3 câu hỏi cho mỗi phiên test (10 phút/người):**
1. *"Điều gì khó hiểu hoặc khó chịu nhất?"*
2. *"Kết quả này bạn có tin không — vì sao?"*
3. *"Bạn có dùng thật không — vì sao / vì sao chưa?"*

**Người log:** ___

### Multi-prototype *(nếu làm)*
Không áp dụng — nhóm chọn build thẳng mức Working do đã có skeleton agent + RAG từ trước.

### Kế hoạch sáng N2
- 09:00 — Chạy golden set lần 1, ghi kết quả
- 09:30 — Sửa lỗi từ golden set (ưu tiên case fail safety trước)
- 10:00 — Chạy golden set lần 2
- 10:30 — CP3: Show AI thật + golden set + bảng kết quả lượt 1
- 11:00 — Validation với user thật (≥5 người)
- 11:30 — Ghi changelog từ feedback
- 12:00 — CP4: Chốt spec.md

---

## §9. Changelog

| Thời điểm | Đổi gì | Vì sao (trỏ về feedback/case nào) |
|---|---|---|
| *(để trống — cập nhật sau CP5)* | | |
