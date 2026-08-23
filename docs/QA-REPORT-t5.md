# QA Report — t5 · Regression toàn bộ flow sau redesign (VLearn)

**Người test:** QA2 (vlearn-ux-team) · **Ngày:** 24/08 · **Trạng thái:** HOÀN TẤT — **9/10 PASS, 1 FAIL là B1 đã biết (không tính lỗi mới)**

## Phạm vi & phương pháp

- Checklist 10 mục theo chỉ đạo captain. Dùng **script CDP nhỏ** (Node + Chrome DevTools Protocol, không puppeteer suite — theo yêu cầu "không suite lớn").
- App: `http://localhost:3001` (dev server Next 16.2.12 Turbopack khởi động mới — **port 3000 đang bị project khác chiếm** `P-187/frontend`).
- Chrome headless **151.0.7922.170**, viewport 1440×900 / 1100×800 / 390×844.
- **Backend agent (`src/agent/server.py`) KHÔNG chạy được trên máy này**: `TypeError: Reviver.__init__() got an unexpected keyword argument 'allowed_objects'` (xung đột phiên bản langgraph/pydantic trong env — xem m-QA3). → Chat được test bằng **mock SSE stream** (chỉ mock tầng mạng, UI logic thật 100%). Code backend không thuộc phạm vi redesign nên không ảnh hưởng kết luận.
- Kết quả đo trên **code hiện tại** (đã gồm thay đổi 23:27 — kho học liệu mở rộng 17 tài liệu). Mọi số liệu đều đo DOM thực tế qua CDP.

## Bảng kết quả

| # | Item | Kết quả | Ghi chú chi tiết |
|---|---|---|---|
| 1 | Load 1440px — 3 panel render | ✅ **PASS** | Topbar "COMP2010 — AI Thực Chiến" ✓ · `#sidebar-panel` ✓ · toolbar viewer (doc switcher + zoom + note) ✓ · `#chat-panel` ✓ · PDF d1 render 29 trang, text layer 1525–1911 spans ✓ · indicator "Trang 1/29" ✓ |
| 2 | Chat mở mặc định ≥1280 | ❌ **FAIL (B1 đã biết)** | `aria-expanded=false`, panel width 0 — đúng blocker B1 của QC (useState(false) vô điều kiện, page.tsx). **Không tính là lỗi mới**; đang chờ Dev sửa ở t7. |
| 3 | Toggle sidebar + đổi doc d1/d2 | ✅ **PASS** | Mở sidebar = 256px ✓ · chọn "Day 2" → chip **D02** + PDF d2 load ✓ · đổi doc qua F5 switcher dropdown (17 options = 17 tài liệu mới thêm) → chip **D01** trở lại ✓ · đóng sidebar = 0px ✓ |
| 4 | Zoom fit/−/%/+ | ✅ **PASS** | Fit = **143%** → Phóng to = **158%** → Thu nhỏ = **143%** → bấm % = reset **100%** ✓ |
| 5 | Bôi đen text → popup Hỏi AI | ✅ **PASS** | Chọn text trong text layer → popup "**Hỏi AI**" hiện (mũi tên + debounce 80ms) ✓ · click → **chat mở 384px** + input tự điền `Giải thích: "AI IN ACTION Day 1…"` ✓ |
| 6 | Gõ câu → gửi → typing + Dừng | ✅ **PASS** | Send enabled sau khi gõ ✓ · typing: 3 dot bounce + status "Đang tìm trong slide… Xs" + đồng hồ giây + **nút Dừng** thay nút gửi ✓ · input clear ✓ · stream giả lập → trả lời đầy đủ + **2 citation chips** ✓ · **Dừng giữa chừng**: abort đúng — giữ phần đã stream ("Xin chào!"), typing tắt, nút Gửi trở lại, KHÔNG error banner, dot topbar "Tutor đang trả lời" tắt ✓ |
| 7 | Mode Normal/Research | ✅ **PASS** | Research: `aria-pressed=true`, config card hiện (select nguồn paper + ô import arXiv + nút Thêm), header "Research · tự động tìm paper trên arXiv", placeholder "Hỏi sâu hơn — Research sẽ tìm paper…" ✓ · về Normal: config ẩn, aria-pressed đúng ✓ |
| 8 | Citation chip + jump-to-page | ✅ **PASS** ⚠️ | Click chip "D1 - Trang 3" → **page-flash** trên `#d1-page-3` ✓ + scroll tới trang (scrollTop 0→1144) ✓. **⚠️ "Trang X/29" live-update không verify được**: IntersectionObserver không deliver callback trong headless session này (đã chứng minh bằng IntersectionObserver probe độc lập — kể cả div fixed hiển thị rõ). Không phải lỗi app (xem Môi trường). |
| 9 | Responsive 1100px + 390px | ✅ **PASS** | **1100px**: chat thành overlay — pill mép phải "Mở trợ lý AI" ✓, mở = 384px + backdrop ✓, đóng bằng click backdrop ✓. **390px**: sidebar overlay — pill "Mở danh sách slide" ✓, mở = 256px + backdrop ✓, đóng (✕) trượt ra x=-256 ✓, chat pill vẫn hiện ✓ |
| 10 | Console errors | ✅ **PASS** | 0 console.error / 0 exception app; 0 failed request (đã loại noise môi trường: HMR ws khi truy cập 127.0.0.1, AbortError khi đổi doc giữa chừng tải PDF, script inject của QA) |

