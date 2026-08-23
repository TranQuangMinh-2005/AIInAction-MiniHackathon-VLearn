import type { Metadata } from "next";
import Link from "next/link";
import {
  ArrowSquareOut,
  BookOpen,
  ChatCircleDots,
  FileText,
  Flask,
  MagnifyingGlass,
  NotePencil,
  Sparkle,
  WarningCircle,
  XCircle,
} from "@phosphor-icons/react/dist/ssr";
import Reveal from "@/components/Reveal";

/* Landing page — Draft A "Calm Focus Editorial" (Superdesign canvas, t19) +
   t31: kể chuyện PAIN → SOLUTION bằng số liệu thật (docs/phan-tich-chatlog.md + docs/spec.md).
   Nguồn thật: COMP2010 · AI Thực Chiến · 17 bài giảng / 926 trang ·
   fail rate 30.5% (385/1.261) → mục tiêu <15% · 52.8% hội thoại 1 turn ·
   46.2% trả lời không cite · khảo sát 58 học viên: 60.3% hụt hẫng vì AI lặp lại slide. */

export const metadata: Metadata = {
  title: "VLearn — AI Thực Chiến · AI Tutor có nguồn kiểm chứng",
  description:
    "AI tutor đọc slide, mở rộng kiến thức bằng paper khoa học từ arXiv, mọi câu trả lời đều có citation [Trang X] và [S1] để bạn tự kiểm chứng.",
};

const NAV_LINKS = [
  { href: "#pain", label: "Vấn đề" },
  { href: "#solution", label: "Giải pháp" },
  { href: "#features", label: "Tính năng" },
  { href: "#how", label: "Cách học" },
  { href: "#evidence", label: "Bằng chứng" },
];

function Logo({ dark = false }: { dark?: boolean }) {
  return (
    <span className="flex items-center gap-2.5">
      <svg width="26" height="26" viewBox="0 0 38 38" fill="none" aria-hidden="true">
        <rect width="38" height="38" rx="8" fill="#134D8B" />
        <text x="9" y="26" fill="white" fontSize="18" fontWeight="900" fontFamily="Geist, sans-serif">
          V
        </text>
      </svg>
      <span
        className={`text-base font-semibold tracking-tight ${
          dark ? "text-white" : "text-ink-strong"
        }`}
      >
        VLearn
      </span>
    </span>
  );
}

