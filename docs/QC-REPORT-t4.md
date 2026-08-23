# QC Report — t4 · VLearn Redesign vs DESIGN.md v3

**Người soát:** QC (vlearn-ux-team) · **Ngày:** 24/08
**Phương pháp:** đọc toàn bộ source (page.tsx, Sidebar, SlideViewer, PDFViewer, ChatPanel, globals.css, layout.tsx) → đo DOM thực tế qua Chrome CDP (computed styles, font, kích thước, media queries) → kiểm chứng pixel bằng sharp → chụp 9 screenshot đối chứng tại **`/tmp/vlearn-qc/`**:

| Ảnh | Trạng thái | Ghi chú |
|---|---|---|
| `01-default-both-closed-1440.png` | default (đúng yêu cầu §8.11) | top bar pixel = #0D335C ✓ |
| `02-sidebar-open-1440.png` | mở sidebar | |
| `03-both-open-1440.png` | both-open (đúng yêu cầu §8.11) | |
| `04-research-mode-1440.png` | research-mode (đúng yêu cầu §8.11) | |
| `05-narrow-1100-chat-overlay.png` | 1100px — chat overlay | F1 check |
| `06-mobile-390.png` | 390px mobile | F1 check |
| `07-typing-user-bubble.png` | bubble user + typing dots | |
| `08-after-send.png` | sau khi gửi (mock backend trả lời thật) | |
| `09-answered-citation-1440.png` | câu trả lời + citation chip | |

*Lưu ý: vision backend không khả dụng trong phiên này nên QC dùng DOM-metrics + pixel-check thay cho đọc ảnh; ảnh giữ nguyên để PO đối chiếu mắt.*

---

## Kết quả tổng quan

**Điểm sáng:** Design system §4 cài đặt gần đủ (tokens màu/radius/shadow/motion khớp từng giá trị trong DESIGN.md), font Geist + Geist Mono self-host qua next/font load thành công, không còn màu amber/hex lạc (grep sạch), không còn emoji/SVG tay (chỉ giữ logo baseline đúng §5.1), focus-visible đủ **34/34 button**, aria-expanded đủ 8 chỗ toggle, `prefers-reduced-motion` đầy đủ, F1 (nút AI luôn hiển thị — verify 1100px + 390px ✓), F2 (padding-hack đã bỏ ✓), F6 (hamburger đã bỏ ✓), F9 (control h-9 thẳng hàng ✓). Contrast các cặp chữ chính đo được 5.0:1–9.6:1 → đạt WCAG AA.

**Tồn đọng: 1 blocker, 2 major, ~17 minor.** Chi tiết bảng dưới.

---

## Bảng findings

