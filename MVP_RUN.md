# Chạy MVP tích hợp

Hệ thống dùng một backend FastAPI:

`Frontend → Agent → Normal (slide) / Research (slide → ArXiv → local RAG)`

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
- **Research mặc định**: viết lại câu hỏi thành truy vấn độc lập từ lịch sử và
  ngữ cảnh slide, tìm nhiều ứng viên trên arXiv rồi rerank theo title/abstract.
  Với câu hỏi tổng quan, hệ thống ưu tiên survey/tutorial/paper nền tảng thay vì
  biến thể hẹp. Chỉ sau khi chọn được một arXiv ID cụ thể, hệ thống mới dùng PDF
  local làm cache hoặc tải, index và trả lời từ full text.
- **Focus paper (tùy chọn)**: chọn một paper khi muốn kiểm thử hoặc chỉ hỏi sâu
  đúng tài liệu đó. Không cần chọn paper để gửi câu hỏi Research.
- **Thêm từ arXiv**: nhập chủ đề, tool tải một PDF phù hợp nhất, index vào local
  RAG và chọn paper vừa thêm làm nguồn focus.
- Mỗi nguồn hiển thị nhãn, tên file, trang, dòng text trích xuất và quote nguyên
  văn để người demo mở ra kiểm chứng.

Nếu API chính thức của arXiv trả `429`, discovery tự fallback qua kết quả tìm
kiếm chỉ giới hạn ở domain `arxiv.org`; PDF và bằng chứng cuối vẫn lấy từ arXiv.

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
2. Chọn **Research**, giữ nguồn ở `Tự động tìm paper phù hợp trên arXiv`, hỏi
   một kiến thức vượt quá slide, ví dụ:
   `Retrieval-Augmented Generation giúp giảm hallucination như thế nào?`
3. Mở citation để chỉ rõ paper được tìm tự động, `Trang`, `dòng` và
   `Trích nguyên văn`.
4. Chọn `W-Online-payment.pdf` để minh họa focus paper, hỏi:
   `Ba mô hình được đề xuất là gì và kết quả giảm tổn thất chính là bao nhiêu?`
5. Nếu còn thời gian, nhập một chủ đề ngắn ở ô arXiv, bấm **Thêm**, rồi hỏi
   một câu trên paper vừa được chọn.

Nên kiểm tra kết nối arXiv và OpenAI trước buổi trình bày. Auto Research vẫn
tìm và rerank động theo từng chủ đề; paper local không tự được chọn chỉ vì có
vài từ khóa trùng. Khi người dùng chọn rõ một paper trong dropdown, hệ thống
mới bỏ qua tìm kiếm arXiv và khóa retrieval vào paper đó.

## 6. Điểm cải thiện so với VLearn cũ

- Có lựa chọn rõ ràng giữa slide Q&A và scientific-paper research.
- Research tự mở rộng kiến thức ngoài slide bằng paper khoa học, không yêu cầu
  học viên phải biết hoặc chọn paper trước.
- Vẫn có focus paper để kiểm thử hai PDF golden set hoặc học sâu một tài liệu.
- Có tool arXiv thật để mở rộng kho local ngay trên giao diện.
- Citation kiểm chứng được tới trang, dòng và quote thay vì chỉ hiển thị tên
  tài liệu.
- Fast path chỉ dùng một lần sinh câu trả lời, phù hợp demo ngắn.