## Kiểm tra bổ sung (ngoài checklist)

- **Nút Dừng (F8)**: verify đầy đủ — xem ghi chú item 6. Toàn bộ chuỗi AbortController hoạt động đúng.
- **Kho học liệu mới (17 tài liệu)**: sidebar hiện 17 mục ✓; mở doc "Day 1 … (bản full)" → chip `D01`, indicator **"Trang 1/78"**, render đủ 78 page ✓ (path + totalPages lấy đúng từ `slideDocs`).

## Kết luận

**Không phát hiện lỗi chức năng MỚI sau redesign.** Mọi flow chính hoạt động: render 3 panel, chuyển tài liệu, zoom, selection→Hỏi AI, chat stream + typing + dừng, mode Research/Normal, citation jump (scroll + highlight), responsive overlay. Chỉ tồn tại **B1 (chat mặc định đóng ≥1280)** — đã có trong QC report, chờ t7.

## Quan sát minior (không block, gửi PO/Dev tham khảo)

- **m-QA1 (dữ liệu)**: kho học liệu mới có **2 nhóm trùng code hiển thị**: d1 & d3 cùng "D01", d2 & d4 cùng "D02". Citation label kiểu "D1 - Trang X" sẽ **không phân biệt** bản short vs bản full → jump-to-page có thể nhảy nhầm doc. Đề xuất đặt code duy nhất hoặc mapping citation rõ ràng.
- **m-QA2 (môi trường)**: truy cập app qua `127.0.0.1:3001` bị Next 16 chặn dev resources (cần `allowedDevOrigins` trong next.config) → trong dev luôn truy cập qua `localhost`. Không ảnh hưởng production.
- **m-QA3 (môi trường)**: backend agent không start được: `langgraph` thiếu tương thích (Reviver `allowed_objects`) với pydantic hiện tại trong env anaconda → cần venv đúng (repo có `.venv/`) để chạy E2E chat thật; khuyến nghị Dev/PO verify 1 lần chat thật với backend để chốt.

## Ghi chú môi trường test (đã loại trừ — KHÔNG phải lỗi app)

1. **Chrome 151 transition freeze**: `transition: width` từ 0 → `calc(var(--spacing) * N)` (pattern Tailwind v4) **đóng băng ở 0px** (repro trên trang HTML tối thiểu độc lập). Ảnh hưởng mở panel ở desktop trong Chrome này. Đã test bằng cách tắt transition riêng 2 panel (final state vẫn assert đầy đủ). QC session trước screenshot panel mở bình thường → nghi là browser regression theo bản Chrome (auto-update). **App-side mitigation đã có sẵn: M2 (bỏ width transition theo DESIGN.md §4.5) đang chờ Dev t7 — fix xong sẽ loại luôn trigger.** Khuyến nghị re-verify trên Chrome thật của user sau t7.
2. **IntersectionObserver không deliver callback** trong headless session (probe độc lập xác nhận) → không verify được live-update "Trang X/Y"; giới hạn test, không phải lỗi app.
3. **Smooth scroll không chạy** trong headless session (direct `scrollTo({behavior:'smooth'})` = 0) → jump-to-page verify bằng ép `behavior:'auto'` (wiring + scroll + flash OK).

