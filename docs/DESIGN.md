# DESIGN.md — VLearn Research Tutor · Redesign UI/UX (v3 — ĐÃ CHỐT)

> **Tác giả:** PO (vlearn-ux-team) · **Phiên bản:** v3 — user đã duyệt 4 quyết định (xem §9). Spec này là chuẩn cài đặt cuối cùng.
> **Phạm vi:** Chỉ spec. Dev implement theo file này; mọi lệch spec phải hỏi lại PO.
> **Baseline screenshot hiện trạng:** `/tmp/vlearn-shots/01-default-collapsed.png` → `05-pdf-content.png`

### Quyết định user đã chốt (24/08)
| # | Câu hỏi | Quyết định |
|---|---|---|
| Q1 | Màu thương hiệu | **A — GIỮ #134D8B đã hiệu chỉnh** (không đổi sang blue/teal); Research phân biệt bằng icon + cấu trúc, KHÔNG màu thứ 2 |
| Q2 | Dark mode | **A — KHÔNG làm đợt này** (phase sau). Chỉ light mode chuẩn. |
| Q3 | Mật độ UI | **A — "Calm & compact"**: chat airy, sidebar/toolbar compact |
| Q4 | Layout | **A — GIỮ 3-panel**: chat mặc định MỞ trên desktop, sidebar 256px, toggle rõ ràng, bỏ trùng lặp hamburger/nút Slide |

## 0. Superdesign Canvas (bắt buộc dùng trong luồng thiết kế)

- **Project:** `VLearn UX Redesign` · projectId `d8f07226-9b65-425e-9760-173bf7f78b2b`
- **Canvas:** https://superdesign.dev/teams/fcc9e8fe-1a8d-49bf-a14c-7a19858fe5a7/projects/d8f07226-9b65-425e-9760-173bf7f78b2b
  (gửi user xem: thêm `?live=1`)
- **Drafts (reference pixel cho Dev):**
  | Draft | ID | Preview | Vai trò |
  |---|---|---|---|
  | Baseline — UI hiện tại (pixel-perfect) | `c120e3e0-e908-4f75-a27e-3fce5e18a296` | https://p.superdesign.dev/draft/c120e3e0-e908-4f75-a27e-3fce5e18a296 | Ground truth đối chứng |
  | **A — Calm Focus Editorial** *(ĐÃ CHỌN — Q3 "Calm & compact")* | `3a405864-ea54-47b7-b8d9-5978d168605e` | https://p.superdesign.dev/draft/3a405864-ea54-47b7-b8d9-5978d168605e | **Hướng cài đặt chính** — khớp spec §5 (1 accent, Research = icon + cấu trúc) |
  | B — Compact Power Console *(lưu so sánh)* | `47e296cd-9c8a-4600-8d83-9d91d97aa660` | https://p.superdesign.dev/draft/47e296cd-9c8a-4600-8d83-9d91d97aa660 | Hướng thay thế (dense/dev-tool) |
- **State:** `.superdesign/resume.json` (target `/`) · init context: `.superdesign/init/*` · design system: `.superdesign/design-system.md`
- **Quy tắc dùng cho Dev:** mở draft **A** trên canvas làm reference pixel chính khi cài đặt §5; nếu cần chỉnh draft dùng `iterate-design-draft --mode replace` (KHÔNG branch lung tung); nếu cần thiết kế thêm màn hình dùng `execute-flow-pages`. User đã chọn hướng A → `activeDraftId` = draft A.

---

## 1. Design Read (1 dòng)

**Page kind:** Study workspace 3-panel (Sidebar học liệu · SlideViewer · ChatPanel AI tutor) — "power tool" học tập: đọc slide + đối thoại học thuật song song, citation trace được đến trang/dòng/quote.
**Audience:** Học viên khoá AI Thực Chiến — người Việt, 20–30 tuổi, tư duy dev/data, quen dùng ChatGPT/Notion/Linear.
**Vibe:** Edtech premium — **calm focus**: UI lùi lại, nội dung học dẫn dắt; đáng tin như tài liệu khoa học; không hào nhoáng, không template AI.
**Design family:** *Editorial workbench* — độ chính xác + motion tinh của Linear, cấu trúc citation-trust của NotebookLM, palette kỷ luật 1 accent.

---

## 2. Audit hiện trạng — bảng lỗi → hướng sửa

### 2.1 Lỗi generic (design-skill checklist)

