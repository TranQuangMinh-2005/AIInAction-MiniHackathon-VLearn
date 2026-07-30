# Local Paper RAG

RAG này đọc một thư mục PDF bất kỳ, lưu toàn bộ text, metadata và vector index
trong SQLite trên máy, sau đó dùng OpenAI hoặc Gemini để tạo embedding và trả
lời. Hai PDF đầu tiên chỉ là bộ kiểm thử; pipeline không gắn cứng vào tên hay
nội dung của chúng.

## Khả năng chính

- Nạp PDF tăng dần: file không đổi sẽ không bị embed lại.
- Chunk theo từng trang để citation luôn có số trang chính xác.
- Tự lọc theo đúng PDF khi câu hỏi chứa tên file/tên bài; API cũng nhận tham số
  `source` tường minh.
- Section-aware retrieval: ưu tiên Abstract/Methods/Results/Conclusion cho câu
  hỏi tổng hợp, hạ References/front matter và chunk quá ngắn.
- Hybrid retrieval: semantic search + BM25 keyword search + MMR để giảm các đoạn
  trùng nhau.
- Citation theo từng claim; `quote` phải là exact substring trong chunk gốc.
- Lượt entailment audit riêng kiểm tra từng claim–quote. `grounded=true` chỉ khi
  toàn bộ kiểm tra đạt, không chỉ vì answer có ký hiệu citation.
- Có CLI, HTTP API và Python function để Agent khác gọi.
- Khi nguồn không đủ, prompt yêu cầu từ chối kết luận thay vì dùng kiến thức bên
  ngoài.

## Cài đặt

Khuyến nghị Python 3.11 hoặc 3.12:

```bash
cd codebase/rag
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
cp .env.example .env
```

Nếu chưa có OpenAI API key, dùng Gemini key:

```bash
export GEMINI_API_KEY="..."
```

Nếu có OpenAI API key:

```bash
export OPENAI_API_KEY="..."
```

Mặc định `RAG_PROVIDER=auto`: OpenAI được ưu tiên khi có cả hai key; nếu không
có OpenAI key, RAG tự dùng Gemini. Có thể ép lựa chọn bằng
`RAG_PROVIDER=gemini` hoặc `RAG_PROVIDER=openai`.

Ứng dụng đọc biến môi trường trực tiếp. Không commit key vào Git. File `.env`
chỉ là nơi tham khảo; nếu muốn tự động đọc `.env`, có thể dùng shell như
`set -a; source .env; set +a`.

## Nạp và hỏi PDF

Đặt PDF vào `data/papers/`, rồi chạy:

```bash
paper-rag ingest
paper-rag ask "Mục tiêu và đóng góp chính của bài báo là gì?" \
  --source "W-Online-payment.pdf"
paper-rag search "experimental setup" --top-k 8
```

Để dùng thư mục khác:

```bash
paper-rag ingest --pdf-dir /duong/dan/toi/pdfs
```

`--reset` xóa index sinh tự động trước khi nạp lại. Không cần reset khi thêm PDF
mới hoặc cập nhật một PDF: pipeline tự nhận biết SHA-256 của file.

## HTTP API cho Agent

```bash
paper-rag serve --host 127.0.0.1 --port 8000
```

Các endpoint:

- `GET /health`
- `POST /search` với `{"query": "...", "top_k": 6, "source": null}`
- `POST /ask` với `{"question": "...", "top_k": 6, "source": null}`

Ví dụ:

```bash
curl -s http://127.0.0.1:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"Phương pháp được đánh giá trên bộ dữ liệu nào?","top_k":6,"source":"W-Online-payment.pdf"}'
```

Agent Python cũng có thể import trực tiếp:

```python
from local_rag.agent_tool import ask_research_papers

result = ask_research_papers("Đóng góp chính của bài báo là gì?")
```

`agent_tool.py` xuất thêm `TOOL_SCHEMA` theo function-calling schema. Vì vậy Agent
có thể dùng tool mà không phụ thuộc FastAPI.

Hợp đồng tích hợp ổn định và ví dụ handoff cho người làm Agent nằm tại
[`AGENT_INTEGRATION.md`](AGENT_INTEGRATION.md).

## Dạng kết quả

```json
{
  "answer": "Bài báo đề xuất ... [S1]",
  "grounded": true,
  "citations": [
    {
      "label": "S1",
      "title": "Paper title",
      "source": "paper.pdf",
      "page": 3,
      "quote": "...",
      "claim": "...",
      "entailed": true,
      "entailment_reason": "..."
    }
  ],
  "retrieval": []
}
```

Một answer có thể vẫn được trả về với `grounded=false`. Điều đó có nghĩa lớp
audit tìm thấy ít nhất một claim thiếu citation, quote không phải exact span,
hoặc quote chưa entail toàn bộ claim. Consumer/Agent không nên trình bày answer
đó như một kết luận đã được xác minh.

## Cấu hình

| Biến | Mặc định | Ý nghĩa |
|---|---:|---|
| `RAG_PROVIDER` | `auto` | Tự chọn OpenAI hoặc Gemini theo key |
| `RAG_CHAT_MODEL` | Theo provider | Model tổng hợp câu trả lời |
| `RAG_EMBEDDING_MODEL` | Theo provider | Model embedding |
| `RAG_GEMINI_EMBEDDING_DIMENSIONS` | `768` | Kích thước vector Gemini |
| `RAG_INDEX_PATH` | `.rag/index.sqlite3` | SQLite index local |
| `RAG_TOP_K` | `6` | Số nguồn đưa cho LLM |
| `RAG_CHUNK_WORDS` | `360` | Kích thước chunk gần đúng |
| `RAG_CHUNK_OVERLAP_WORDS` | `70` | Overlap trong cùng một trang |

Có thể đổi provider/model bằng biến môi trường mà không sửa code. OpenAI mặc
định dùng `gpt-5.6-terra` + `text-embedding-3-large`; Gemini mặc định dùng
`gemini-3.6-flash` + `gemini-embedding-2`.

Khi đổi provider, embedding model hoặc số chiều vector, phải chạy lại:

```bash
paper-rag ingest --reset
```

Vector của các provider/model khác nhau không được trộn chung trong một index.

## Kiểm thử

```bash
pytest
```

Các test lõi không gọi OpenAI và không tốn API credit. Kiểm thử end-to-end được
thực hiện sau khi có API key và PDF thật.