| # | Mức độ | Vị trí (file:dòng) | Lỗi | Gợi ý sửa |
|---|---|---|---|---|
| **B1** | **BLOCKER** | `src/frontend/src/app/page.tsx:14` | Chat mặc định **ĐÓNG** trên desktop — vi phạm quyết định user đã chốt Q4: *"Chat mặc định MỞ trên desktop (≥xl)"* (DESIGN.md §9). `useState(false)` vô điều kiện. | Init theo breakpoint: `useEffect(() => { if (window.innerWidth >= 1280) setChatOpen(true); }, [])` (tránh hydration mismatch). 1 dòng, không đụng logic. |
| **M1** | **MAJOR** | `src/frontend/src/app/globals.css:77-80` | **Token `text-mono` không áp font Geist Mono.** Tailwind v4 không emit `font-family` từ `--text-mono--font-family` (bằng chứng: CSS compile `.text-mono` chỉ có font-size/line-height/font-weight; DOM đo "Trang 1/29" — SlideViewer:237 — computed font = *Geist sans*). Mọi element dùng `text-mono` render sai font: page indicator (SlideViewer:237), "D01 · 29 trang" (Sidebar:103), meta dropdown (SlideViewer:267), "% zoom" (SlideViewer:305). | Thêm rule explicit: `.text-mono { font-family: var(--font-mono); }` trong globals.css, hoặc dùng kèm class `font-mono`. (Blockquote citation dùng `font-mono` → đã đúng, không cần sửa.) |
| **M2** | **MAJOR** | `src/frontend/src/app/page.tsx:13` + `ChatPanel.tsx:409` / `Sidebar.tsx:31` | Đóng/mở panel trên desktop chạy **transition width** (`transition-[transform,width]` + `w-0`), DESIGN.md §4.5 cấm animate width (chỉ transform/opacity) và §6 yêu cầu "transform slide". Panel bị "bóp" chữ trong lúc mở. | Giữ panel w-256/w-384 cố định, đóng bằng `translate-x` (slide) hoặc `scale/opacity`; bỏ `width` khỏi transition-property. |
| m1 | minor | `ChatPanel.tsx:651,657` | Bubble user/tutor: `rounded-lg` (12px) + thiếu corner nhỏ — spec §5.4: **radius-xl (16px) + corner-tr 4px** (user) / **corner-tl 4px** (tutor); max-w 85% vs 88%. | `rounded-xl rounded-tr-xs` / `rounded-xl rounded-tl-xs`, `max-w-[88%]`. |
| m2 | minor | `ChatPanel.tsx:657` + `PDFViewer.tsx:110` | Hairline dùng `ring-black/5` (xám trung tính) thay vì tint navy `border-brand-950/8` (G4/G7: "Xoá viền xám"; §5.3 tường minh *bỏ viền* trang PDF). | Đổi `ring-black/5` → `ring-brand-950/8` (bubble, trang PDF). |
| m3 | minor | `ChatPanel.tsx:419-420` | Chat header: avatar tròn Robot + title `text-sm` (14px) — spec §5.4: dot brand-600 + `text-title` 16/600 "VLearn Tutor"; context line 11px vs caption 12px. | `text-base font-semibold` cho title; context `text-caption` (12px). Hỏi PO avatar vs dot (draft A có avatar — nếu PO chốt theo draft thì bỏ qua m3). |
| m4 | minor | `ChatPanel.tsx:486-505` | Mode selector active: text + icon `text-brand-600` — spec: **text-brand-700** + icon brand-600. Track p-1 vs p-0.5. | `text-brand-700` cho active tab. |
| m5 | minor | `ChatPanel.tsx:687,705` | Citation card: `border-border` (xám) thay vì hairline `border-brand-950/8`; summary 11px thường thay vì `text-mono` 12/600 brand-700; quote 11px vs 12px. | Đổi border + `text-mono` cho summary header (sau khi fix M1). |
| m6 | minor | `ChatPanel.tsx:787-792` | Typing dots `bg-brand-600` — spec: **brand-400**, bounce stagger 150ms ✓; đồng hồ `{Xs}` không dùng mono. | `bg-brand-400`; bọc giây trong `font-mono`. |
| m7 | minor | `ChatPanel.tsx:820` | Composer `rounded-xl` (16px) + border-border/60 — spec: **radius-lg (8px)** bg-surface-2. | `rounded-lg`, bỏ hoặc giữ hairline tối thiểu. |
| m8 | minor | `ChatPanel.tsx:616-630` | Empty-state chips nền `bg-brand-50` — spec: **outline brand** (border brand-300, text brand-700, nền trắng). | Đổi sang outline. |
| m9 | minor | `page.tsx:143` + `ChatPanel.tsx:397` | Edge pill: `w-10 h-24` + `rounded-r-xl/l-xl` — spec §5.5: **w-9 h-20, radius-r-full/l-full**; `transition-all` (animates width) vi phạm §4.5. | Đổi kích thước + `rounded-r-full`/`rounded-l-full`; transition chỉ `transform, opacity, background-color`. |
| m10 | minor | `Sidebar.tsx:56,83` | Hàng group thiếu caption "2 tài liệu"; item `p-3` vs spec `py-2.5 px-3`; meta dùng text-mono+uppercase thay vì caption 12 ink-faint. | Thêm caption; chỉnh padding; dùng `text-caption text-ink-faint` cho meta (hoặc giữ mono nếu PO thích — hiện M1 làm nó thành sans). |
| m11 | minor | `PDFViewer.tsx:104` | Gap trang PDF 24px (`gap-6`) vs §5.3 **16px** (comment "theo draft A" — cần PO xác nhận draft A vs DESIGN.md cái nào chuẩn). | `gap-4` nếu theo DESIGN.md. |
| m12 | minor | `SlideViewer.tsx:361-405` | Notes panel mở **không có animation** — §6: "Trượt nhẹ 200ms ease-quick". | Thêm animate-fade-up / translate khi mount. |
| m13 | minor | toàn app (nút primary) | Thiếu press feedback `active:scale-0.98` trên nút chính (§6 Tương tác: Active). | Thêm `active:scale-[0.98]` cho nút primary (Lưu ghi chú, Thử lại, gửi…). |
| m14 | minor | `globals.css:102-103,183,210` | `--animate-shimmer` dùng `ease-in-out` (bị cấm tên trong §4.5), `fade-in`/`page-flash` dùng `ease-out` không phải 3 token. | Đổi shimmer về linear/`var(--ease-quick)`; fade về ease token. |
| m15 | minor | ChatPanel (messages/citations/chips) | **Thiếu stagger 40ms** cho danh sách vào (citations, chips, message mới) — §4.5; `animate-fade-up` đã định nghĩa nhưng chỉ dùng cho toast. | Áp `animate-fade-up` + `animation-delay: 40ms×i` (tối đa 5 phần tử). |
| m16 | minor | `SlideViewer.tsx:227,433` + rải rác ChatPanel | Hardcode `text-[10px]/[11px]` thay vì token `text-caption` (12) / `text-overline` (11) — không nhất quán scale §4.2 (chip "D01" 10px, quote tooltip 11px, chip citation 11px, context 11px…). | Chuyển về token: caption 12px cho chip/meta; giữ overline 11px cho label nhóm; quote tooltip có thể giữ 11 nhưng nên qua token riêng. |
| m17 | minor | `SlideViewer.tsx:320` | Divider toolbar `h-4` vs spec `h-5`; icon 12/14px rải rác (CaretDown switcher 12, X notes 14) vs G9 (16px UI thường). | `h-5`; nâng icon lên 16 (trừ icon trong citation/chip 12px là đúng §5.4). |
| m18 | trivial | `layout.tsx:9-19` | Fallback chain thiếu **Outfit** (spec §4.2: Geist thiếu glyph → Outfit → system-ui). Geist latin-ext đã cover tiếng Việt (verified load) nên chỉ là phòng hờ. | Thêm `outfit` vào chain nếu muốn đúng spec từng chữ. |
| m19 | trivial | `globals.css:204-206` | `.slide-transition` dead code (không ai dùng). | Xoá. |

