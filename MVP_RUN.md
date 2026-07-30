# Chạy MVP tích hợp

Hệ thống dùng một backend FastAPI duy nhất:

`Frontend → Agent → slide retrieval / local paper RAG / arXiv`

RAG vẫn là package độc lập trong `codebase/rag`; Agent chỉ gọi interface
`ask_research_papers(...)`, không phụ thuộc vào chi tiết index hay PDF parser.

## 1. Cài đặt

Từ thư mục gốc:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cd src/frontend && npm ci && cd ../..
```

Tạo `.env` ở thư mục gốc (hoặc tiếp tục dùng `codebase/rag/.env`):

```bash
cp .env.example .env
```

Điền `GEMINI_API_KEY`. Không commit file `.env`.

## 2. Nạp paper PDF

Chép PDF vào `codebase/rag/data/papers`, rồi:

```bash
.venv/bin/paper-rag ingest --reset
.venv/bin/paper-rag health
```

Nếu index hiện có đã đúng thì không cần ingest lại.

## 3. Chạy backend và frontend

Terminal 1:

```bash
PYTHONPATH=src/agent .venv/bin/uvicorn server:app \
  --app-dir src/agent --host 127.0.0.1 --port 8000
```

Terminal 2:

```bash
cd src/frontend
npm run dev
```

Mở <http://localhost:3000>. Bật **Research** để dùng fast path:

- Câu hỏi nêu tên PDF đã index → retrieve local paper.
- Câu hỏi không chọn local PDF → tìm tối đa hai paper trên arXiv.

Mỗi câu chỉ đi theo một nhánh để tránh nhiều API call nối tiếp trong demo.
Trong smoke test local, hai nhánh đều hoàn tất trong khoảng 2-3 giây; thời
gian thực tế vẫn phụ thuộc mạng và quota API.

## 4. Kiểm tra nhanh

```bash
curl http://localhost:8000/api/health

curl -X POST http://localhost:8000/api/papers/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"What models are proposed in W-Online-payment?"}'
```

`/api/papers/ask` là route chẩn đoán RAG đầy đủ, có grounding audit nên chậm
hơn. Giao diện sử dụng `/api/chat/stream` với retrieve-only fast path rồi gọi
Gemini một lần để thời gian phản hồi phù hợp demo.

Nếu model Gemini chính bị rate-limit, Agent tự thử
`gemini-3.1-flash-lite`, sau đó `gemini-2.5-flash-lite`. Nếu embedding API
bị giới hạn, local PDF tự chuyển sang BM25 offline.

Nếu backend chạy ở URL khác, tạo `src/frontend/.env.local`:

```bash
NEXT_PUBLIC_AGENT_API_URL=http://localhost:8000
```

## 5. Checklist demo 5 phút

Khởi động backend/frontend trước giờ demo và mở sẵn
<http://localhost:3000>. Chạy:

```bash
curl http://localhost:8000/api/health
```

Health phải hiện `slide_pages: 58`, `documents: 2`, `chunks: 99`.

Ba câu đã smoke test:

1. Normal: `AI là gì theo nội dung bài học?` — khoảng 3,7 giây.
2. Research local: `Trong bài W-Online-payment, ba mô hình được đề xuất là
   gì và kết quả giảm tổn thất chính là bao nhiêu?` — khoảng 2,2 giây.
3. Research arXiv: `Tìm các paper về retrieval augmented generation và tóm
   tắt đóng góp chính` — khoảng 2,7 giây.

Với local PDF, luôn nhắc đúng tên file/paper trong câu hỏi để router không
nhầm sang arXiv. Không dùng `/api/papers/ask` trên sân khấu vì route này chạy
thêm grounding audit, dành cho kiểm tra chất lượng sau demo.

Nên chạy thử câu arXiv một lần trước demo; kết quả thành công được cache trong
backend để lần hỏi lại không phụ thuộc vào arXiv API.
