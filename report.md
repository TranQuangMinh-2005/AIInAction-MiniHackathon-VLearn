# Report: VLearn AI Tutor — Khi chatbot không trả lời được câu hỏi của học viên

> **Nguồn:** `chat_history_anonymized_for_hackathon.csv` — 2,522 messages thực tế  
> **Phạm vi:** 1,261 turn · 585 hội thoại · 369 học viên · 22/07–29/07/2026

---

## 1. Chiến tuyến

| | |
|---|---|
| **Sản phẩm** | VLearn AI Tutor — chatbot trả lời câu hỏi dựa trên nội dung slide |
| **Người dùng** | Học viên khóa AI Thực Chiến, đọc và học lại slide trên VLearn |
| **Vấn đề** | Học viên muốn hỏi sâu hơn về bài giảng, nhưng chatbot thường xuyên không trả lời được |
| **Gốc rễ** | AI tutor bị giới hạn trong nội dung slide — không được research bên ngoài, không có khả năng tổng hợp hay mở rộng kiến thức |

---

## 2. Tổng quan số liệu

| Chỉ số | Số liệu | Ý nghĩa |
|---|---|---|
| Tổng turn hỏi-đáp | 1,261 | — |
| **Turn AI thất bại** | **385** | **30.5%** — cứ 3 câu thì 1 câu không trả lời được |
| Hội thoại 1 turn rồi bỏ | 309/585 (52.8%) | Quá nửa học viên rời đi sau câu hỏi đầu tiên |
| AI trả lời không cite tài liệu | 582/1,261 (46.2%) | Gần nửa số câu trả lời không dẫn nguồn |
| Bị downvote | 37 turn | 37 > 33 upvote — học viên không hài lòng nhiều hơn hài lòng |
| AI chủ động kiểm tra hiểu bài | 3/2,515 lần | Gần như không tồn tại |
| Field `misconceptions` | 0/1,261 lần dùng | Không phát hiện hiểu lầm của học viên |
| Field `follow_ups` | 0/1,261 lần dùng | Không gợi ý câu hỏi tiếp theo |

---

## 3. 385 turn thất bại — phân loại theo khả năng của slide

### 3.1 Slide CÓ SẴN câu trả lời, nhưng AI retrieval fail (~57%)

Lỗi kỹ thuật — nội dung tồn tại trong slide, AI không tìm ra.

**Ví dụ 1 — ReAct là nội dung chính của bài, AI bảo không có:**

> **USER:** *"Designt Pattern ReAct là gì có lưu ý gì về nó?"*
>
> **TUTOR:** *"Rất tiếc, tôi không tìm thấy định nghĩa chi tiết về 'ReAct' trong các slide bài giảng hiện tại của ngày học này."*

→ ReAct pattern là chủ đề chính của cả buổi học. Slide có đầy đủ. AI không retrieval được.

**Ví dụ 2 — AI cite sai trang (trang 4 → cite trang 70):**

> **USER:** *"Giải thích slide 4 cho tôi"*
>
> **TUTOR:** *"...[trang 70]..."*
>
> 🔻 **Downvote**

→ Học viên hỏi slide 4, AI trả lời bằng nội dung trang 70 — index sai hoàn toàn.

---

### 3.2 Slide KHÔNG ĐỦ để trả lời — cần kiến thức ngoài slide (~43%)

Lỗi thiết kế — học viên muốn nhiều hơn những gì slide cung cấp, AI không được ra ngoài.

**Ví dụ 1 — Học viên muốn tóm tắt toàn bộ buổi học:**

> **USER:** *"tóm tắt nội dung chính trong slide này"*
>
> **TUTOR:** *"Xin lỗi bạn, tôi không tìm thấy nội dung cụ thể cho slide 37 trong tài liệu hiện có."*

→ Slide không có sẵn bản tóm tắt. AI không có khả năng tự đọc và tổng hợp nội dung.

**Ví dụ 2 — Học viên muốn summary chi tiết toàn bộ ngày học:**

> **USER:** *"Giúp tôi viết summary chi tiết và đầy đủ nhất về toàn bộ slide bài giảng ngày hôm nay"*
>
> **TUTOR:** *"Rất tiếc, hiện tại trong nội dung slide không chứa... bản tóm tắt tổng quát về toàn bộ các slide."*

→ AI chỉ trả lời được từng khái niệm riêng lẻ, không tổng hợp được bức tranh lớn.

**Ví dụ 3 — Học viên hỏi kiến thức thực tế ngoài slide:**