| # | Lỗi hiện tại | Chỗ | Hướng sửa |
|---|---|---|---|
| G1 | Font mặc định: `'Be Vietnam Pro'` khai báo trong CSS **nhưng chưa từng load** → render bằng system-ui | `globals.css` | Self-host **Geist** qua `next/font/google` (subsets latin+latin-ext, weights 400–700); mono: **Geist Mono**. Không Inter. |
| G2 | `#134D8B` dùng tràn lan không có scale (bar, nút, link, chip cùng 1 hex) | toàn app | Dựng scale brand-50→950, dùng đúng bậc theo vai trò (§4.1) |
| G3 | **2 accent xung đột**: navy + amber-500 cho Research; amber mang nghĩa "cảnh báo" cho tính năng chính | ChatPanel mode selector + research block | **Chỉ 1 accent** (navy). Research phân biệt bằng icon + cấu trúc, không bằng màu thứ 2. Amber/đỏ chỉ cho cảnh báo/lỗi thật. |
| G4 | Viền 1px xám generic (`border-slate-200`) khắp nơi — nhìn như khung wireframe | mọi panel/card | Bỏ viền làm công cụ phân tách chính: dùng **tương phản bề mặt** (surface vs canvas) + hairline tint navy `border-brand-950/8` chỉ khi bắt buộc |
| G5 | Emoji làm icon UI (📖 🔬 📄 🔗 ✅) lẫn với SVG thủ công stroke khác nhau | ChatPanel | Icon thư viện **Phosphor** (`@phosphor-icons/react`), weight regular/duotone nhất quán; xoá toàn bộ emoji + SVG tay |
| G6 | Thiếu gần hết các state: không skeleton (spinner trần), không empty state chat, không error+retry, không focus-visible, hover nghèo | toàn app | Implement đủ bộ state theo §6 |
| G7 | Shadow xám trung tính (`shadow-lg/xl/2xl` tuỳ tiện), bong bóng tutor xám phẳng | SlideViewer, ChatPanel | Shadow **nhuốm navy** (`rgb(10 41 73 / x%)`), tối đa 2 lớp; tutor bubble = card trắng + shadow-sm |
| G8 | Motion mặc định (transition-transform ease mặc định), không token, không reduced-motion | toàn app | 3 token cubic-bezier riêng (§4.4), chỉ animate transform/opacity, tôn trọng `prefers-reduced-motion` |
| G9 | Icon SVG stroke 2px vẽ tay rải rác, kích cỡ không đồng bộ (12/14/16/18) | toàn app | Phosphor: 16px cho UI thường, 18px cho control chính; weight regular |
| G10 | Không có hệ radius nhất quán (rounded-md/lg/xl lẫn lộn) | toàn app | Shape lock §4.3: card=lg, input=md, bubble=xl+corner 4, chip=full |

### 2.2 Lỗi chức năng/layout (bắt buộc sửa trong redesign)

| # | Lỗi | Chỗ | Hướng sửa |
|---|---|---|---|
| F1 | **Chat biến mất dưới 1280px**: `<div className="hidden xl:block">` bọc cả ChatPanel lẫn nút AI | `page.tsx` | Nút AI luôn hiển thị mọi breakpoint; <xl panel thành overlay + backdrop |
| F2 | Padding-hack lệch kép: `paddingLeft: sidebarOpen ? 280 : 0` trong khi sidebar ≥lg nằm in-flow (w-80=320) | `SlideViewer.tsx` | Chỉ padding khi panel là overlay (<lg sidebar, <xl chat); desktop panel chiếm chỗ thật |
| F3 | Nút "Lưu ghi chú" chết (không xử lý) | `SlideViewer.tsx` | Wire localStorage (không cần backend) hoặc tối thiểu state feedback: đang lưu → Đã lưu ✓ |
| F4 | Research im lặng khi chờ arXiv (tìm → tải → index có thể >10s) → tưởng treo | `ChatPanel.tsx` | Typing status theo bước + đồng hồ giây (§5.4, §7) |
| F5 | Breadcrumb trùng thông tin ở 2 nơi (toolbar viewer + subtitle chat) | 2 component | Toolbar viewer → doc switcher chip; chat subtitle → dòng ngữ cảnh mode |
| F6 | Hamburger ☰ top bar trùng chức năng nút "Slide" cạnh trái | `page.tsx` | Top bar: 2 nút toggle panel rõ ràng (Học liệu / Trợ lý AI) + aria-expanded |
| F7 | Selection popup không clamp biên, dễ nhấp nháy | `SlideViewer.tsx` | Debounce 80ms + clamp ±16px + quote rút gọn khi >120 ký tự |
| F8 | Composer không auto-grow, không nút Dừng khi stream | `ChatPanel.tsx` | Auto-grow tới 6 dòng; đổi nút send → Dừng (AbortController) khi đang stream |
| F9 | Textarea ghi chú + select research lệch chiều cao, nút "Thêm" lệch giữa | 2 chỗ | Chuẩn hoá control h-9 (36px), thẳng hàng baseline |

---

## 3. Tham khảo nền tảng — học gì từ mỗi nơi

