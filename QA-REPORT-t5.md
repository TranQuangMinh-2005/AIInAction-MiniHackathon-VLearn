
---

## T28 VERIFY — Citation paper nhảy trang (24/08, sau t28)

**Môi trường**: build prod `npm run build` + `next start :3001` (test port, CORS OK 3000/3001/3002) + **Chrome headed** CDP (9313). KHÔNG test trên :3002 — Dev2 đang sửa file liên tục → HMR reload loop (215 navigations/3 phút) — không stable. Backend :8001 (restart 02:14, có t28 + fix VX13/14). Câu research: "Multiview Transformers video recognition".

| # | Item | Kết quả | Ghi chú chi tiết |
|---|---|---|---|
| 1 | Research → citation_details [S1] arxiv-*.pdf | ✅ **PASS** | Trả lời đầy đủ + **4 card "Bằng chứng"** (nút "Xem trang 1/1/3/2"), source `arxiv-2201.04288v4.pdf`, trace tool=papers; 0 banner |
| 2 | Click "Xem trang N" → viewer PAPER + scroll/flash + badge | ❌ **FAIL — BUG THẬT** | Badge **"Paper · arxiv-2201.04288v4.pdf"** + nút **Thoát** hiện ĐÚNG, nhưng PDF **404**: viewer gọi `http://localhost:3001/api/papers/arxiv-2201.04288v4.pdf/pdf` → **frontend KHÔNG proxy /api** (Next chỉ có rewrite `/backend/*`→8000 cũ) → error card "Không thể tải slide", 0 trang paper → **không scroll/flash trang**. Backend 8001 OK: `GET /api/papers/arxiv-2201.04288v4.pdf/pdf` → **200 (664KB PDF)** (lưu ý: source đã gồm `.pdf` nên URL đầy đủ có `/pdf/pdf`). **Gốc rễ: SlideViewer.tsx:66 dùng relative URL `/api/papers/{source}/pdf` → phải thêm rewrite/proxy `/api/papers/* → :8001` hoặc dùng absolute agentApiUrl.** Đây chính là lý do Dev t28 không verify UI được |
| 3 | Nút "Thoát" → về slide, không vỡ layout | ✅ **PASS** | Badge mất, **29 trang slide trở lại**, chat 384px, toolbar viewer OK, không error overlay |
| 4 | Slide citation (D-x Trang N) vẫn nhảy | ✅ **PASS (mechanism) ⚠️** | Hỏi "giải thích 4 chiến lược tối ưu prompt" → chip **"D1 - Trang 6"** ✓ → click → **page-flash trên #d1-page-6 ✓**. ⚠️ scroll không di chuyển trong Chrome này (smooth-scroll quirk Chrome 151 — đã ghi ở t5; flash tức là handler chạy đúng) — không phải regression t28 |
| 5 | Console errors | ✅ **PASS** | **0 console error, 0 exception**; PDF 404 chỉ là network fail (react-pdf xử lý bằng error card) — 1 mục network 404 ghi ở item 2 |

**Kết luận T28**: 4/5 PASS, **1 FAIL chặn (item 2)** — luồng UI paper mode (badge/Thoát) đúng nhưng PDF không tải được do thiếu proxy → dev cần fix (1 dòng rewrite trong next.config.ts: `/api/papers/:path*` → `http://localhost:8001/api/papers/:path*` hoặc absolute URL). Sau fix: re-run item 2 (kỳ vọng pages render + scroll/flash đúng trang theo citation_details.page).
