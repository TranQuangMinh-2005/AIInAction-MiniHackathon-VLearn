# Chạy MVP tích hợp

Hệ thống dùng một backend FastAPI:

`Frontend → Agent → Normal (slide) / Research (đúng một local paper)`

RAG nằm độc lập trong `codebase/rag`. Agent chỉ gọi interface của RAG, nên
nhóm Agent có thể thay graph hoặc prompt mà không cần biết PDF parser, chunking
hay SQLite index hoạt động thế nào.

## 1. Cài đặt

Từ thư mục gốc:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cd src/frontend && npm ci && cd ../..
cp .env.example .env
```

Không commit `.env` hoặc API key.

### Dùng Gemini

```dotenv
RAG_PROVIDER=gemini
GEMINI_API_KEY=...
```

### Dùng OpenAI trả phí cho buổi demo

```dotenv
RAG_PROVIDER=openai
OPENAI_API_KEY=...
```

Chat và embedding dùng chung provider. Vì vector của hai provider không tương
thích, sau khi đổi từ Gemini sang OpenAI phải chạy `ingest --reset` đúng một
lần trước demo.

## 2. Nạp hai paper PDF có sẵn

Đặt PDF trong `codebase/rag/data/papers`, rồi chạy:

```bash
.venv/bin/paper-rag ingest --reset
.venv/bin/paper-rag health
```

Lệnh này tạo lại line metadata dùng cho citation. Sau đó có thể thêm paper mà
không reset index.

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

Mở <http://localhost:3000>.

- **Normal**: trả lời theo slide VLearn như hệ thống cũ.
- **Research**: bắt buộc chọn một paper; retrieval và câu trả lời bị khóa vào
  đúng file đó, không trộn paper và không tự web search.
- **Thêm từ arXiv**: nhập chủ đề, tool tải một PDF phù hợp nhất, index vào local
  RAG và tự chọn paper vừa thêm. Các câu hỏi sau đó vẫn chỉ dựa vào paper này.
- Mỗi nguồn hiển thị nhãn, tên file, trang, dòng text trích xuất và quote nguyên
  văn để người demo mở ra kiểm chứng.

Việc đánh số dòng dựa trên text được trích xuất từ PDF, không phải số dòng in
sẵn trên giao diện PDF.

## 4. Kiểm tra nhanh

```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/papers
```

Kiểm tra trực tiếp strict RAG:

```bash
curl -X POST http://localhost:8000/api/papers/ask \
  -H 'Content-Type: application/json' \
  -d '{
    "question":"What models are proposed and what are the main results?",
    "source":"W-Online-payment.pdf"
  }'
```

`/api/papers/ask` có grounding audit nên phù hợp test kỹ. Frontend dùng
`/api/chat/stream`: retrieve một lần rồi stream một lần gọi model để demo nhanh.
Nếu embedding tạm lỗi/quota, local paper tự fallback sang BM25 offline. Slide
retrieval cũng chạy local nên backend không chờ embedding API lúc khởi động.

Nếu backend ở URL khác, tạo `src/frontend/.env.local`:

```bash
NEXT_PUBLIC_AGENT_API_URL=http://localhost:8000
```

## 5. Kịch bản demo 5 phút

Khởi động trước giờ demo, chạy health và mở sẵn UI.

1. Chọn **Normal**, hỏi: `AI là gì theo nội dung bài học?`
2. Chọn **Research** → chọn `W-Online-payment.pdf`, hỏi:
   `Ba mô hình được đề xuất là gì và kết quả giảm tổn thất chính là bao nhiêu?`
3. Mở một citation để chỉ rõ `Trang`, `dòng` và `Trích nguyên văn`.
4. Đổi sang paper Wallet, hỏi:
   `Paper sử dụng mô hình nào và giảm false alarm bằng cách nào?`
5. Nhập một chủ đề ngắn ở ô arXiv, bấm **Thêm**, đợi thông báo đã index; paper
   mới được tự chọn. Hỏi một câu chỉ có trong paper mới và mở citation.

Nên nhập thử đúng chủ đề arXiv dự định demo trước buổi trình bày để xác nhận
paper kết quả đầu tiên phù hợp và thời gian tải PDF ổn. Không cần gọi arXiv lại
khi paper đã nằm trong danh sách.

## 6. Điểm cải thiện so với VLearn cũ

- Có lựa chọn rõ ràng giữa slide Q&A và scientific-paper research.
- Research không còn trộn nguồn: người dùng biết chính xác paper nào đang được
  dùng.
- Có tool arXiv thật để mở rộng kho local ngay trên giao diện.
- Citation kiểm chứng được tới trang, dòng và quote thay vì chỉ hiển thị tên
  tài liệu.
- Fast path chỉ dùng một lần sinh câu trả lời, phù hợp demo ngắn.
