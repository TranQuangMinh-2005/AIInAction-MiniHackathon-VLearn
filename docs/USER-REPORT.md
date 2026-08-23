# USER-REPORT — VLearn Redesign vòng 1

> **Soạn bởi:** PO (vlearn-ux-team) · **BẢN HOÀN CHỈNH — toàn bộ task t1–t13 đã đóng** · QC 19/19 + QA 6/6 PASS, 0 lỗi mở
> **App chạy sẵn cho user xem:** http://localhost:3002 (frontend production, build mới nhất) · backend http://localhost:8001

---

## 1. Đã làm gì

Redesign toàn diện UI/UX app học VLearn theo **hướng A "Calm Focus Editorial"** — đúng 4 quyết định bạn đã chốt:

| Quyết định | Hiện trạng |
|---|---|
| Giữ navy **#134D8B** | ✓ Giữ nguyên, mở rộng thành scale brand-50→950, 1 accent duy nhất (bỏ hẳn màu amber của Research — phân biệt bằng icon + cấu trúc) |
| Không dark mode | ✓ Chỉ light mode chuẩn (dark mode để phase sau) |
| Calm & compact | ✓ Chat airy (14/22, ≤65 ký tự/dòng), sidebar/toolbar gọn (control 36px, chip 12px) |
| Giữ 3-panel, chat mở mặc định ≥1280px | ✅ **ĐÃ SỬA** — chat mở sẵn ≥1280px (re-verify PASS) |

**Trước → Sau** (ảnh đối chứng; bộ SAU = ảnh sau-fix cuối, tài liệu kèm):

| Trạng thái | TRƯỚC | SAU (cuối — sau fix) |
|---|---|---|
| Mặc định 1440px (chat mở sẵn) | `/tmp/vlearn-shots/01-default-collapsed.png` | `/tmp/vlearn-shots/t3-fix-qc/01-default-1440.png` |
| Mở cả 2 panel | `/tmp/vlearn-shots/03-both-open.png` | `/tmp/vlearn-shots/t3-fix-qc/02-both-open-1440.png` |
| Mode Research | `/tmp/vlearn-shots/04-research-mode.png` | `/tmp/vlearn-shots/t3-fix/03-research-mode-1440.png` |
| Trả lời + citation | — | `/tmp/vlearn-qc/09-answered-citation-1440.png` |
| Giao diện hẹp 1100px (chat overlay) | — | `/tmp/vlearn-shots/t3-fix-qc/03-narrow-1100.png` |
| Mobile 390px | — | `/tmp/vlearn-qc/06-mobile-390.png` |

**Thay đổi chính:**
- **Font premium:** Geist + Geist Mono (self-host, đủ dấu tiếng Việt) — trước đây font khai báo nhưng không load, render bằng font mặc định.
- **Hệ design system hoàn chỉnh:** token màu/radius(4–16px)/shadow nhuốm navy/motion 3 cubic-bezier — bỏ viền xám 1px generic, bỏ emoji → icon Phosphor đồng bộ.
- **3 panel theo spec:** top bar navy 2 nút toggle rõ ràng (Học liệu / Trợ lý AI) · sidebar item card vuông góc + selected/hover/focus đầy đủ · viewer: doc switcher, cụm zoom Fit/−/%/+, skeleton tải, error + Thử lại, popup "Hỏi AI" khi bôi đen, ghi chú localStorage 3 trạng thái · chat: welcome + 3 chip gợi ý, segmented Normal/Research, card citation "BẰNG CHỨNG" bấm nhảy trang + flash highlight, typing 3-dot + đồng hồ giây, nút Dừng khi stream, clear-chat có xác nhận.
- **Responsive:** chat không còn biến mất dưới 1280px — thành overlay + backdrop, nút AI hiện mọi kích thước; sidebar overlay trên mobile.
- **Accessibility:** focus-visible 34/34, aria-label/aria-expanded đủ, contrast đo đạt WCAG AA (4.5:1–9.6:1).

## 2. Kiểm định chất lượng (đã chạy thực tế)

- **Visual QC (t4):** design system khớp spec từng token; các hạng mục PASS lớn: màu sạch 1 accent, font Geist load thật, states + a11y gần đủ bộ, F1/F2/F6/F9 verified. Phát hiện 1 blocker + 2 major + ~17 minor → **đã sửa hết** (t7 + t11, build PASS).
- **Chức năng QA (t5):** regression 10 mục trên Chrome thật: **9/10 PASS, 0 lỗi chức năng mới** — render, chuyển tài liệu (17 doc), zoom, bôi đen→Hỏi AI, chat stream + Dừng đúng, Research/Normal, citation jump, responsive 1100/390px, console sạch.
- **Re-regression sau fix (t13):** **6/6 PASS** — B1 chat mở mặc định ✓ · M2 motion (chỉ transform, không freeze) ✓ · M1 font-mono = Geist Mono ✓ · responsive 1100/390px ✓ · console 0 lỗi ✓ · chat flow (typing + Dừng + citation, abort giữ text) ✓. Chi tiết: QA-REPORT-t5.md mục "RE-RUN SAU FIX".
- **Visual re-verify vòng 2 (t8 + t12):** **cực kỳ sạch** — B1/M1/M2 PASS (3 trạng thái chuẩn đạt, ảnh `/tmp/vlearn-shots/t3-fix-qc/`); lô minor sau t11: **19/19 mục đóng** (bảng chi tiết QC-REPORT-t4.md "QC-pass lô minor"); PO2 đối chiếu độc lập xác nhận (annex cùng file). Toàn bộ findings vòng 1 của QC đã đóng hết.