## Files

- Script test: `/tmp/vlearn-qa2/qa-run.mjs` (kèm debug 1–29 + ảnh evidence `/tmp/vlearn-qa2/*.png`, kết quả JSON `/tmp/vlearn-qa2/qa-results.json`)

---

## BỔ SUNG — Pass với backend thật (localhost:8001) · 24/08

Captain xác nhận backend thật chạy ở **8001** (app đã cấu hình đúng: `.env.local` → `NEXT_PUBLIC_AGENT_API_URL=http://localhost:8001`, verified chuỗi inline trong client bundle). Đã chạy pass bổ sung trên Chrome headless sạch (không mock) trực tiếp qua UI:

| Mục | Kết quả | Ghi chú |
|---|---|---|
| `/api/health` | ✅ 200 | backend thật nhận diện: "VLearn Agent API" (paths: health, papers, import-arxiv, papers/ask, chat, chat/stream) |
| `/api/papers` | ✅ 200 `{"papers":[]}` | danh sách rỗng — graceful, không lỗi |
| Research mode | ✅ | select hiện "Tự động tìm paper phù hợp trên arXiv" + "Chưa có paper — nhập chủ đề để thêm", không error banner |
| `/api/papers/ask` | ✅ 200 | JSON graceful: `{"answer":"Không tìm thấy bằng chứng phù hợp...","grounded":false}` |
| Chat UI (gửi câu thật) | ✅ graceful | → **error banner "Không thể kết nối đến AI server. Vui lòng thử lại." + nút Thử lại**; welcome giữ nguyên; typing tắt; **0 console error, 0 exception, không crash** |
| Nguyên nhân gốc chat | ⚠️ backend-side | Network trace CDP: POST `8001/api/chat/stream` → **RES 200 text/event-stream → `net::ERR_INCOMPLETE_CHUNKED_ENCODING`** — server đóng kết nối chunked không đúng chuẩn (thiếu terminal chunk) khi LLM fail vì **key giả**; browser coi là lỗi mạng → UI chạy đúng nhánh graceful. Theo quy ước captain: **ghi nhận, không tính là FAIL** của UI. Lưu ý cho Dev/PO: khi có key thật, generator sẽ yield token bình thường nên SSE chuẩn; nếu muốn chắc, backend nên trả `data: {"error": ...}` + đóng stream đúng chuẩn thay vì đóng chunked bẩn khi lỗi sớm. |

**Kết luận bổ sung:** UI xử lý đúng mọi nhánh lỗi thật (mất kết nối, key giả, papers rỗng) — không lỗi mới. Phần chat nội dung thật (key thật) **chưa test được do thiếu key thật** (theo quy ước captain: ghi nhận, không phải fail).

⚠️ Lưu ý môi trường: **không tắt/khởi động lại gì trên 8001 (của user)** — chỉ dùng request để test. Port 3000 đang bị project khác chiếm; 3002/8001 của user, không đụng.

---

# RE-RUN SAU FIX — t13 (QA3) · 24/08

**Người test:** QA3 (vlearn-ux-team) · **Trạng thái:** ✅ **6/6 PASS — CHỐT KẾT QUẢ CUỐI**
**Phạm vi:** re-regression nhanh sau t7 (Dev2: B1/M1/M2 + minors) + t11 (Dev3: lô minor) — theo chỉ đạo captain, KHÔNG test lại toàn bộ 10 mục (QA2 đã làm vòng đầu).
**Phương pháp:** script CDP nhỏ `/tmp/vlearn-qa3/qa-rerun.mjs` (mẫu QA2 `/tmp/vlearn-qa2/qa-run.mjs`) trên dev server `http://localhost:3001` (hot-reload, đã có toàn bộ fix). Chrome headless 151 CDP :9312 (target mới mỗi run, KHÔNG đụng page khác). Chat dùng mock SSE tầng mạng (UI logic thật 100%) — giữ nguyên cách vòng đầu. **KHÔNG inject workaround width-transition** (t13 phải đo motion thật sau M2).
**Evidence:** `/tmp/vlearn-qa3/t13-final-1440.png` · `t13-1100.png` · `t13-390.png` (+ JSON kết quả `qa-rerun-results.json`); ảnh Dev2 `/tmp/vlearn-shots/t3-fix/` (default chat-open · both-open · research).

