"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { CaretLeft, SidebarSimple, Sparkle } from "@phosphor-icons/react";
import Sidebar from "@/components/Sidebar";
import SlideViewer from "@/components/SlideViewer";
import ChatPanel from "@/components/ChatPanel";
import { slideDocuments } from "@/components/slideDocs";

export default function Home() {
  const [activeDocId, setActiveDocId] = useState("d1");
  const [pdfPath, setPdfPath] = useState("/d1-slide-hackathon.pdf");
  const [totalPages, setTotalPages] = useState(29);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [selectionText, setSelectionText] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const pendingScrollRef = useRef<number | null>(null);
  /* t28 — paper view tạm (citation [S1] nhảy trang): {source, page} | null */
  const [paperView, setPaperView] = useState<{ source: string; page: number } | null>(null);

  const openPaper = useCallback((source: string, page: number) => {
    setPaperView({ source, page });
  }, []);

  const closePaper = useCallback(() => {
    setPaperView(null);
    setCurrentPage(1);
  }, []);

  /* Deep-link ?paper=<source>&page=<n> — mở thẳng paper view (CDP verify + chia sẻ) */
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const source = params.get("paper");
    const page = parseInt(params.get("page") ?? "1", 10);
    if (source && /^arxiv-[A-Za-z0-9._-]+\.pdf$/.test(source)) {
      setPaperView({ source, page: Number.isFinite(page) ? page : 1 });
    }
  }, []);

  const handleSelectDoc = (docId: string, _title: string, path: string, pages: number) => {
    setActiveDocId(docId);
    setPdfPath(path);
    setTotalPages(pages);
    setCurrentPage(1);
    setPaperView(null); /* t28 — chọn doc khác → thoát paper view */
  };

  const handleJumpToDocPage = useCallback((docId: string, page: number) => {
    if (docId === activeDocId) return;

    const doc = slideDocuments.find((d) => d.id === docId);
    if (!doc) return;

    pendingScrollRef.current = page;
    setActiveDocId(doc.id);
    setPdfPath(doc.pdfPath);
    setTotalPages(doc.pages);
    setCurrentPage(page);
    setPaperView(null); /* t28 — nhảy doc → thoát paper view */
  }, [activeDocId]);

  const handleAskAboutSelection = useCallback((text: string) => {
    setChatOpen(true);
    setSelectionText(text);
  }, []);

  /* B1 — chat mặc định MỞ trên desktop ≥1280px (Q4 user đã chốt).
     Init phía client theo breakpoint tránh hydration mismatch. */
  useEffect(() => {
    if (window.innerWidth >= 1280) setChatOpen(true);
  }, []);

  useEffect(() => {
    if (pendingScrollRef.current === null) return;

    const page = pendingScrollRef.current;
    const timer = setTimeout(() => {
      const el = document.getElementById(`${activeDocId}-page-${page}`);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "start" });
        /* Flash highlight 1.2s trang đích (jump-to-page từ citation) */
        el.classList.remove("page-flash");
        void el.offsetWidth; /* reflow để chạy lại animation */
        el.classList.add("page-flash");
        window.setTimeout(() => el.classList.remove("page-flash"), 1300);
      }
      pendingScrollRef.current = null;
    }, 800);

    return () => clearTimeout(timer);
  }, [activeDocId, totalPages]);

  const topBarToggleClass = (active: boolean) =>
    `flex h-8 items-center gap-1.5 rounded-lg px-3 text-sm transition-colors duration-150 ease-quick
     focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/60
     ${active
       ? "bg-white/15 text-white"
       : "text-white/70 hover:bg-white/10 hover:text-white active:bg-white/15"}`;

  return (
    <div className="flex h-full flex-col">
      {/* ===== Top navigation bar — DESIGN.md v2 §5.1: h-12 bg-brand-800 ===== */}
      <header className="z-30 flex h-12 shrink-0 items-center gap-2 bg-brand-800 px-3 text-white sm:gap-3 sm:px-4">
        {/* Nút Quay lại — về trang giới thiệu (/) thay vì history.back() */}
        <a
          href="/"
          aria-label="Về trang giới thiệu"
          className="flex h-8 items-center gap-1 rounded-lg px-2 text-sm text-white/70 transition-colors duration-150 ease-quick hover:bg-white/10 hover:text-white active:bg-white/15 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/60"
        >
          <CaretLeft size={16} aria-hidden="true" />
          <span className="hidden sm:inline">Quay lại</span>
        </a>

        <div className="flex min-w-0 items-center gap-2.5">
          <svg width="22" height="22" viewBox="0 0 38 38" fill="none" className="shrink-0" aria-hidden="true">
            <rect width="38" height="38" rx="8" fill="white" />
            <text x="9" y="26" fill="#134D8B" fontSize="18" fontWeight="900">V</text>
          </svg>
          <span className="truncate text-sm font-semibold">COMP2010 — AI Thực Chiến</span>
        </div>

        <div className="flex-1" />

        {/* Cụm phải — segmented control 2 toggle panel theo draft A (F6) */}
        <div className="flex items-center gap-2 rounded-lg border border-white/5 bg-black/20 p-1">
          <button
            type="button"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            aria-expanded={sidebarOpen}
            aria-controls="sidebar-panel"
            title={sidebarOpen ? "Đóng học liệu" : "Mở học liệu"}
            className={topBarToggleClass(sidebarOpen)}
          >
            <SidebarSimple size={16} aria-hidden="true" />
            <span className="hidden md:inline">Học liệu</span>
          </button>

          <button
            type="button"
            onClick={() => setChatOpen(!chatOpen)}
            aria-expanded={chatOpen}
            aria-controls="chat-panel"
            title={chatOpen ? "Đóng trợ lý AI" : "Mở trợ lý AI"}
            className={topBarToggleClass(chatOpen)}
          >
            <Sparkle size={16} aria-hidden="true" />
            {/* Dot báo tutor đang trả lời — brand-300 (đồng bộ isTyping từ ChatPanel) */}
            {isTyping && (
              <span
                role="status"
                aria-label="Tutor đang trả lời"
                className="h-1.5 w-1.5 animate-pulse rounded-full bg-brand-300"
              />
            )}
            <span className="hidden md:inline">Trợ lý AI</span>
          </button>
        </div>
      </header>

      {/* ===== Main 3-panel workspace =====
          Sidebar: in-flow ≥lg (w-64) · overlay <lg · Chat: in-flow ≥xl (w-96) · overlay <xl */}
      <div className="relative flex min-h-0 flex-1 overflow-hidden">
        {/* Edge toggle pill — mép trái, chỉ khi sidebar đóng (draft A §5.5) */}
        {!sidebarOpen && (
          <button
            type="button"
            onClick={() => setSidebarOpen(true)}
            aria-label="Mở danh sách slide"
            aria-expanded="false"
            aria-controls="sidebar-panel"
            title="Mở danh sách slide"
            className="absolute left-0 top-1/2 z-20 flex h-20 w-9 -translate-y-1/2 flex-col items-center justify-center gap-1 rounded-r-full border-l border-white/10 bg-brand-600 text-white opacity-85 shadow-md transition-[transform,opacity,background-color] duration-150 ease-quick hover:bg-brand-700 hover:opacity-100 focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2"
          >
            <SidebarSimple size={18} aria-hidden="true" />
            <span className="text-overline font-bold uppercase leading-none tracking-widest [writing-mode:vertical-rl]">Slide</span>
          </button>
        )}

        <Sidebar
          activeDocId={activeDocId}
          onSelectDoc={handleSelectDoc}
          isOpen={sidebarOpen}
          onToggle={() => setSidebarOpen(!sidebarOpen)}
        />
        <SlideViewer
          activeDocId={activeDocId}
          pdfPath={pdfPath}
          totalPages={totalPages}
          currentPage={currentPage}
          onPageChange={setCurrentPage}
          onAskAboutSelection={handleAskAboutSelection}
          onSelectDoc={handleSelectDoc}
          /* t28 — paper view tạm + thoát */
          paperView={paperView}
          onExitPaper={closePaper}
        />
        <ChatPanel
          activeDocId={activeDocId}
          currentPage={currentPage}
          isOpen={chatOpen}
          onToggle={() => setChatOpen(!chatOpen)}
          onJumpToDocPage={handleJumpToDocPage}
          onOpenPaper={openPaper}
          selectionText={selectionText}
          onSelectionConsumed={() => setSelectionText("")}
          onTypingChange={setIsTyping}
        />
      </div>
    </div>
  );
}