| Nền tảng | Học từ họ | Né từ họ |
|---|---|---|
| **NotebookLM** | Citation gắn ngay cạnh câu trả lời, click → nhảy đúng đoạn nguồn; **Suggested questions** ở empty state theo ngữ cảnh tài liệu; bố cục "nguồn trái — chat phải" là đối chứng trực tiếp cho VLearn | Tất cả cùng một tông xám nhạt, thiếu phân cấp → VLearn cần nhịp mạnh hơn (navy header, card trắng) |
| **Perplexity** | Luồng hỏi-đáp tối giản: source chip đánh số [1][2] sau câu trả lời, expand được; mục Related gợi câu tiếp; rất ít chrome | Trang kết quả toàn chữ, không có khu vực đọc tài liệu → VLearn phải giữ slide làm trung tâm |
| **Coursera** | Left-rail điều hướng học liệu phân cấp (module → lesson → trang); giữ vị trí học khi chuyển mục; top bar mỏng | Branding nặng khắp nơi, banner chiếm chỗ |
| **Notion** | Hệ thống học liệu: neutral palette trầm, nội dung dẫn dắt; **callout** để báo trạng thái (rất hợp cho câu hỏi làm rõ của tutor); spacing hào phóng | Quá nhiều chrome config quanh editor |
| **Linear** | **Polish + motion**: token `cubic-bezier(0.2,0,0,1)` snappy 100–200ms; border + micro-shadow thay đổ bóng dày; empty state chăm chút (minh hoạ + hành động); keyboard-first | Phong cách issue-tracker quá dày cho app học → chỉ lấy motion + empty state + độ chính xác |

**Kết luận:** Bố cục/citation ← NotebookLM · luồng hỏi-đáp ← Perplexity · học liệu ← Coursera/Notion · motion/polish ← Linear.

---

## 4. Design Tokens

### 4.1 Palette — 1 accent + 1 họ neutral

**Quy tắc:** MỘT accent duy nhất = VLearn navy (đã hiệu chỉnh saturation). Không có accent thứ 2 — **Research mode phân biệt bằng icon + cấu trúc** (quyết định user Q1). Amber/đỏ chỉ cho cảnh báo/lỗi thật. Neutral: **một họ slate duy nhất** nhuốm xanh (cùng undertone với navy).

```css
@theme {
  /* ACCENT — VLearn Navy (giữ #134D8B làm lõi, mở rộng scale, hiệu chỉnh bão hoà các bậc) */
  --color-brand-50:  #EFF5FB;   /* tint cho selected/ngữ cảnh */
  --color-brand-100: #DEEBF7;
  --color-brand-200: #BDD6EE;
  --color-brand-300: #8FB8E1;
  --color-brand-400: #548DCC;
  --color-brand-500: #2A67A9;
  --color-brand-600: #134D8B;   /* PRIMARY — nút, link, selected (giữ nguyên) */
  --color-brand-700: #103F72;
  --color-brand-800: #0D335C;
  --color-brand-900: #0A2847;
  --color-brand-950: #061A30;

  /* NEUTRAL — một họ slate nhuốm xanh duy nhất */
  --color-canvas:        #F1F4F8;  /* nền viewer (slate nhuốm brand) */
  --color-surface:       #FFFFFF;  /* panel/card */
  --color-surface-2:     #F7F9FC;  /* nền phụ, hover nhẹ */
  --color-border:        #E3E8EF;  /* hairline khi BẮT BUỘC (hạn chế dùng) */
  --color-border-strong: #C9D2DE;
  --color-ink:           #1E293B;  /* body text */
  --color-ink-strong:    #0F172A;  /* heading */
  --color-ink-muted:     #46556A;  /* text phụ */
  --color-ink-faint:     #64748B;  /* placeholder/icon phụ */

  /* FUNCTIONAL — chỉ cho trạng thái thật */
  --color-danger:        #D6222F;  /* lỗi (đồng bộ đỏ logo VLearn) */
  --color-warning:       #B45309;  /* cảnh báo (rate limit, mất kết nối) */
  --color-success:       #15803D;  /* thành công (import xong, đã lưu) */
}
```

**Quy tắc dùng màu:**
- Navy chỉ cho: hành động primary, link, selected, badge ngữ cảnh — gồm cả Research mode (tab active, nút "Thêm" secondary, quote citation). Hover các bậc ±1.
- Tách vùng bằng **tương phản bề mặt** (canvas → surface → surface-2); chỉ thêm hairline `border` khi hai vùng trắng sát nhau và thiếu phân cách.
- Bong bóng user = brand-600; mọi card "tài liệu" (tutor answer, citation) = surface + shadow-sm.

### 4.2 Typography

**Font:** Self-host qua `next/font/google`, **KHÔNG dùng Inter, KHÔNG dùng font mặc định**:
- **Sans — Geist** (primary; subsets `latin`+`latin-ext` bao phủ dấu tiếng Việt; weights 400/500/600/700). Fallback chain: `system-ui`. *(QUYẾT ĐỊNH PO 24/08: bỏ Outfit khỏi chain — Geist latin-ext đã verify render-test dấu tiếng Việt, thêm Outfit chỉ là phòng hờ + 1 font dependency; nếu QA thật phát hiện thiếu glyph → mở lại vấn đề.)*
- **Mono — Geist Mono** (số liệu, citation, quote, đồng hồ đếm giây). Fallback: `JetBrains Mono`.