| # | Item | Kết quả | Chi tiết đo được |
|---|---|---|---|
| 1 | **B1** — chat mở mặc định ≥1280 | ✅ **PASS** (trước: FAIL) | Load mới 1440px, KHÔNG click: `aria-expanded=true`, `#chat-panel` offsetWidth = **384px** = rectWidth 384px. Init `useEffect(innerWidth>=1280 → setChatOpen(true))` — đúng Q4 user chốt, không hydration mismatch. |
| 2 | **M2** — panel đóng/mở không freeze (motion) | ✅ **PASS** | `transition-property` computed của cả `#chat-panel` lẫn `#sidebar-panel` = **"transform, translate, scale, rotate" — KHÔNG chứa width** (đúng DESIGN.md §4.5). Đóng chat: width giữ **384px suốt** (mẫu {w:384,x:1370}→{w:384,x:1440}), trượt hẳn ra ngoài viewport (x=1440), KHÔNG kẹt/freeze. Mở lại: đạt 384px ngay. Lỗi freeze Chrome-151 ghi ở vòng đầu (width calc transition) đã biến mất vì không còn animate width. |
| 3 | **M1** — text-mono render Geist Mono | ✅ **PASS** | Element "Trang 1/29" → computed `font-family="Geist Mono", "Geist Mono Fallback", ui-monospace, …` (body = Geist sans + Outfit fallback). Rule `.text-mono { font-family: var(--font-mono) }` hoạt động đúng. |
| 4 | Responsive 1100px + 390px không vỡ | ✅ **PASS** | **1100px**: chat tự về overlay — pill "Mở trợ lý AI" ✓, mở = overlay w=384 + backdrop ✓. **390px**: pill "Mở danh sách slide" ✓, sidebar mở w=256 + backdrop ✓, đóng trượt ra x=**-256** (translate-x thuần) ✓, chat pill vẫn hiện ✓. |
| 5 | Console errors = 0 | ✅ **PASS** | Toàn run (load, toggle, resize 2 lần, chat stream, Stop giữa chừng): **0 console.error, 0 exception, 0 failed request** (đã loại noise như vòng đầu: HMR-dev ws, AbortError do stop/đổi doc). |
| 6 | Flow gõ → gửi → typing + Dừng → kết quả | ✅ **PASS** | Send enable sau khi gõ ✓ · typing: 3 dot + status "Đang tìm trong slide… 0s" + nút Dừng ✓ · input clear ✓ · stream → trả lời đầy đủ + **2 citation chips** ✓ · **Dừng giữa chừng**: abort giữ phần đã stream ("Xin chào! Đây là câu trả lời…"), typing tắt, nút Gửi trở lại, **KHÔNG error banner** ✓. |

## Kết luận t13

**6/6 PASS — toàn bộ findings của vòng QC/QA đã fix và re-verify sạch.**
- Blocker **B1** (chat mở mặc định ≥1280): **ĐÃ HẾT** — mở 384px đúng spec.
- Major **M2** (animate width): **ĐÃ HẾT** — chuyển sang translate-x thuần, không còn bóp chữ, không freeze; đúng §4.5.
- Major **M1** (text-mono sai font): **ĐÃ HẾT** — Geist Mono áp đúng.
- Không phát hiện **lỗi chức năng mới** nào sau fix: responsive 2 breakpoint, chat flow (stream/typing/Stop/citations), console sạch.
- **CHỐT:** app sẵn sàng cho báo cáo user vòng 1 + chuyển giao. Các mục ngoài scope giữ nguyên kết luận vòng đầu (chat key thật chưa test được — thiếu key, ghi nhận không fail; IntersectionObserver live-update trang — hạn chế môi trường headless, không phải lỗi app).