"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import dynamic from "next/dynamic";

const PDFViewer = dynamic(() => import("@/components/PDFViewer"), { ssr: false });

interface SelectionState {
  visible: boolean;
  x: number;
  y: number;
  text: string;
}

interface SlideViewerProps {
  activeDocId: string;
  pdfPath: string;
  totalPages: number;
  sidebarOpen: boolean;
  chatOpen: boolean;
  onToggleSidebar: () => void;
  currentPage: number;
  onPageChange: (page: number) => void;
  onAskAboutSelection?: (text: string) => void;
}

export default function SlideViewer({
  activeDocId,
  pdfPath,
  totalPages,
  sidebarOpen,
  chatOpen,
  onToggleSidebar,
  currentPage,
  onPageChange,
  onAskAboutSelection,
}: SlideViewerProps) {
  const [numPages, setNumPages] = useState<number>(totalPages);
  const [showNotePanel, setShowNotePanel] = useState(false);
  const [scale, setScale] = useState(1.0);
  const [selection, setSelection] = useState<SelectionState>({ visible: false, x: 0, y: 0, text: "" });
  const scrollRef = useRef<HTMLDivElement>(null);

  const onDocumentLoadSuccess = useCallback((pages: number) => {
    setNumPages(pages);
  }, []);

  const zoomIn = () => setScale((s) => Math.min(2.0, +(s + 0.15).toFixed(2)));
  const zoomOut = () => setScale((s) => Math.max(0.5, +(s - 0.15).toFixed(2)));

  useEffect(() => {
    const handleSelectionChange = () => {
      const sel = window.getSelection();
      if (!sel || !sel.toString().trim()) {
        setSelection((s) => (s.visible ? { visible: false, x: 0, y: 0, text: "" } : s));
        return;
      }

      const container = scrollRef.current;
      if (!container) return;

      const containerRect = container.getBoundingClientRect();
      const range = sel.getRangeAt(0);
      const rect = range.getBoundingClientRect();

      if (rect.bottom < containerRect.top || rect.top > containerRect.bottom || rect.width === 0) {
        setSelection((s) => (s.visible ? { visible: false, x: 0, y: 0, text: "" } : s));
        return;
      }

      setSelection({
        visible: true,
        x: rect.left + rect.width / 2 - containerRect.left + container.scrollLeft,
        y: rect.top - containerRect.top + container.scrollTop - 12,
        text: sel.toString().trim(),
      });
    };

    document.addEventListener("selectionchange", handleSelectionChange);
    return () => document.removeEventListener("selectionchange", handleSelectionChange);
  }, []);

  const handleAskAI = () => {
    onAskAboutSelection?.(selection.text);
    setSelection({ visible: false, x: 0, y: 0, text: "" });
    window.getSelection()?.removeAllRanges();
  };

  return (
    <div
      className="flex-1 flex flex-col min-w-0 bg-white transition-[padding] duration-300"
      style={{
        paddingLeft: sidebarOpen ? 280 : 0,
        paddingRight: chatOpen ? 384 : 0,
      }}
    >
      {/* Top bar */}
      <header className="px-5 py-3 border-b border-slate-200 flex items-center justify-between shrink-0 bg-white">
        <div className="flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-2 border-r border-slate-200 pr-3">
            <svg width="34" height="34" viewBox="0 0 38 38" fill="none" className="shrink-0">
              <rect width="38" height="38" rx="8" fill="#134D8B" />
              <text x="7" y="26" fill="white" fontSize="20" fontWeight="900" fontFamily="sans-serif">V</text>
              <rect x="17" y="14" width="14" height="2" rx="1" fill="#d6222f" />
              <rect x="17" y="19" width="12" height="2" rx="1" fill="white" opacity="0.7" />
              <rect x="17" y="24" width="10" height="2" rx="1" fill="white" opacity="0.5" />
            </svg>
            <span className="text-xl font-black tracking-tight">
              <span className="text-[#d6222f]">V</span>
              <span className="text-[#134D8B]">Learn</span>
            </span>
          </div>

          <div className="flex items-center gap-2 text-sm text-slate-500">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
              <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
            </svg>
            <span className="truncate max-w-[200px] text-xs">
              {activeDocId === "d1" ? "Day 1 — AI & LLM Foundation" : "Day 2 — Xác định bài toán cho AI"}
            </span>
          </div>

          {/* Current page indicator */}
          <span className="text-xs text-slate-400 ml-2">
            Trang {currentPage}/{numPages}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button onClick={zoomOut} className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors" title="Thu nhỏ">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M5 12h14" /></svg>
          </button>
          <span className="text-xs text-slate-400 w-10 text-center">{Math.round(scale * 100)}%</span>
          <button onClick={zoomIn} className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors" title="Phóng to">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 5v14M5 12h14" /></svg>
          </button>

          <div className="w-px h-5 bg-slate-200 mx-1" />

          <button
            onClick={() => setShowNotePanel(!showNotePanel)}
            className={`p-1.5 rounded-lg transition-colors ${showNotePanel ? "text-[#134D8B] bg-[#134D8B]/10" : "text-slate-400 hover:text-slate-600 hover:bg-slate-100"}`}
            title="Ghi chú"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 20h9" /><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
            </svg>
          </button>
        </div>
      </header>

      {/* PDF Viewer — scroll all pages */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-auto custom-scrollbar flex bg-slate-100 relative"
      >
        <div className="flex-1 flex justify-center py-4">
          {pdfPath ? (
            <PDFViewer
              pdfPath={pdfPath}
              scale={scale}
              activeDocId={activeDocId}
              onDocumentLoadSuccess={onDocumentLoadSuccess}
              onPageInView={onPageChange}
            />
          ) : (
            <div className="flex items-center justify-center h-96 text-slate-400">
              <p className="text-sm">Chọn một tài liệu từ sidebar để bắt đầu.</p>
            </div>
          )}
        </div>

        {showNotePanel && (
          <div className="w-72 border-l border-slate-200 bg-slate-50 p-4 shrink-0">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-slate-700">Ghi chú — Trang {currentPage}</h3>
              <button onClick={() => setShowNotePanel(false)} className="text-slate-400 hover:text-slate-600">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 6 6 18M6 6l12 12" /></svg>
              </button>
            </div>
            <textarea
              placeholder="Nhập ghi chú của bạn..."
              className="w-full h-40 text-sm p-3 border border-slate-200 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-[#134D8B]/20 focus:border-[#134D8B]"
            />
            <button className="mt-3 w-full py-2 bg-[#134D8B] text-white text-sm font-medium rounded-lg hover:bg-[#0d3b6e] transition-colors">
              Lưu ghi chú
            </button>
          </div>
        )}

        {/* Selection popup */}
        {selection.visible && (
          <div
            className="absolute z-30"
            style={{
              left: selection.x,
              top: selection.y,
              transform: "translate(-50%, -100%)",
            }}
          >
            <button
              onClick={handleAskAI}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-[#134D8B] text-white text-xs font-medium rounded-lg shadow-lg hover:bg-[#0d3b6e] transition-colors whitespace-nowrap"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
              Hỏi AI
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