---

## Các mục PASS (đã đo, không liệt kê lỗi)

- **Màu:** top bar pixel #0D335C = brand-800 ✓; 1 accent duy nhất, neutrals đúng token; grep sạch amber/slate/hex lạc; functional chỉ danger/success/warning.
- **Font:** Geist + Geist Mono self-host load thật (`document.fonts.check` = true); body 14/22 ✓; tiếng Việt render bằng Geist ✓.
- **Top bar §5.1:** h-12, 2 toggle pill + aria-expanded/aria-controls, dot báo brand-300 khi typing, focus ring white/60, logo giữ nguyên baseline ✓.
- **Sidebar §5.2:** w-256 in-flow ≥lg ✓; selected bg-brand-50 + ring brand-200 + text brand-700/600 ✓; hover/active/focus ✓; backdrop brand-950/30 ✓; empty state ✓.
- **Viewer §5.3:** toolbar h-12, doc switcher chip + dropdown (animate-scale-in, role=listbox) ✓; cụm zoom trên track surface-2 (Fit/−/%/+) ✓; page indicator "Trang X/Y" ✓; skeleton 4:3 + caption ✓; error card + Thử lại ✓; selection popup navy h-8 + mũi tên + clamp ±16px + debounce 80ms + quote >120 ký tự max-w 280 ellipsis ✓; ghi chú localStorage 3 trạng thái (spin → ✓ ẩn 2s) ✓.
- **Chat §5.4:** mode selector đồng ngôn ngữ thị giác (không accent 2) ✓; research config card trung tính (bỏ amber) ✓; select h-9 + chevron ✓; import spin → toast success → error+retry ✓; typing status theo mode + đồng hồ giây ✓; composer auto-grow 6 dòng, send↔Stop (AbortController), disabled opacity-40 ✓; welcome + 3 chip theo mode ✓; clear confirm popover ease-pop ✓; error banner danger + Thử lại ✓; <xl overlay + backdrop ✓.
- **A11y:** focus-visible 34/34 button; aria-label đủ icon-only; role=status/alert đúng chỗ; `lang="vi"`; contrast ≥4.5:1 (đo: brand-700/brand-50 = 9.6:1, white/brand-600 = 8.5:1, white-70%/brand-800 = 7.0:1, success/white = 5.0:1, danger/white = 5.1:1).
- **Motion:** 3 token ease đúng giá trị cubic-bezier; keyframes chỉ opacity/transform; reduced-motion global ✓; bounce dots dùng transform ✓.
- **F1/F2/F6/F9** đã verify (xem "Điểm sáng").