| Token | Size / LH / Weight / Tracking | Dùng cho |
|---|---|---|
| `text-display` | 28 / 36 / 600 / -0.02em | Tiêu đề lớn (hiếm dùng) |
| `text-title-xl` | 20 / 28 / 600 / -0.01em | Tiêu đề panel chính |
| `text-title` | 16 / 24 / 600 | Header panel, tên tài liệu |
| `text-body` | 14 / 22 / 400 | **Base toàn UI** (chat, list, form) |
| `text-body-sm` | 13 / 20 / 400 | Meta, context line |
| `text-caption` | 12 / 18 / 500 | Số trang, chip |
| `text-overline` | 11 / 16 / 600 / +0.08em uppercase | Label nhóm ("BẰNG CHỨNG", "NGUỒN RESEARCH") |
| `text-mono` | 12 / 18 / 400 · Geist Mono | `Trang 2 · dòng 10–14`, quote, `12s` |

**Đo văn:** Headline có presence (weight 600 + tracking âm nhẹ + màu ink-strong). Body tối đa **~65ch** mỗi dòng — message chat max-w ~65ch (khoảng 620px), không để chữ tràn toàn panel.

### 4.3 Shape lock — 1 hệ radius + spacing

```css
  /* Radius — MỘT hệ thống cho cả app */
  --radius-xs: 4px;   /* corner của bubble (bubble + xs) */
  --radius-sm: 6px;   /* chip nhỏ */
  --radius-md: 8px;   /* input, button, select */
  --radius-lg: 12px;  /* card, slide page, citation card */
  --radius-xl: 16px;  /* bubble chat, panel lớn, popover */

  /* Spacing — base 4px (scale Tailwind mặc định), quy ước cố định: */
  /* gutter panel: p-4 (16) · gap section: space-y-3 (12) · gap trang PDF: 24 (draft A — QUYẾT ĐỊNH PO 24/08) ·
     hit-area icon button tối thiểu 32px · control height chuẩn h-9 (36px) */
```

### 4.4 Shadow — nhuốm màu nền (navy), tối đa 2 lớp

```css
  --shadow-xs:   0 1px 2px rgb(10 41 73 / 0.05);
  --shadow-sm:   0 1px 2px rgb(10 41 73 / 0.06), 0 1px 3px rgb(10 41 73 / 0.08);
  --shadow-md:   0 2px 4px rgb(10 41 73 / 0.06), 0 4px 12px rgb(10 41 73 / 0.09);
  --shadow-lg:   0 4px 8px rgb(10 41 73 / 0.08), 0 8px 24px rgb(10 41 73 / 0.13);
  --shadow-page: 0 1px 2px rgb(10 41 73 / 0.08), 0 4px 16px rgb(10 41 73 / 0.10); /* trang PDF */
```

### 4.5 Motion — chỉ transform/opacity, cubic-bezier riêng

```css
  --ease-quick: cubic-bezier(0.2, 0, 0, 1);        /* hover/color 150ms */
  --ease-panel: cubic-bezier(0.2, 0, 0, 1);        /* panel slide 240ms */
  --ease-pop:   cubic-bezier(0.34, 1.56, 0.64, 1); /* popover scale-in 200ms */
```

- **Cấm** `ease-linear` / `ease-in-out` mặc định. Chỉ animate `transform` + `opacity` (không animate width/height/top/left).
- **Stagger nhẹ:** danh sách (citations, chips, message mới) vào sau nhau 40ms, tối đa 5 phần tử, translateY(4px)→0 + fade.
- `@media (prefers-reduced-motion: reduce)`: tắt mọi transition/animation, giữ opacity cuối.

---

## 5. Redesign Spec — từng panel

> Icon: **Phosphor** (`@phosphor-icons/react`), weight regular, 16px (UI thường) / 18px (control chính). Tên icon gợi ý trong [ ].

### 5.1 Top bar (app)
```
┌────────────────────────────────────────────────────────────────────┐
│ ← Quay lại   [V] COMP2010 — AI Thực Chiến         [◧ Học liệu][⌁ AI] │  h-12 bg-brand-800
└────────────────────────────────────────────────────────────────────┘
```
- Nền `brand-800` (bar "lùi ra sau", nội dung nổi lên). Logo giữ nguyên (vuông trắng + V navy + 3 gạch đỏ).
- Nút "Quay lại" [CaretLeft] ghost trắng/70 → hover trắng, `aria-label="Quay lại"`.
- **Cụm phải = 2 nút toggle panel** (thay hamburger trùng lặp F6): `[SidebarSimple] Học liệu` và `[Sparkle] Trợ lý AI` — pill `px-3 h-8`, `aria-expanded`, active khi panel mở: `bg-white/15 text-white`; idle: `text-white/70 hover:text-white hover:bg-white/10`. Nút AI có **dot báo** (brand-300) khi tutor đang trả lời.
- Focus trên nền navy: `ring-2 ring-white/60 ring-offset-0`.

