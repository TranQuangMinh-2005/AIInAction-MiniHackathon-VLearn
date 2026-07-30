# Chạy MVP tích hợp

Hệ thống dùng một backend FastAPI duy nhất:

`Frontend → Agent → slide retrieval / local paper RAG / arXiv / web`

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

Mở <http://localhost:3000>. Bật **Research** để Agent dùng local paper
RAG, arXiv và web khi slide không đủ thông tin.

## 4. Kiểm tra nhanh

```bash
curl http://localhost:8000/api/health

curl -X POST http://localhost:8000/api/papers/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"What models are proposed in W-Online-payment?"}'
```

`/api/papers/ask` là route chẩn đoán trực tiếp. Giao diện sử dụng
`/api/chat/stream`; trong Research mode, graph Agent gọi cùng RAG tool đó.

Nếu backend chạy ở URL khác, tạo `src/frontend/.env.local`:

```bash
NEXT_PUBLIC_AGENT_API_URL=http://localhost:8000
```