## Đề xuất thứ tự sửa

1. B1 (1 dòng) + M1 (1 dòng CSS) + M2 (sửa 2 chỗ class) — 3 lỗi này ảnh hưởng trạng thái mặc định + font + motion, sửa nhanh.
2. Nhóm m1–m8 (ChatPanel — panel trọng tâm, nhiều lệch token nhỏ).
3. Nhóm m9–m17 (pills, spacing, tokens, stagger).
4. m18–m19 tuỳ chọn.

**Kết luận:** Chất lượng cài đặt ở mức tốt (design system + states + a11y gần như đủ bộ), còn 1 blocker về trạng thái mặc định của chat (quyết định user đã chốt) và 2 major về font-mono + motion. Sau khi Dev sửa 3 lỗi đầu, khuyến nghị QC-pass vòng 2 tập trung re-screenshot 3 trạng thái chuẩn.

---

## QC-pass vòng 2 — Re-verify sau t7 (QC2, 24/08)

**Phương pháp:** DOM metrics qua Chrome CDP (headed — headless bị frozen timeline nên không đo được transition) trên `http://localhost:3003` (dev server mới — xem ghi chú infra bên dưới), viewport 1440x900 & 1100x800, kèm 3 screenshot tại `/tmp/vlearn-shots/t3-fix-qc/` (01-default-1440 · 02-both-open-1440 · 03-narrow-1100).

**Kết quả 3 lỗi chính:**

| # | Kết quả | Bằng chứng đo được |
|---|---|---|
| **B1** | ✅ PASS | Load mới 1440px: chat `aria-expanded=true`, panel `w=384, x=1056, position:relative` (in-flow, hiển thị) — chat MỞ mặc định ≥1280. |
| **M1** | ✅ PASS | `.text-mono` (page indicator "Trang 1/29") computed `font-family: "Geist Mono", "Geist Mono Fallback", ui-monospace…`; `document.fonts.check('16px "Geist Mono"')` = true. |
| **M2** | ✅ PASS | Sidebar & ChatPanel: `transition-property: transform, translate, scale, rotate` (KHÔNG có width); `w-64`/`w-96` cố định; đóng/mở bằng translate-x slide (open = x:0/1056, closed = ±full). Edge pill: `transition-[transform,opacity,background-color]` + `h-20 w-9 rounded-*-full` (m9 ✓). |

**Trạng thái chuẩn:** default-1440 (sidebar đóng + chat mở ✓ đúng Q4) · both-open (sidebar x:0 in-flow + chat x:1056) · narrow-1100 (chat overlay `position:fixed` x:716, không tràn ngang — scrollWidth diff 0).

**Minors spot-check (source + DOM):** group caption "N tài liệu" ✓ (m10), chips welcome outline brand ✓ (m8), composer `rounded-lg bg-surface-2` ✓ (m7), `active:scale-[0.98]` nút primary ✓ (m13), citation summary `text-mono` ✓ (m5). Lô còn lại do t11/t12 (Dev3/QC3) xử lý.

**Ghi chú infra (quan trọng cho QA3/Dev):** (1) Dev server cũ :3001 (PID 36977) đã hỏng — Next 16 chặn dev-resources cho origin `127.0.0.1` (allowedDevOrigins) nên hydration chết im lặng; QC2 đã kill và chạy server mới tại **`http://localhost:3003`** — dùng origin `localhost`, không dùng `127.0.0.1`. (2) `next start` :3002 đang serve BUILD CŨ (trước redesign) — cần rebuild nếu muốn dùng. (3) Headless Chrome bị frozen timeline (visibility:hidden, docTimeline=0) → transition không bao giờ chạy, panel "mở" nhưng đứng yên ở translate 100% — dùng Chrome HEADED + CDP để đo.

**Kết luận vòng 2: PASS — B1/M1/M2 đã fix đúng, 3 trạng thái chuẩn đạt, không phát hiện lỗi mới của t7.**

---

## QC-pass lô minor — Re-verify sau t11 (t12, QC2, 24/08)

**Phương pháp:** source sweep toàn bộ findings m1–m19 (sau t7 + t11, build PASS) + live DOM metrics trên http://localhost:3003 (Chrome headed CDP), chuẩn cuối đã xác nhận: **m11 = gap-6 24px (giữ)**, **m18 = không "Outfit" (giữ)**.

