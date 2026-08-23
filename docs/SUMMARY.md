# Tóm tắt tiến độ — VLearn Reader Hackathon

## Bối cảnh
Dự án nằm trong **Batch03-K4-AI-Product-Hackathon**, hướng **A — VLearn**. 
Vấn đề: AI tutor trên VLearn chỉ trả lời dựa trên nội dung slide, không research được bên ngoài → 30.5% câu hỏi thất bại.

**Chiến tuyến:** VLearn AI Tutor — chatbot không trả lời được câu hỏi sâu hơn slide.

---

## Cấu trúc thư mục hiện tại

```
Batch03-K4-AI-Product-Hackathon/
├── 01-de-bai.md, 02-guide.md, 03-template-ai-spec.md, 04-rubric.md, README.md   # Tài liệu hackathon gốc
├── data/vlearn-pack/               # Chatlog + transcript + slide PDF (data pack)
├── tham-khao/                      # JTBD Playbook + worksheet
├── phan-tich-chatlog.md            # Phân tích 2,522 dòng chatlog
├── report.md                       # Report tổng hợp cho hackathon
├── frontend/                       # 🌐 Next.js reader clone (đã push GitHub)
│   ├── src/
│   │   ├── app/
│   │   │   ├── globals.css         # Tailwind + VLearn color vars
│   │   │   ├── layout.tsx          # Root layout
│   │   │   └── page.tsx            # Main page — 3 panel layout
│   │   └── components/
│   │       ├── Sidebar.tsx         # Panel trái — danh sách slide (2 PDF thật)
│   │       ├── SlideViewer.tsx     # Panel giữa — render PDF (react-pdf), zoom, ghi chú
│   │       ├── PDFViewer.tsx       # PDF renderer (dynamic import, ssr:false)
│   │       └── ChatPanel.tsx       # Panel phải — chat AI (toggle, mock response)
│   ├── public/
│   │   ├── d1-slide-hackathon.pdf  # Day 1 slide (29 trang)
│   │   └── d2-slide-hackathon.pdf  # Day 2 slide (29 trang)
│   └── package.json                # Next.js 16, react-pdf, tailwindcss 4
└── agent/                          # 🧠 LangGraph Agent (Python, mới tạo skeleton)
    └── agent/
        ├── state.py                # AgentState TypedDict
        ├── graph.py                # StateGraph: search_slide → decide_search → web_search → generate_answer
        ├── nodes/
        │   ├── slide_search.py     # Node: tìm trong slide
        │   ├── web_search.py       # Node: research bên ngoài (web)
        │   └── answer.py           # Node: tổng hợp câu trả lời
        └── tools/
            └── web_search.py       # Tool: Tavily/SerpAPI search (mock, chưa tích hợp)

GitHub: https://github.com/mronion112/Batch03-K4-AI-Product-Hackathon (nhánh main)
```

---

## Frontend — đã làm xong

### Layout 3 panel
```
┌──────────┬──────────────────┬──────────┐
│ Sidebar  │   Slide Viewer   │ Chat AI  │
│ (trái)   │   (PDF scroll)   │ (phải)   │
└──────────┴──────────────────┴──────────┘
```

### Các nút tương tác
- **Sidebar toggle**: nút `Slide` dọc bên trái (giống style nút AI), nút X trên sidebar, overlay click
- **Chat toggle**: nút `AI` dọc bên phải, panel trượt vào/ra
- **Zoom**: +/- trong header SlideViewer
- **Ghi chú**: toggle panel note bên phải slide
- **Chọn slide**: Sidebar có 2 PDF (Day 1 & Day 2), chọn để đổi slide

### UI state
- Sidebar mặc định đóng, mở bằng nút Slide hoặc hamburger top bar
- Chat panel đóng, mở bằng nút AI bên phải
- PDF render bằng react-pdf (tất cả trang scroll liên tục, không pagination)
- Chat hiện trả lời mock (3 câu mẫu ngẫu nhiên)

### Vấn đề đã gặp & giải quyết
- **DOMMatrix SSR error**: PDFViewer import bằng `dynamic(() => import(...), { ssr: false })`
- **pdfjs worker version mismatch**: Dùng `import.meta.url` thay vì CDN URL
- **Reload liên tục**: Bỏ IntersectionObserver/scroll tracking → PDFViewer giờ render thuần, không theo dõi trang

---

## Agent — skeleton đã có, chưa tích hợp

### Luồng xử lý (graph.py)
```
User hỏi → search_slide → decide_search
                              ├─ Đủ → generate_answer → trả lời
                              └─ Thiếu → web_search → generate_answer → trả lời
```

### Việc cần làm tiếp
1. **Tích hợp LLM thật** vào các node (gọi Gemini/OpenAI API)
2. **Tích hợp web search** (Tavily API hoặc SerpAPI)
3. **Kết nối frontend ↔ agent**: ChatPanel gửi request → agent trả về câu trả lời thật (qua API route hoặc FastAPI)
4. **Chạy server**: `cd frontend && npm run dev` (port 3000)
5. **Push code lên GitHub** khi có thay đổi: `git add . && git commit -m "..." && git push origin main`

### Cách chạy
```bash
# Frontend
cd Batch03-K4-AI-Product-Hackathon/frontend
npm run dev
# → http://localhost:3000

# Agent (Python — chưa có server, mới có skeleton)
cd Batch03-K4-AI-Product-Hackathon/agent
# Cần tạo virtualenv + cài langgraph, sau đó viết API server
```