export default function LandingPage() {
  return (
    <div className="min-h-[100dvh] bg-surface text-ink">
      {/* ===== Nav — 64px, 1 dòng, sticky ===== */}
      <header className="sticky top-0 z-30 border-b border-border/60 bg-surface/90 backdrop-blur-md">
        <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          <a href="#top" aria-label="VLearn về đầu trang" className="rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400">
            <Logo />
          </a>
          <div className="hidden items-center gap-1 md:flex">
            {NAV_LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="rounded-md px-3 py-1.5 text-sm font-medium text-ink-muted transition-colors duration-150 ease-quick hover:bg-surface-2 hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
              >
                {link.label}
              </a>
            ))}
          </div>
          <Link
            href="/app"
            className="flex h-9 items-center rounded-lg bg-brand-600 px-4 text-sm font-semibold text-white transition-colors duration-150 ease-quick hover:bg-brand-700 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2"
          >
            Vào học
          </Link>
        </nav>
      </header>

      {/* ===== Hero — split asymmetric ===== */}
      <section id="top" className="mx-auto grid max-w-6xl grid-cols-1 items-center gap-12 px-4 pb-16 pt-16 sm:px-6 lg:grid-cols-[1.05fr_0.95fr] lg:pt-20">
        <Reveal>
          <div className="max-w-xl">
            <span className="inline-flex items-center rounded-full border border-brand-200 bg-brand-50 px-3 py-1 text-overline font-semibold uppercase tracking-[0.08em] text-brand-700">
              COMP2010 · AI Thực Chiến
            </span>
            <h1 className="mt-6 text-4xl font-semibold leading-[1.08] tracking-tighter text-ink-strong md:text-5xl lg:text-6xl">
              Học AI thực chiến.{" "}
              <span className="text-brand-600">Mọi câu trả lời đều có nguồn.</span>
            </h1>
            <p className="mt-6 max-w-[52ch] text-base leading-relaxed text-ink-muted md:text-lg">
              AI tutor trả lời được mọi câu hỏi của bạn về bài học — kể cả những
              thứ slide không có.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Link
                href="/app"
                className="flex h-11 items-center gap-2 rounded-lg bg-brand-600 px-6 text-sm font-semibold text-white shadow-sm transition-colors duration-150 ease-quick hover:bg-brand-700 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2"
              >
                Vào học
                <ArrowSquareOut size={16} aria-hidden="true" />
              </Link>
              <a
                href="#features"
                className="flex h-11 items-center rounded-lg border border-brand-300 px-6 text-sm font-semibold text-brand-700 transition-colors duration-150 ease-quick hover:bg-brand-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
              >
                Xem tính năng
              </a>
            </div>
          </div>
        </Reveal>

        {/* Mockup workspace dạng schematic (bằng DOM + tokens thật, không ảnh giả) */}
        <Reveal delay={120}>
          <div className="rounded-2xl bg-canvas p-3 shadow-lg ring-1 ring-brand-950/8">
            <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1.5fr)_minmax(0,1.1fr)] gap-2 rounded-xl bg-surface p-2">
              {/* Sidebar mini */}
              <div className="space-y-1.5">
                <div className="rounded-md bg-surface-2 px-2 py-1.5">
                  <p className="text-overline uppercase text-ink-faint">Học liệu</p>
                  <p className="text-caption font-medium text-ink">Day 5 · Thiết kế sản phẩm AI</p>
                  <p className="text-caption text-ink-faint">D05 · 52 trang</p>
                </div>
                <div className="h-6 rounded-md bg-brand-50 ring-1 ring-brand-100" />
                <div className="h-6 rounded-md bg-surface-2" />
              </div>
              {/* Slide mini */}
              <div className="flex flex-col gap-1.5">
                <div className="rounded-lg bg-white p-2 shadow-sm ring-1 ring-brand-950/8">
                  <div className="h-14 rounded-md bg-brand-50" />
                  <div className="mt-2 h-1.5 w-3/4 rounded bg-border-strong" />
                  <div className="mt-1.5 h-1.5 w-1/2 rounded bg-border" />
                </div>
                <div className="flex items-center justify-between px-1">
                  <span className="text-caption text-ink-faint">Trang 12/52</span>
                  <span className="rounded bg-brand-50 px-1.5 py-0.5 font-mono text-[10px] font-bold text-brand-700">
                    D05
                  </span>
                </div>
              </div>
              {/* Chat mini */}
              <div className="flex flex-col justify-between rounded-lg bg-surface-2 p-2">
                <div className="space-y-1.5">
                  <div className="max-w-[90%] rounded-xl rounded-tl-xs bg-surface p-2 shadow-sm ring-1 ring-brand-950/8">
                    <div className="h-1.5 w-full rounded bg-border-strong" />
                    <div className="mt-1 h-1.5 w-2/3 rounded bg-border" />
                    <div className="mt-1.5 flex items-center gap-1">
                      <FileText size={10} aria-hidden="true" className="text-brand-500" />
                      <span className="font-mono text-[9px] text-brand-700">D05 · Trang 12</span>
                    </div>
                  </div>
                  <div className="max-w-[85%] rounded-xl rounded-tr-xs bg-brand-600 px-2 py-1.5">
                    <div className="h-1.5 w-4/5 rounded bg-white/80" />
                  </div>
                </div>
                <div className="flex items-center gap-1 rounded-md bg-surface px-2 py-1.5 ring-1 ring-border/60">
                  <span className="h-1.5 flex-1 rounded bg-border-strong" />
                  <span className="flex h-5 w-5 items-center justify-center rounded-md bg-brand-600">
                    <Sparkle size={10} aria-hidden="true" className="text-white" />
                  </span>
                </div>
              </div>
            </div>
          </div>
        </Reveal>
      </section>

      {/* ===== Pain — vấn đề thật từ chatlog + khảo sát (t31) ===== */}
      <section id="pain" className="scroll-mt-20 border-y border-border/60 bg-surface-2 py-24">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <Reveal>
            <span className="text-overline font-semibold uppercase tracking-[0.08em] text-brand-700">
              Vấn đề · đo bằng dữ liệu thật
            </span>
            <h2 className="mt-4 max-w-3xl text-3xl font-semibold leading-tight tracking-tighter text-ink-strong md:text-4xl">
              Tutor cũ chỉ đọc lại slide của bạn
            </h2>
            <p className="mt-3 max-w-[58ch] text-base leading-relaxed text-ink-muted">
              Trước khi VLearn Research Tutor ra đời, chúng tôi đo toàn bộ chatlog
              thật của trợ giảng AI cũ — 2.522 tin nhắn, 585 hội thoại, 369 học viên
              trong 8 ngày — và khảo sát 58 học viên. Kết quả không vui.
            </p>
          </Reveal>

          <div className="mt-12 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {/* 30.5% — fail rate */}
            <Reveal>
              <div className="flex h-full flex-col rounded-2xl bg-surface p-6 shadow-sm ring-1 ring-brand-950/8">
                <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                  <WarningCircle size={18} aria-hidden="true" />
                </span>
                <p className="mt-5 font-mono text-3xl font-semibold tracking-tight text-brand-700">30.5%</p>
                <h3 className="mt-2 text-sm font-semibold leading-snug text-ink-strong">
                  câu hỏi AI không trả lời được
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-ink-muted">
                  385/1.261 turn thất bại trong chatlog thật — cứ 3 câu hỏi thì
                  1 câu nhận lại "không tìm thấy".
                </p>
              </div>
            </Reveal>

            {/* 52.8% — hội thoại 1 turn */}
            <Reveal delay={60}>
              <div className="flex h-full flex-col rounded-2xl bg-surface p-6 shadow-sm ring-1 ring-brand-950/8">
                <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                  <XCircle size={18} aria-hidden="true" />
                </span>
                <p className="mt-5 font-mono text-3xl font-semibold tracking-tight text-brand-700">52.8%</p>
                <h3 className="mt-2 text-sm font-semibold leading-snug text-ink-strong">
                  hội thoại kết thúc sau đúng 1 câu hỏi
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-ink-muted">
                  309/585 hội thoại — học viên hỏi một câu, không hài lòng, rồi
                  bỏ đi.
                </p>
              </div>
            </Reveal>

            {/* 46.2% — không cite */}
            <Reveal delay={120}>
              <div className="flex h-full flex-col rounded-2xl bg-surface p-6 shadow-sm ring-1 ring-brand-950/8">
                <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                  <FileText size={18} aria-hidden="true" />
                </span>
                <p className="mt-5 font-mono text-3xl font-semibold tracking-tight text-brand-700">46.2%</p>
                <h3 className="mt-2 text-sm font-semibold leading-snug text-ink-strong">
                  câu trả lời không có trích dẫn nguồn
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-ink-muted">
                  582/1.261 câu trả lời thiếu nguồn — học viên không thể tự kiểm
                  chứng điều vừa nghe.
                </p>
              </div>
            </Reveal>

            {/* Quote — React/ReAct từ chatlog thật */}
            <Reveal delay={180}>
              <div className="flex h-full flex-col justify-between rounded-2xl bg-brand-800 p-6 shadow-sm ring-1 ring-brand-950/8">
                <div>
                  <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-white/15 text-white">
                    <ChatCircleDots size={18} aria-hidden="true" />
                  </span>
                  <p className="mt-5 text-sm font-medium leading-relaxed text-white/90">
                    Hỏi <span className="font-mono">"React là gì?"</span> — chủ đề
                    chính của buổi học — AI trả lời:{" "}
                    <span className="font-mono">"không tìm thấy"</span>
                  </p>
                </div>
                <p className="mt-5 text-caption leading-relaxed text-white/60">
                  Chatlog thật · hội thoại C0128 · 8 ngày thu thập
                </p>
              </div>
            </Reveal>
          </div>

          {/* Khảo sát 58 học viên — 60.3% hụt hẫng */}
          <Reveal delay={80}>
            <div className="mt-4 flex flex-col gap-3 rounded-2xl bg-surface p-5 ring-1 ring-border/60 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-sm leading-relaxed text-ink">
                <span className="font-mono text-lg font-semibold tracking-tight text-brand-700">60.3%</span>{" "}
                học viên từng hụt hẫng vì AI lặp lại slide — khảo sát 58 người, 30/07/2026
              </p>
              <p className="shrink-0 text-caption text-ink-faint">
                35/58 trả lời đồng ý
              </p>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ===== Solution — VLearn Research Tutor, hiểu sâu hơn slide (t31) ===== */}
      <section id="solution" className="scroll-mt-20 bg-brand-800 py-24">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <Reveal>
            <span className="text-overline font-semibold uppercase tracking-[0.08em] text-brand-200">
              Giải pháp
            </span>
            <h2 className="mt-4 max-w-3xl text-3xl font-semibold leading-tight tracking-tighter text-white md:text-4xl">
              VLearn Research Tutor — hiểu sâu hơn slide
            </h2>
            <p className="mt-3 max-w-[58ch] text-base leading-relaxed text-white/70">
              Khi slide không đủ, tutor không từ chối: nó tự định tuyến câu hỏi,
              đi tìm kiến thức khoa học và trả lời kèm nguồn kiểm chứng được.
            </p>
          </Reveal>

          <ol className="mt-12 grid grid-cols-1 gap-4 md:grid-cols-3">
            {[
              {
                step: "01",
                icon: <ChatCircleDots size={22} aria-hidden="true" />,
                title: "Bạn hỏi vượt ngoài slide",
                text: "Khái niệm chưa có trong bài giảng, so sánh, ứng dụng thực tế — kể cả câu 'ReAct là gì?' tutor vẫn nhận và xử lý đúng.",
              },
              {
                step: "02",
                icon: <MagnifyingGlass size={22} aria-hidden="true" />,
                title: "AI tự tìm paper khoa học",
                text: "Research tự tìm paper phù hợp trên arXiv, tải và đọc toàn văn — không bỏ cuộc khi slide thiếu thông tin.",
              },
              {
                step: "03",
                icon: <FileText size={22} aria-hidden="true" />,
                title: "Trả lời kèm nguồn kiểm chứng",
                text: "Citation thật: [Trang X] cho slide, [S1] cho paper — kèm trang, dòng và trích dẫn nguyên văn để bạn tự kiểm chứng.",
              },
            ].map((item) => (
              <li
                key={item.step}
                className="flex h-full flex-col rounded-2xl bg-white/10 p-6 ring-1 ring-white/15"
              >
                <div className="flex items-center justify-between">
                  <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-white/15 text-white">
                    {item.icon}
                  </span>
                  <span className="font-mono text-sm font-semibold tracking-widest text-white/50">
                    {item.step}
                  </span>
                </div>
                <h3 className="mt-5 text-base font-semibold text-white">{item.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-white/70">{item.text}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* ===== Stats band — khối card nổi trên nền surface-2 ===== */}
      <section className="border-y border-border/60 bg-surface-2">
        <Reveal>
          <dl className="mx-auto grid max-w-6xl grid-cols-1 gap-4 px-4 py-12 sm:px-6 sm:grid-cols-2 lg:grid-cols-4">
            {[
              {
                value: "17",
                label: "bài giảng trong khoá",
                icon: <BookOpen size={18} aria-hidden="true" />,
                strong: true,
              },
              {
                value: "926",
                label: "trang slide được index",
                icon: <FileText size={18} aria-hidden="true" />,
              },
              {
                value: "30.5% → <15%",
                label: "mục tiêu giảm tỉ lệ hỏng của AI tutor",
                icon: <Flask size={18} aria-hidden="true" />,
              },
              {
                value: "24",
                label: "case eval gate chống regression",
                icon: <NotePencil size={18} aria-hidden="true" />,
              },
            ].map((stat) => (
              <div
                key={stat.label}
                className={`rounded-xl p-5 shadow-sm ring-1 ring-brand-950/8 ${
                  stat.strong
                    ? "bg-brand-800 text-white"
                    : "bg-surface text-ink"
                }`}
              >
                <span
                  className={`flex h-9 w-9 items-center justify-center rounded-lg ${
                    stat.strong ? "bg-white/15 text-white" : "bg-brand-50 text-brand-600"
                  }`}
                >
                  {stat.icon}
                </span>
                <dd
                  className={`mt-4 font-mono text-2xl font-semibold tracking-tight md:text-3xl ${
                    stat.strong ? "text-white" : "text-brand-700"
                  } ${stat.value.length > 8 ? "text-xl md:text-2xl" : ""}`}
                >
                  {stat.value}
                </dd>
                <dd className={`mt-1 text-sm leading-snug ${stat.strong ? "text-white/75" : "text-ink-muted"}`}>
                  {stat.label}
                </dd>
              </div>
            ))}
          </dl>
        </Reveal>
      </section>

      {/* ===== Features — bento khối rõ, cards nổi trên nền surface-2 ===== */}
      <section id="features" className="scroll-mt-20 bg-surface-2 py-24">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <Reveal>
            <h2 className="max-w-2xl text-3xl font-semibold leading-tight tracking-tighter text-ink-strong md:text-4xl">
              Một workspace học tập, bốn cách AI hỗ trợ
            </h2>
            <p className="mt-3 max-w-[58ch] text-base leading-relaxed text-ink-muted">
              Vừa đọc slide vừa hỏi sâu. Mỗi chế độ đều trả kèm nguồn để bạn
              tự kiểm chứng trước khi tin.
            </p>
          </Reveal>

          <div className="mt-12 grid grid-cols-1 gap-4 md:grid-cols-6">
            {/* Normal — cell lớn */}
            <Reveal className="md:col-span-6 lg:col-span-4">
              <div className="flex h-full flex-col justify-between rounded-2xl bg-surface p-7 shadow-sm ring-1 ring-brand-950/8">
                <div>
                  <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
                    <ChatCircleDots size={24} aria-hidden="true" />
                  </div>
                  <h3 className="mt-5 text-lg font-semibold text-ink-strong">AI Tutor · Normal</h3>
                  <p className="mt-3 text-base leading-relaxed text-ink-muted">
                    Trả lời trực tiếp từ slide bạn đang xem, kèm citation{" "}
                    <span className="font-mono text-caption">[Trang X]</span>. Gợi ý câu
                    hỏi tiếp theo dạng chip nhấn được và ghi nhận nhầm lẫn như{" "}
                    <em>React vs ReAct</em>.
                  </p>
                </div>
                <div className="mt-6 grid gap-2 border-t border-border/60 pt-5 sm:grid-cols-2">
                  <div className="flex items-start gap-3 rounded-lg bg-surface-2 p-3 ring-1 ring-border/60">
                    <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-brand-50">
                      <FileText size={13} aria-hidden="true" className="text-brand-600" />
                    </span>
                    <p className="text-sm leading-snug text-ink">Bôi đen đoạn trên slide và hỏi "Giải thích đoạn này".</p>
                  </div>
                  <div className="flex items-start gap-3 rounded-lg bg-surface-2 p-3 ring-1 ring-border/60">
                    <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-brand-50">
                      <NotePencil size={13} aria-hidden="true" className="text-brand-600" />
                    </span>
                    <p className="text-sm leading-snug text-ink">Ghi chú theo trang, lưu ngay trong trình duyệt.</p>
                  </div>
                </div>
              </div>
            </Reveal>

            {/* Research — cell nhỏ */}
            <Reveal className="md:col-span-3 lg:col-span-2" delay={80}>
              <div className="flex h-full flex-col rounded-2xl bg-surface p-6 shadow-sm ring-1 ring-brand-950/8">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
                  <Flask size={22} aria-hidden="true" />
                </div>
                <h3 className="mt-5 text-base font-semibold text-ink-strong">Research Scholar</h3>
                <p className="mt-2 text-sm leading-relaxed text-ink-muted">
                  Tự tìm paper phù hợp trên arXiv. Trích dẫn{" "}
                  <span className="font-mono text-caption">[S1]</span> kèm trang, dòng
                  và quote nguyên văn, kiểm chứng từng claim.
                </p>
              </div>
            </Reveal>

            {/* Summary — cell nhỏ */}
            <Reveal className="md:col-span-3 lg:col-span-2" delay={140}>
              <div className="flex h-full flex-col rounded-2xl bg-surface p-6 shadow-sm ring-1 ring-brand-950/8">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
                  <BookOpen size={22} aria-hidden="true" />
                </div>
                <h3 className="mt-5 text-base font-semibold text-ink-strong">Tóm tắt toàn tài liệu</h3>
                <p className="mt-2 text-sm leading-relaxed text-ink-muted">
                  Hỏi "tóm tắt day 4" để nhận bản tóm tắt theo từng phần. Lần hai
                  trả trong chưa đầy một giây nhờ cache.
                </p>
              </div>
            </Reveal>
          </div>

          {/* Memory + Coach — khối ngang đậm hơn */}
          <Reveal className="mt-4" delay={60}>
            <div className="flex flex-col gap-6 rounded-2xl bg-surface p-7 shadow-sm ring-1 ring-brand-950/8 md:flex-row md:items-center md:justify-between">
              <div className="flex items-start gap-4">
                <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-brand-800 text-white">
                  <Sparkle size={24} aria-hidden="true" />
                </span>
                <div className="max-w-xl">
                  <h3 className="text-lg font-semibold text-ink-strong">Nhớ bạn, dạy sâu hơn</h3>
                  <p className="mt-2 text-sm leading-relaxed text-ink-muted">
                    Tiến độ và khái niệm đã hỏi được lưu ẩn danh theo trình duyệt.
                    AI chỉ hỏi kiểm tra hiểu khi thấy bạn gặp khó hoặc hỏi lặp,
                    không làm phiền mỗi lượt.
                  </p>
                </div>
              </div>
              <Link
                href="/app"
                className="flex h-10 shrink-0 items-center rounded-lg border border-brand-300 px-5 text-sm font-semibold text-brand-700 transition-colors duration-150 ease-quick hover:bg-brand-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
              >
                Mở workspace
              </Link>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ===== Cách học — bôi đen để hỏi ===== */}
      <section id="how" className="bg-surface-2 py-24">
        <Reveal>
          <div className="mx-auto max-w-6xl px-4 sm:px-6">
            <h2 className="max-w-2xl text-3xl font-semibold leading-tight tracking-tighter text-ink-strong md:text-4xl">
              Học theo nhịp đọc của bạn
            </h2>
            <ol className="mt-12 grid grid-cols-1 gap-4 md:grid-cols-3">
              {[
                {
                  step: "01",
                  title: "Mở bài giảng",
                  text: "Chọn một trong 17 tài liệu, lật trang như đọc slide thật.",
                },
                {
                  step: "02",
                  title: "Bôi đen để hỏi",
                  text: "Chọn đoạn khó hiểu, AI giải thích đúng ngữ cảnh trang bạn đang xem.",
                },
                {
                  step: "03",
                  title: "Kiểm chứng nguồn",
                  text: "Mỗi câu trả lời kèm [Trang X] hoặc [S1] với trích dẫn nguyên văn.",
                },
              ].map((item) => (
                <li key={item.step} className="rounded-2xl bg-surface p-6 shadow-sm ring-1 ring-brand-950/8">
                  <span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-50 font-mono text-sm font-semibold text-brand-700">
                    {item.step}
                  </span>
                  <h3 className="mt-4 text-base font-semibold text-ink-strong">{item.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-ink-muted">{item.text}</p>
                </li>
              ))}
            </ol>
          </div>
        </Reveal>
      </section>

      {/* ===== Bằng chứng ===== */}
      <section id="evidence" className="mx-auto max-w-6xl scroll-mt-20 px-4 py-24 sm:px-6">
        <div className="grid grid-cols-1 items-center gap-12 lg:grid-cols-2">
          <Reveal>
            <div>
              <h2 className="text-3xl font-semibold leading-tight tracking-tighter text-ink-strong md:text-4xl">
                Chúng tôi đo bằng dữ liệu thật, không lời hứa
              </h2>
              <ul className="mt-8 space-y-3">
                {[
                  {
                    title: "Giảm fail rate",
                    text: "30.5% câu hỏi thất bại trong chatlog thật, mục tiêu đưa về dưới 15% bằng định tuyến ý định và retrieval toàn kho.",
                  },
                  {
                    title: "Citation kiểm chứng",
                    text: "Trang và dòng trích dẫn là dữ liệu thật từ 926 trang slide và paper arXiv đã tải về máy.",
                  },
                  {
                    title: "Chống regression",
                    text: "24 case eval gate chạy sau mỗi thay đổi agent, không cho phép nâng cấp làm hỏng hành vi cũ.",
                  },
                ].map((item) => (
                  <li key={item.title} className="flex gap-4 rounded-xl bg-surface-2 p-4 ring-1 ring-border/60">
                    <span aria-hidden="true" className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-brand-500" />
                    <div>
                      <h3 className="text-base font-semibold text-ink-strong">{item.title}</h3>
                      <p className="mt-1 text-sm leading-relaxed text-ink-muted">{item.text}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          </Reveal>

          {/* Citation mẫu — đúng ngôn ngữ citation trong chat */}
          <Reveal delay={120}>
            <div className="rounded-2xl bg-surface p-6 shadow-sm ring-1 ring-brand-950/8">
              <p className="text-overline uppercase tracking-[0.08em] text-ink-faint">Bằng chứng</p>
              <p className="mt-4 text-sm leading-relaxed text-ink">
                RAG pipeline ưu tiên tìm đúng chứng cứ: nếu retrieval sai, kết quả
                cuối cùng gần như chắc chắn sai.
              </p>
              <blockquote className="mt-5 border-l-2 border-brand-300 py-0.5 pl-3 font-mono text-xs leading-relaxed text-ink-muted">
                "R (Retrieval): Bước quan trọng nhất, nơi cần tìm đúng chứng cứ..."
              </blockquote>
              <div className="mt-4 flex items-center gap-1.5">
                <FileText size={12} aria-hidden="true" className="text-brand-500" />
                <span className="font-mono text-xs font-semibold text-brand-700">
                  D10 · Trang 16 · dòng 5-7
                </span>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ===== CTA band ===== */}
      <section className="mx-auto max-w-6xl px-4 pb-24 sm:px-6">
        <Reveal>
          <div className="rounded-3xl bg-brand-800 px-6 py-14 text-center shadow-lg ring-1 ring-brand-950/8">
            <h2 className="mx-auto max-w-2xl text-3xl font-semibold leading-tight tracking-tighter text-white md:text-4xl">
              Sẵn sàng đọc sâu và hỏi thật?
            </h2>
            <p className="mx-auto mt-3 max-w-[48ch] text-sm leading-relaxed text-white/70">
              Không cần tài khoản. Mở bài giảng, bôi đen đoạn khó hiểu và để
              AI tutor dẫn bạn tới nguồn.
            </p>
            <Link
              href="/app"
              className="mt-8 inline-flex h-11 items-center gap-2 rounded-lg bg-white px-7 text-sm font-semibold text-brand-800 transition-colors duration-150 ease-quick hover:bg-brand-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/60"
            >
              Vào học ngay
              <ArrowSquareOut size={16} aria-hidden="true" />
            </Link>
          </div>
        </Reveal>
      </section>

      {/* ===== Footer ===== */}
      <footer className="border-t border-border/60 bg-surface-2">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-4 py-8 sm:flex-row sm:px-6">
          <Logo />
          <p className="text-sm text-ink-faint">COMP2010 · AI Thực Chiến · học bằng cách thực chiến</p>
          <p className="text-caption text-ink-faint">© 2026 VLearn</p>
        </div>
      </footer>
    </div>
  );
}