### 5.2 Sidebar (w-256px desktop; overlay <lg)
```
┌──────────────────────────────┐
│ HỌC LIỆU MÔN HỌC          ✕ │  overline 11/600 ink-faint; ✕ chỉ hiện <lg
├──────────────────────────────┤
│ ▾ AI Thực Chiến — Hackathon   │  hàng group: title 14/600 + "2 tài liệu" caption
│ ┌──────────────────────────┐ │
│ │ ▤ Day 1 — AI & LLM        │ │  SELECTED: bg-brand-50 + ring-1 brand-200,
│ │   Foundation              │ │    text brand-700, icon brand-600, radius-lg
│ │   D01 · 29 trang          │ │  HOVER: bg-surface-2 · ACTIVE: bg-brand-100
│ └──────────────────────────┘ │  FOCUS: ring-2 brand-400 offset-2
│ │ ▤ Day 2 — Xác định…       │ │  IDLE: text ink-muted, icon ink-faint
│ └──────────────────────────┘ │
└──────────────────────────────┘
```
- Thay `border-r-2` dày + viền xám bằng **card bo góc ring brand** (G4, G10).
- Item: `py-2.5 px-3`, icon `[FilePdf]` 16, title truncate 14/500, meta caption 12 ink-faint.
- **Empty state:** `[Files]` + "Chưa có tài liệu nào" (ink-muted) giữa panel.
- Backdrop <lg: fade-in 200ms `bg-brand-950/30`.
- Nút ✕ (mobile) và nút "Slide" cạnh trái giữ nguyên chức năng, bổ sung `aria-expanded`.

### 5.3 SlideViewer
```
┌────────────────────────────────────────────────────────────────┐
│ [Day 1 ▾] AI & LLM Foundation          [⊠ Fit] [−] [100%] [+] │ 📝 │  toolbar h-12
├────────────────────────────────────────────────────────────────┤
│              ┌─────────────────────────────┐                   │
│              │                             │ ← trang PDF: bg-white,│
│              │         SLIDE NỘI DUNG      │    radius-lg,         │
│              │                             │    shadow-page        │
│              └─────────────────────────────┘                      │
│                          (gap 16px)                               │
│              ┌─────────────────────────────┐                      │
│              │         trang tiếp          │                      │
│              └─────────────────────────────┘                      │
└────────────────────────────────────────────────────────────────┘
 canvas: bg-canvas; trang canh giữa; scroll chung (custom-scrollbar)
```
- **Trái toolbar:** doc switcher chip `[CaretDown] Day 1` mở dropdown 2 tài liệu (D1/D2) + tên tài liệu hiện tại 14/600 — sidebar trở thành tuỳ chọn (F5).
- **Phải toolbar:** cụm zoom thống nhất trong 1 track nền surface-2 radius-md: `[CornersOut] Fit-width` → `[Minus]` → `100%` (nút reset, click về 100) → `[Plus]`; nút 32px, icon 16. Divider `w-px h-5 bg-border` rồi đến `[NotePencil]` ghi chú.
- **Zoom:** thêm Fit-width (tính container/page width); giữ giới hạn 0.5–2.0.
- **Trang PDF:** gap **24px** (theo draft A — QUYẾT ĐỊNH PO 24/08: draft A là chuẩn visual user đã chốt, thể hiện 24px; DESIGN cũ ghi 16px nay cập nhật cho khớp), radius-lg, `shadow-page`, `scroll-mt-4` giữ jump-to-page. Xoá viền xám.
- **Loading:** skeleton trang (khối trắng tỉ lệ 4:3 radius-lg, shimmer opacity 60↔100 chu kỳ 1.5s) + caption "Đang tải slide…"; không spinner trần giữa canvas (G6).
- **Error:** card giữa canvas: `[CloudX]` + "Không thể tải slide. Kiểm tra kết nối." + nút **"Thử lại"** (primary navy).
- **Selection popup "Hỏi AI":** pill navy `px-3 h-8` + `[ChatCircleDots]` 14; `shadow-lg` + mũi tên nhỏ; **clamp vị trí ±16px** trong viewport; quote rút gọn khi >120 ký tự (max-w 280px, 1 dòng, ellipsis); debounce `selectionchange` 80ms (F7). Animation: scale 0.96→1 + fade, 200ms `ease-pop`.
- **Ghi chú panel:** giữ chức năng local. Header title + nút đóng `[X]`; textarea radius-md focus ring brand; nút Lưu 3 trạng thái: *idle → đang lưu (`[CircleNotch]` spin) → Đã lưu `[Check]` success (tự ẩn 2s)*. **Đề xuất:** wire localStorage theo key `vlearn-notes:{docId}:{page}` — không cần backend (F3).
- **Fix F2:** chỉ `paddingLeft/paddingRight` khi panel tương ứng là overlay (sidebar <lg, chat <xl); desktop panel nằm in-flow chiếm chỗ thật.