## 3. Đang xử lý / còn lại

**ĐÃ SỬA XONG — vòng fix đợt 1 (t7 + t11, build PASS, re-verify toàn bộ PASS):**
- **B1 (blocker):** chat mặc định ĐÓNG trên desktop → **đã sửa**: mở sẵn ≥1280px (QA3 verify: aria-expanded=true, panel 384px khi load 1440px không click).
- **M1:** text-mono chưa áp Geist Mono → **đã sửa** (QA3 verify: computed font = Geist Mono).
- **M2:** transition width vi phạm chuẩn motion → **đã sửa**: chỉ transform/translate, đóng/mở không freeze (QA3 verify).
- **~17 minor:** bo góc bubble, hairline tint navy, kích thước pill, stagger animation, token caption thay hardcode, m11 giữ gap-6 theo draft A, m18 bỏ Outfit… → **đã sửa hết và re-verify 19/19 PASS** (t7 + t11 + t12), ảnh đối chứng sau-fix: `/tmp/vlearn-shots/t3-fix/` + `/tmp/vlearn-shots/t3-fix-qc-minor/`, evidence QA3: `/tmp/vlearn-qa3/`.

**Đề xuất cho vòng sau (chờ bạn chọn ưu tiên):**
1. **OCR** cho `day03-design-pattern-react.pdf` — 66/71 trang là ảnh scan → AI chưa đọc được nội dung bài này.
2. **Mã tài liệu trùng** D01/D02 (bản short vs bản full 78 trang) — citation có thể nhảy nhầm doc khi kho học liệu đã có 17 tài liệu.
3. **SSE status thật** — hồi âm từ backend theo từng bước (tìm → index → viết) thay vì frontend tự suy đoán theo thời gian.
4. **Kế hoạch nâng cấp multi-agent**: Arch2 đã viết `AGENT-UPGRADE-PLAN.md` (387 dòng, chỉ docs) — sẵn sàng để bạn duyệt chia nhỏ.
5. Dark mode (đã chốt để phase sau) + persist ghi chú lên server nếu muốn đồng bộ nhiều máy.
6. Polishing rất nhỏ (backlog QC2, không chặn): bổ sung `active:scale-[0.98]` cho 2 nút "Thử lại" ghost 11px (import-arxiv + error banner — ChatPanel:588/817); 2 chip danger 11px giữ nguyên (bậc overline); verify press feedback composer sau rebuild (source đã có patch).

**Lưu ý vận hành:** app đang chạy ở http://localhost:3002 với toàn bộ chức năng; chat AI sẽ trả lỗi graceful cho tới khi bạn đặt API key thật vào `.env` (key giả hiện tại) — không phải lỗi của bản cài đặt.

## 4. Câu hỏi feedback

1. Mở thử app tại **http://localhost:3002** (mở sidebar, chuyển tài liệu, bôi đen text → Hỏi AI, thử Research) — ấn tượng chung thế nào? Có điểm nào muốn chỉnh ngay (màu, font, mật độ)?
2. Sau khi xem ảnh trước/sau ở §1 — đã đúng cảm giác "calm focus" edtech premium bạn mong muốn chưa?
3. Vòng sau làm gì trước trong danh sách P2 ở §3? (gợi ý: OCR + mã tài liệu + SSE status)

## 5. Quyết định chi tiết đã chốt (cuối vòng 1 — PO)

| # | Vấn đề | Quyết định | Lý do |
|---|---|---|---|
| m11 | Gap giữa các trang PDF: DESIGN cũ ghi 16px, draft A thể hiện 24px | **Theo draft A — giữ 24px** (DESIGN.md §4.3/§5.3 đã cập nhật cho khớp) | Draft A là chuẩn visual user đã chốt; 24px cho slide "thở" hơn, đúng vibe calm |
| m18 | Fallback font Outfit (phòng hờ khi Geist thiếu glyph) | **Bỏ hẳn** — fallback = system-ui (DESIGN.md §4.2 đã ghi chú) | Geist latin-ext đã verify cover dấu tiếng Việt; thêm Outfit chỉ là font dependency phòng hờ |
| B1/M1/M2 + minors | Fix QC đợt 1 | **ĐÃ SỬA XONG + RE-VERIFY PASS TOÀN BỘ** (t7+t11 build PASS · t13 QA 6/6 PASS · t8+t12 QC 19/19 đóng) | Ưu tiên blocker trước, đúng quyết định Q4 của bạn |
| Citation label bản full (m-QA1, Giai đoạn 2) | Phân biệt tài liệu full Day1/Day2 với bản short (trước trùng "D01/D02" → jump nhầm doc) | **"D1 Full" / "D2 Full"** — short giữ "D1"/"D2"; legacy D3–D16 decode giữ nguyên | Rõ nghĩa với học viên (không ký hiệu lạ "-F"), đủ ngắn cho chip, khớp ngôn ngữ sidebar "bản full" |