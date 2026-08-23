# Agent integration contract (v1)

RAG là module độc lập. Agent không cần biết cách đọc PDF, embedding, retrieval
hay entailment hoạt động bên trong.

## Cách ghép khuyến nghị: HTTP

Chạy RAG service:

```bash
cd libs/rag
set -a; source .env; set +a
.venv/bin/paper-rag serve
```

Agent gọi:

```http
POST http://127.0.0.1:8000/ask
Content-Type: application/json

{
  "question": "Bài báo báo cáo false positive rate bao nhiêu?",
  "top_k": 6,
  "source": "W-Online-payment.pdf"
}
```

Chỉ `question` là bắt buộc. `top_k` mặc định là `6`; `source` có thể bỏ qua.
Nếu câu hỏi chứa tên file hoặc tên bài báo, RAG tự nhận diện source.

Response ổn định:

```json
{
  "answer": "Câu trả lời có citation [S1].",
  "grounded": true,
  "citations": [],
  "retrieval": []
}
```

Agent nên:

1. Dùng nguyên `answer` làm nội dung từ paper-RAG.
2. Đính kèm `citations` nếu UI hỗ trợ nguồn.
3. Nếu `grounded=false`, vẫn có thể hiển thị answer trong prototype nhưng nên
   thêm cảnh báo “một phần bằng chứng chưa vượt qua kiểm tra grounding”.
4. Không tự tính lại retrieval score hoặc sửa citation label.

Kiểm tra service trước khi gọi:

```http
GET http://127.0.0.1:8000/health
```

## Ghép trực tiếp bằng Python

Nếu Agent chạy trong cùng Python environment:

```python
from local_rag.agent_tool import TOOL_SCHEMA, ask_research_papers

result = ask_research_papers(
    question="Bài báo báo cáo false positive rate bao nhiêu?",
    source="W-Online-payment.pdf",  # optional
)
```

`TOOL_SCHEMA` có thể đưa thẳng vào function/tool registry của Agent. Hàm tool
giữ tên `ask_research_papers`; input cũ chỉ có `question` vẫn tiếp tục chạy.

## Quy tắc tương thích

- Không đổi tên `/ask`, `/search` hoặc `ask_research_papers` trong contract v1.
- Không xóa hoặc đổi kiểu bốn top-level response fields:
  `answer`, `grounded`, `citations`, `retrieval`.
- Có thể bổ sung field mới bên trong citation/retrieval; Agent nên bỏ qua field
  không dùng.
- Đổi provider OpenAI/Gemini, model, chunking hoặc retrieval không làm thay đổi
  contract này.