### 5.4 ChatPanel (trọng tâm)
```
┌────────────────────────────────────────┐
│ ● VLearn Tutor                   🗑  ✕ │  dot brand-600 + title 16/600; 🗑=[Trash], ✕=[X]
│ Research · tự động tìm paper arXiv      │  context 12/500 ink-faint (đổi theo mode)
├────────────────────────────────────────┤
│ ┌─────────segmented──────────────┐     │
│ │ [ ◧ Normal ]  [ ⚗ Research ]   │     │  track: bg-surface-2 radius-lg p-0.5,
│ └────────────────────────────────┘     │  active CẢ HAI: bg-surface text-brand-700
│ ┌────────────────────────────────┐     │   shadow-sm + icon brand-600; idle: ink-muted
│ │ NGUỒN RESEARCH · tuỳ chọn      │     │  card trung tính: bg-surface-2 radius-lg
│ │ [ Tự động tìm paper trên arXiv ]│     │   (KHÔNG màu vàng — G3)
│ │ [ Tìm paper arXiv…  ] [ Thêm ]  │     │  Thêm = secondary outline brand
│ └────────────────────────────────┘     │
├────────────────────────────────────────┤
│                 ┌────────────────┐     │
│                 │ câu hỏi của tôi│     │  user: bg-brand-600 text-white radius-xl
│                 └────────────────┘     │        corner-tr 4px, max-w 88% & ≤65ch
│ ┌────────────────────────────────┐     │
│ │ Câu trả lời markdown…          │     │  tutor: bg-surface + shadow-sm + hairline
│ │                                │     │   border-brand-950/8, radius-xl corner-tl 4
│ │ ▸ BẰNG CHỨNG (overline 11/600) │     │
│ │ ┌────────────────────────────┐ │     │
│ │ │ [PAPER-1] tên paper ▾      │ │     │  citation card: surface, border-brand-950/8
│ │ │ Trang 2 · dòng 10–14       │ │     │   header: text-mono 12/600 brand-700
│ │ │ ┌ quote (Geist Mono) ────┐ │ │     │
│ │ │ │ "trích nguyên văn..."  │ │ │     │   quote: font-mono 12, border-l-2 brand-300,
│ │ │ └───────────────────────┘ │ │     │   bg-surface-2
│ │ │ ↗ Mở nguồn (arXiv)         │ │     │   [ArrowSquareOut] 12
│ │ └────────────────────────────┘ │     │
│ └────────────────────────────────┘     │
│ ● ● ●  Đang tìm paper trên arXiv… 12s  │  typing status (xem dưới)
├────────────────────────────────────────┤
│ ┌────────────────────────────────┐     │
│ │ Nhập câu hỏi về slide…      ▶ │     │  composer: bg-surface-2 radius-lg, focus
│ └────────────────────────────────┘     │   ring brand; Enter gửi / Shift+Enter dòng
└────────────────────────────────────────┘
```
- **Mode selector (2 tab):** cùng ngôn ngữ thị giác — cả 2 đều pill trắng nổi trên track, chỉ đổi icon + màu chữ navy khi active (G3: không accent thứ 2). Research phân biệt bằng icon `[Flask]` + dòng context phía dưới + badge "paper" trên citation.
- **Research config:** card trung tính `bg-surface-2` (bỏ amber). Select có chevron `[CaretDown]`, control chuẩn `h-9`; input + nút "Thêm" (secondary: outline brand, hover bg-brand-50) thẳng hàng (F9). Import: nút hiển thị `[CircleNotch]` spin + "Đang index…" → xong: **toast** "✓ Đã thêm paper · chọn làm focus" (không nhét vào message) → lỗi: text danger + nút thử lại.
- **Bubble tutor:** card trắng `shadow-sm` + hairline tint (cảm giác "tài liệu đáng tin" — NotebookLM). Markdown giữ (prose-sm, link brand-600 underline, code mono, ul spacing).
- **Citations:** nhóm "BẰNG CHỨNG" (overline). Slide-cite = chip clickable `[FileText] D1 - Trang 4` nhảy trang + **flash highlight 1.2s** trang đích (ring brand-400, fade out). Paper-cite = card expand như wireframe: label mono `[PAPER-1]`, quote mono viền brand-300.
- **Typing status (F4):** dòng `● ● ● [Trạng thái] [Xs]` — 3 dot (brand-400, bounce stagger 150ms), trạng thái đổi theo mode + thời gian trôi:
  - Normal: "Đang tìm trong slide…"
  - Research: "Đang tìm paper trên arXiv…" → "Đang tải & index paper…" → "Đang viết câu trả lời…"
  - Backend hiện không gửi status event → frontend tự suy theo mode + elapsed (0–4s: tìm, 4–15s: index, >15s: viết). **Đề xuất backend P2** (§7).
- **Composer:** auto-grow tới 6 dòng (F8); nút gửi `[PaperPlaneTilt]` → khi stream đổi thành **Dừng `[Stop]`** (AbortController + `reader.cancel()`); disabled: opacity 40 + cursor-not-allowed; focus-within ring brand.
- **Empty state (G6):** welcome card + **3 chip gợi ý theo ngữ cảnh**: "Tóm tắt trang này" · "Giải thích khái niệm chính trang này" · "Tìm paper về chủ đề trang này" (Research) — chip = outline brand, nhấn điền vào input. Có hội thoại → chip ẩn.
- **Clear chat:** nếu >1 turn → popover confirm "Xoá hội thoại?" [Huỷ]/[Xoá] (ease-pop 200ms).
- **Error:** banner trong panel (bg danger/5 + text danger + `[WarningCircle]` + message tiếng Việt + nút "Thử lại" gửi lại turn cuối); lỗi mạng không nhét vào bubble (G6).
- **Responsive (F1):** ≥xl panel in-flow w-96; <xl overlay `fixed` + backdrop `bg-brand-950/30`; **nút AI luôn hiển thị mọi kích thước**.