> **USER:** *"6 giai đoạn phát triển của AI"*
>
> **TUTOR:** *"Rất tiếc, nội dung về '6 giai đoạn phát triển của AI' không có trong tài liệu slide của ngày học hôm nay."*

→ Học viên hỏi kiến thức có thật ngoài đời. Slide không cover. AI không được phép tìm kiếm bên ngoài → đứng im.

**Ví dụ 4 — Học viên hỏi kỹ thuật thực tế không có trong slide:**

> **USER:** *"promt caching ở đâu"*
>
> **TUTOR:** *"nội dung slide bài giảng hôm nay không có thông tin chi tiết về 'prompt caching'."*

→ Prompt caching là kỹ thuật phổ biến trong ngành AI. Slide buổi đó không dạy. AI không thể bổ sung.

**Ví dụ 5 — Học viên muốn giải thích chi tiết hơn mức slide cung cấp:**

> **USER:** *"giải thích nghĩa chi tiết của trang 4"*
>
> **TUTOR:** *"rất xin lỗi vì hiện tại hệ thống tìm kiếm không tìm thấy nội dung cụ thể cho trang 4 trong tài liệu của bài học hôm nay."*
>
> 🔻 **Downvote**

→ Slide trang 4 có thể chỉ có tiêu đề/bullet points. Học viên muốn giải thích CHI TIẾT — thứ slide không có sẵn.

**Ví dụ 6 — Học viên dùng teencode, AI không hiểu:**

> **USER:** *"Tóm tắt sờ lai này"* (= "tóm tắt slide này")
>
> **TUTOR:** *"Rất tiếc, tôi không tìm thấy nội dung cụ thể cho trang 7."*

→ AI không map được "sờ lai" → "slide". Không hiểu ngôn ngữ tự nhiên của học viên Việt Nam.

**Ví dụ 7 — Học viên hỏi liên tục, AI fail 8/9 câu rồi học viên bỏ đi:**

> **Conv C0128 — 13 turns:**
>
> | Lần | Học viên hỏi | AI trả lời |
> |---|---|---|
> | 1 | *"React là gì và dùng để làm gì?"* | ❌ *"không chứa thông tin về React"* |
> | 2 | *"Tóm tắt nội dung slide đầu tiên"* | ❌ *"không tìm thấy"* |
> | 3 | *"AI Agent khác gì LLM thông thường?"* | ❌ *"không có phần so sánh"* |
> | 4 | *"React là gì?"* | ❌ *"không tìm thấy"* |
> | 5 | *"React là gì?"* | ❌ *"không thấy đề cập"* |
> | 6 | *"2+2 bằng mấy?"* | ✅ *"2 cộng 2 bằng 4"* |
> | 7 | *"Giải phẫu agent 5 bộ phận?"* | ❌ *"không tìm thấy"* |
> | 8 | *"3 ý chính của slide"* | ❌ *"không tìm thấy"* |
> | 9 | *"Tiêu đề buổi học, giảng viên?"* | ❌ *"không tìm thấy"* |
>
> → **8/9 câu fail. Học viên bỏ đi.** Câu duy nhất AI trả lời được là "2+2=4" — một câu ngoài lề.

---

## 4. Nguyên nhân gốc rễ

| # | Nguyên nhân | Loại |
|---|---|---|
| 1 | **AI bị nhốt trong slide** — không được tìm kiếm bên ngoài, không có kiến thức nền để bổ trợ cho câu trả lời | 🔴 Thiết kế |
| 2 | **Không có khả năng tổng hợp** — không tóm tắt được slide, không so sánh được khái niệm, không trả lời được câu hỏi "tổng quan" | 🔴 Thiết kế |
| 3 | **Retrieval/indexing kém** — nội dung có trong slide nhưng AI không tìm ra, thậm chí cite sai trang | 🟡 Kỹ thuật |
| 4 | **Không hiểu ngôn ngữ tự nhiên** — teencode, chính tả sai, viết tắt → AI không mapping được | 🟡 Kỹ thuật |
| 5 | **Không chủ động** — không kiểm tra hiểu bài, không gợi ý câu tiếp theo, không phát hiện học viên stuck | 🟡 UX |

---

## 5. Lát cắt

> **385/1,261 câu hỏi AI thất bại (30.5%). Trong đó ~43% học viên muốn đào sâu hơn những gì slide cung cấp — tóm tắt, so sánh, ví dụ, kiến thức mở rộng — nhưng AI tutor bị giới hạn trong nội dung slide, không được phép research bên ngoài, không có khả năng tổng hợp. Đây không phải học viên hỏi ngoài lề — đây là giới hạn thiết kế của hệ thống.**