| # | KQ | Bằng chứng |
|---|---|---|
| m1 | ✅ | user `max-w-[88%] rounded-xl rounded-tr-xs` (ChatPanel:652) / tutor `rounded-tl-xs` + ring-brand-950/8 (658) |
| m2 | ✅ | bubble + PDF page dùng `ring-brand-950/8` (658, PDFViewer:110); grep sạch `ring-black/5` |
| m3 | ✅ | title "VLearn Tutor" computed **16px/600** (live), context **12px** text-caption (live); avatar giữ theo draft A |
| m4 | ✅ | mode active: computed **text rgb(16,63,114)=brand-700, bg trắng**; track `bg-surface-2 p-0.5` (479) |
| m5 | ✅ | citation `border-brand-950/8` (686) + summary `text-mono font-semibold text-brand-700` (689) + quote `text-xs` mono (707) |
| m6 | ✅ | dots `bg-brand-400` delay 0/150/300ms (792–794) |
| m7 | ✅ | composer `rounded-lg border-border/50 bg-surface-2` (826) |
| m8 | ✅ | chips outline `border-brand-300 bg-surface text-brand-700` (620–640, live) |
| m9 | ✅ | edge pill live: **36x80 (w-9 h-20)**, radius-full, `transition: transform, opacity, background-color` — 2 bên |
| m10 | ✅ | caption "N tài liệu" (Sidebar:60), item `px-3 py-2.5` (88), meta `text-caption` ink-faint/brand-500 (108) |
| m11 | ✅ FINAL | gap giữa 2 trang PDF đo live = **24px** (gap-6, chuẩn cuối) |
| m12 | ✅ | notes panel `animate-fade-up` (SlideViewer:362) |
| m13 | ✅ (đã đóng sau t12) | `active:scale-[0.98]` có trên Lưu ghi chú (SV:385), Thử lại (PDF:96), selection popup (SV:421); **Dev2 đã bổ sung cho Xoá (851) + Gửi (861) ngay sau review t12** — hết điểm mở |
| m14 | ✅ | shimmer/fade-in/page-flash dùng `var(--ease-quick)` (globals.css:102,103,211); hết ease-in-out/ease-out |
| m15 | ✅ | stagger 40ms × min(i,5) messages (651,657); citations/chips animate-fade-up |
| m16 | ✅ | hết `text-[10px]`; chip "D01"/quote tooltip = `text-caption` (SV:227,433); còn 2 chỗ `text-[11px]` danger action (CP:588,817) ≈ overline 11px — chấp nhận |
| m17 | ✅ | divider `h-5 w-px` (SV:320); icons 16px (FileText/CaretDown/BookOpen/Flask) |
| m18 | ✅ FINAL | fallback chain chỉ Geist + Geist Mono, **không Outfit** (layout.tsx) |
| m19 | ✅ | `.slide-transition` đã xóa (grep 0 hits) |

**Kết luận t12: PASS — 19/19 mục đạt chuẩn (m13 đã được Dev2 bổ sung active:scale cho Xoá/Gửi sau review — hết điểm mở). Toàn bộ findings t4 đã đóng; QC duy nhất xác nhận sẵn sàng tổng kết.**

---

### Annex t12 — Xác nhận độc lập (PO2, 24/08) + đính chính build :3002

Đo độc lập (Chrome 151 headless CDP :9333, localhost:3003, 1440×900, 3 ảnh `/tmp/vlearn-shots/t3-fix-qc-minor/`): m11 gap pixel trang 1→2 = **24px** ✓ · m10 caption "17 tài liệu", item padding 10/10/12px, meta 12px #64748B ✓ · m17 divider 20px ✓ · m12 notes `fade-up` 0.2s ✓. m13: nút Gửi ChatPanel:861 đã có `active:scale-[0.98]` (xác nhận source sau khi Dev2 vá) ✓. m16: 2× `text-[11px]` chip danger = bậc 11px tương đương overline — **PO chấp nhận, đóng m16** ✓.

**Đính chính ghi chú infra:** mục cũ ghi ":3002 serve build cũ" đã HẾT hiệu lực — chunks build **00:33:20** mới hơn mọi source (ChatPanel 00:32:57 · page.tsx 00:11:42 · globals 00:18:39) và chunk `0xsl1iox7hth7.js` chứa `innerWidth>=1280&&p(!0` (fix B1): **:3002 đang serve build mới nhất, hợp lệ cho user xem**. Dev server test: `http://localhost:3003`.