### 5.5 Toggle 2 cạnh (Slide / AI)
```
 ┌──┐
 │▤│  ← pill h-20 w-9: bg-brand-600/95 + backdrop-blur, radius-r-full (trái) /
 │S│     radius-l-full (phải); icon [SidebarSimple]/[Sparkle] + chữ dọc 10/600
 └──┘     hover: w-11 + bg-brand-700 (ease-quick 150ms, chỉ transform/opacity)
```
- `aria-expanded` + tooltip "Mở danh sách slide" / "Mở trợ lý AI"; khi hover ra → opacity 85%.

---

## 6. Danh sách states bắt buộc

### Panel / layout
| State | Mô tả |
|---|---|
| Sidebar open/closed | Desktop in-flow (w-256 ↔ w-0, transform slide); <lg overlay + backdrop fade |
| Chat open/closed | ≥xl in-flow; <xl overlay có backdrop; **nút AI luôn hiển thị mọi breakpoint** |
| Notes open/closed | Trượt nhẹ 200ms ease-quick |
| Breakpoints | <lg: sidebar overlay · <xl: chat overlay · ≥xl: 3 cột |

### Slide viewer
| State | Mô tả |
|---|---|
| Loading | Skeleton trang + caption "Đang tải slide…" |
| Loaded | Trang render; page-in-view cập nhật "Trang X/Y" |
| Error | Card + `[CloudX]` + nút Thử lại |
| Empty | Không có PDF → "Chọn một tài liệu từ sidebar" |
| Zoom | − / % (reset) / + / Fit-width |
| Selection popup | Hiện/ẩn; quote rút gọn >120 ký tự; clamp biên |
| Jump-to-page | Scroll mượt + flash highlight 1.2s trang đích |
| Ghi chú lưu | idle → đang lưu (spin) → Đã lưu ✓ (ẩn 2s) |

### Chat
| State | Mô tả |
|---|---|
| Empty/welcome | Welcome + 3 suggested chips theo mode/trang |
| Composing | Input trống → send disabled; auto-grow tới 6 dòng |
| Streaming | 3-dot + trạng thái bước + đồng hồ giây; nút Dừng |
| Answered | Markdown + citations (slide chips / paper cards) |
| Citation expand/collapse | `<details>` mượt; quote mono |
| Error mạng | Banner + nút Thử lại (gửi lại turn cuối) |
| AI unavailable | Message riêng từ backend + gợi ý thử lại sau |
| Import paper | idle → importing (spin) → success (toast + chọn focus) → error (danger + retry) |
| Papers load | Select skeleton → danh sách / rỗng ("Chưa có paper — nhập chủ đề để thêm") |
| Clear chat | Confirm popover khi >1 turn |

### Tương tác (MỌI control — G6)
**Hover** (150ms ease-quick) · **Active** (press: bg đậm hơn 1 bậc, scale 0.98 cho nút chính) · **Focus-visible** (`ring-2 ring-brand-400 offset-2`; trên nền navy `ring-white/60`) · **Disabled** (opacity 40 + cursor-not-allowed) · **Loading** (spinner 16px thay icon).

---

## 7. Đề xuất backend (P2 — Dev làm nếu có thời gian)

1. **SSE status events** trên `/api/chat/stream`: thêm `data: {"status": "searching"|"indexing"|"answering", "elapsed_ms": ...}` giữa các token → ChatPanel hiển thị trạng thái bước thật thay vì suy đoán theo thời gian. **Giữ backward-compatible** (frontend bỏ qua event lạ).
2. **Persist ghi chú:** nếu muốn đồng bộ thì `GET/PUT /api/notes/{doc_id}/{page}`; nếu không, localStorage đủ (khuyến nghị: localStorage, không cần endpoint).
3. `GET /api/papers` trả thêm `imported_at` để sort select mới nhất lên đầu.

---

## 8. Quy tắc bắt buộc cho Dev (checklist)

1. **Không đổi chức năng / API contract.** Giữ endpoints (`/api/chat/stream`, `/api/papers`, `/api/papers/import-arxiv`), props component, logic chat/stream/jump. Mọi đổi logic phải báo PO trước.
2. **Chỉ dùng tokens §4.** Không hardcode hex; **1 accent duy nhất** (navy) — xoá hết amber khỏi Research; màu functional chỉ cho trạng thái thật.
3. **Font:** Geist + Geist Mono qua `next/font/google` (KHÔNG Inter, xoá khai báo 'Be Vietnam Pro' chết). Render-test dấu tiếng Việt; thiếu glyph → fallback Outfit.
4. **Icon:** Phosphor duy nhất (`@phosphor-icons/react`); xoá toàn bộ emoji + SVG thủ công; 16px/18px nhất quán.
5. **Không viền xám 1px generic** — phân tách bằng surface contrast + shadow; hairline tint `brand-950/8` chỉ khi bắt buộc. Shadow luôn nhuốm navy (§4.4), tối đa 2 lớp.
6. **Shape lock:** radius đúng 5 bậc §4.3; control h-9; hit-area ≥32px.
7. **Motion:** chỉ transform/opacity; dùng 3 token ease §4.5 (cấm linear/ease-in-out); stagger ≤5 item × 40ms; `prefers-reduced-motion` tắt hết.
8. **States đầy đủ §6** — mọi hành động có loading/empty/error; focus-visible mọi control; aria-label cho icon button; `aria-expanded` mọi toggle; contrast ≥4.5:1.
9. **Fix bắt buộc F1–F9** (§2.2), đặc biệt F1 (chat không được biến mất <1280px) và F2 (padding-hack).
10. **Tiếng Việt toàn UI** đúng chính tả; số trang/dòng giữ format hiện có.
11. **QC-pass trước bàn giao:** tự screenshot 3 trạng thái (default · both-open · research-mode) đối chiếu wireframe §5.

---

## 9. Quyết định đã chốt (log chính thức — user duyệt 24/08)

| # | Câu hỏi | User chọn | Ý nghĩa thiết kế |
|---|---|---|---|
| Q1 | Màu thương hiệu | **A — GIỮ #134D8B đã hiệu chỉnh** (không đổi sang blue/teal) | 1 accent duy nhất; Research phân biệt bằng icon `[Flask]` + cấu trúc, KHÔNG màu thứ 2 |
| Q2 | Dark mode | **A — KHÔNG làm đợt này** | Chỉ light mode; dark mode để phase sau (P2) |
| Q3 | Mật độ UI | **A — "Calm & compact"** | Chat airy (body 14/22, ≤65ch); sidebar/toolbar compact (h-9, gap 12) |
| Q4 | Layout | **A — GIỮ 3-panel** | Chat **mặc định MỞ** trên desktop (≥xl); sidebar 256px; 2 nút toggle rõ ràng trên top bar; bỏ trùng lặp hamburger/nút Slide |

→ Toàn bộ spec §4–§8 của file này đã khớp với 4 quyết định trên. Đây là chuẩn cài đặt cuối cùng cho Dev.

---

## §10 Landing page (t19 — vlearn-ux-team)

**Hướng đã chọn:** Draft A "Calm Focus Editorial" (sáng, tiếp nối §4–§7) — bản B "Dark Studio Tech" (tối) để dự phòng nếu user đổi ý.
- Superdesign canvas: https://superdesign.dev/teams/fcc9e8fe-1a8d-49bf-a14c-7a19858fe5a7/projects/d8f07226-9b65-425e-9760-173bf7f78b2b
- Draft A preview: https://p.superdesign.dev/draft/43ebfd39-316d-4c6c-bc58-7df34f6d758d · Draft B preview: https://p.superdesign.dev/draft/0cc2a23a-9940-43cd-9a29-e1d23bb60f10

**Quyết định route:** `/` = landing (giới thiệu project) · `/app` = study workspace (page.tsx cũ move sang `app/app/page.tsx`). Nút "Quay lại" trong workspace → `<a href="/">` thay `history.back()`.

**Cấu trúc landing:** nav 64px 1 dòng (logo V + Tính năng/Bằng chứng/Cách học + CTA "Vào học") · hero split (headline 2 dòng 1 accent + CTA đôi, phải = mockup workspace schematic bằng DOM + tokens thật) · stats band Geist Mono (17 bài giảng · 926 trang · 30.5%→<15% fail · 24 eval gate) · features bento (Normal/Research/Tóm tắt/Memory&Coach, cell rộng hẹp không đều) · "Cách học" 3 bước (mở tài liệu → bôi đen để hỏi → kiểm chứng nguồn) · evidence (số liệu thật + citation mẫu D10 · Trang 16) · CTA band navy-800 · footer tối giản.

**Tokens:** dùng chung 100% globals.css (1 accent navy · Geist + Geist Mono · radius/shadow/motion system) — KHÔNG thêm màu/font mới. Motion: `Reveal` (IntersectionObserver, opacity+translate 500ms ease-quick, stagger ≤140ms, tôn trọng prefers-reduced-motion). Anti-slop: không emoji, không gradient màu, CTA 1 intent ("Vào học"), a11y focus-visible ring khắp nơi.

**Số liệu thật (nguồn):** 17 tài liệu/926 trang (slideDocs.ts + rag.py) · fail rate 30.5% → mục tiêu <15% (phan-tich-chatlog.md + AGENT-UPGRADE-PLAN §4) · 24 case eval gate (src/eval).

**Quyết định USER (đã duyệt):** chọn **Draft A "Calm Focus Editorial"**, yêu cầu bổ sung: *"làm nổi bật các hình khối lên, nội dung hơi rời rạc"* → đã gia cố block-hierarchy: stats = 4 card khối (card đầu navy-800), features = cards nổi trên band surface-2 + icon badge ô navy-50/800, cách học = step badge tròn navy-50, evidence = item card surface-2, CTA = ring + shadow-lg, gap nhất quán 4.
