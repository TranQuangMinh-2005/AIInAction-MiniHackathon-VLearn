"use client";

import { useState, useCallback, useRef, useEffect, useLayoutEffect } from "react";
import dynamic from "next/dynamic";
import {
  CaretDown,
  ChatCircleDots,
  Check,
  CircleNotch,
  CornersOut,
  FilePdf,
  Minus,
  NotePencil,
  Plus,
  X,
} from "@phosphor-icons/react";
import { slideDocuments } from "@/components/slideDocs";
import { getLearnerId } from "@/lib/learner";

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
  currentPage: number;
  onPageChange: (page: number) => void;
  onAskAboutSelection?: (text: string) => void;
  /* Doc switcher (F5) — chuyển tài liệu không cần sidebar */
  onSelectDoc?: (docId: string, docTitle: string, pdfPath: string, totalPages: number) => void;
  /* t28 — paper view tạm (citation paper [S1] nhảy trang) */
  paperView?: { source: string; page: number } | null;
  onExitPaper?: () => void;
}

const MIN_SCALE = 0.5;
const MAX_SCALE = 2.0;

export default function SlideViewer({
  activeDocId,
  pdfPath,
  totalPages,
  currentPage,
  onPageChange,
  onAskAboutSelection,
  onSelectDoc,
  paperView,
  onExitPaper,
}: SlideViewerProps) {
  const [numPages, setNumPages] = useState<number>(totalPages);
  const [showNotePanel, setShowNotePanel] = useState(false);
  const [scale, setScale] = useState(1.0);
  const [basePageWidth, setBasePageWidth] = useState<number | null>(null);
  const [switcherOpen, setSwitcherOpen] = useState(false);
  const [selection, setSelection] = useState<SelectionState>({ visible: false, x: 0, y: 0, text: "" });

  /* t28 — viewer đang hiển thị paper tạm hay slide */
  const agentApiUrl = process.env.NEXT_PUBLIC_AGENT_API_URL ?? "http://localhost:8000";
  const viewingPaper = Boolean(paperView);
  /* t40 — dùng ABSOLUTE URL (không relative): trước đây /api/papers… tương đối
     trúng web origin → 404 (QA2 t28 verify). Không phụ thuộc proxy web. */
  const viewerPdfPath = paperView
    ? `${agentApiUrl}/api/papers/${encodeURIComponent(paperView.source)}/pdf`
    : pdfPath;
  const viewerDocId = paperView
    ? `paper-${paperView.source.replace(/[^A-Za-z0-9.-]/g, "-")}`
    : activeDocId;

  /* t28 — paper mở: scroll + flash đúng trang khi PDF load xong */
  useEffect(() => {
    if (!paperView) return;
    const timer = window.setTimeout(() => {
      const el = document.getElementById(`${viewerDocId}-page-${paperView.page}`);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "start" });
        el.classList.remove("page-flash");
        void el.offsetWidth;
        el.classList.add("page-flash");
        window.setTimeout(() => el.classList.remove("page-flash"), 1300);
      }
    }, 900);
    return () => window.clearTimeout(timer);
  }, [paperView, numPages, viewerDocId]);

  /* F3 — ghi chú localStorage: vlearn-notes:{docId}:{page} */
  const [noteText, setNoteText] = useState("");
  const [noteState, setNoteState] = useState<"idle" | "saving" | "saved">("idle");
  /* P0-4 — notes sync qua Memory A-06 + dot trang có note */
  const learnerId = getLearnerId();
  const [notePages, setNotePages] = useState<number[]>([]);

  const scrollRef = useRef<HTMLDivElement>(null);
  const switcherRef = useRef<HTMLDivElement>(null);
  const popupRef = useRef<HTMLDivElement>(null);
  const selectionTimerRef = useRef<number | null>(null);
  const noteTimersRef = useRef<number[]>([]);

  const activeDoc = slideDocuments.find((d) => d.id === activeDocId);

  const clampScale = (s: number) => Math.min(MAX_SCALE, Math.max(MIN_SCALE, +s.toFixed(2)));

  const onDocumentLoadSuccess = useCallback((pages: number) => {
    setNumPages(pages);
  }, []);

  const handlePageSize = useCallback((width: number) => {
    setBasePageWidth(width);
  }, []);

  const zoomIn = () => setScale((s) => clampScale(s + 0.15));
  const zoomOut = () => setScale((s) => clampScale(s - 0.15));
  const resetZoom = () => setScale(1.0);

  /* Fit-width: scale = (containerWidth - padding) / pageWidth gốc */
  const fitWidth = () => {
    const container = scrollRef.current;
    if (!container || !basePageWidth) return;
    const available = container.clientWidth - 64; // p-8 (32px mỗi bên)
    setScale(clampScale(available / basePageWidth));
  };

  /* ---------- Doc switcher (F5) ---------- */
  useEffect(() => {
    if (!switcherOpen) return;
    const onDown = (e: MouseEvent) => {
      if (switcherRef.current && !switcherRef.current.contains(e.target as Node)) {
        setSwitcherOpen(false);
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setSwitcherOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [switcherOpen]);

  /* ---------- Ghi chú (F3) — P0-4: sync qua Memory, fallback localStorage ---------- */
  useEffect(() => {
    if (!showNotePanel) return;
    let local = "";
    try {
      local = localStorage.getItem(`vlearn-notes:${activeDocId}:${currentPage}`) ?? "";
    } catch {
      local = "";
    }
    setNoteText(local);
    setNoteState("idle");
    if (!learnerId) return;

    let cancelled = false;
    (async () => {
      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_AGENT_API_URL ?? "http://localhost:8000"}/api/learners/${encodeURIComponent(learnerId)}/notes?doc_id=${encodeURIComponent(activeDocId)}`,
          { cache: "no-store" }
        );
        if (!response.ok) return;
        const data = (await response.json()) as {
          notes: { doc_id: string; page: number; text: string }[];
        };
        if (cancelled) return;
        const pages = data.notes.map((n) => n.page);
        setNotePages(pages);
        const current = data.notes.find((n) => n.page === currentPage);
        if (current) setNoteText(current.text);
      } catch {
        /* offline/backend ngắt → giữ fallback localStorage */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [showNotePanel, activeDocId, currentPage, learnerId]);

  useEffect(() => {
    /* P0-4 — đổi doc → tải lại danh sách trang có note (cho dot) */
    if (!learnerId) return;
    let cancelled = false;
    (async () => {
      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_AGENT_API_URL ?? "http://localhost:8000"}/api/learners/${encodeURIComponent(learnerId)}/notes?doc_id=${encodeURIComponent(activeDocId)}`,
          { cache: "no-store" }
        );
        if (!response.ok) return;
        const data = (await response.json()) as {
          notes: { doc_id: string; page: number }[];
        };
        if (!cancelled) setNotePages(data.notes.map((n) => n.page));
      } catch {
        /* offline → không có dot từ server; giữ state cũ */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [activeDocId, learnerId, totalPages]);

  useEffect(() => {
    const timers = noteTimersRef.current;
    return () => timers.forEach((t) => window.clearTimeout(t));
  }, []);

  const handleSaveNote = () => {
    if (noteState !== "idle") return;
    setNoteState("saving");
    const key = `vlearn-notes:${activeDocId}:${currentPage}`;
    try {
      if (noteText.trim()) localStorage.setItem(key, noteText);
      else localStorage.removeItem(key);
    } catch {
      /* localStorage không khả dụng — feedback vẫn chạy đúng luồng */
    }
    /* P0-4 — đồng bộ lên Memory (text rỗng = xoá); lỗi mạng im lặng (fallback local) */
    if (learnerId) {
      fetch(
        `${process.env.NEXT_PUBLIC_AGENT_API_URL ?? "http://localhost:8000"}/api/learners/${encodeURIComponent(learnerId)}/notes`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ doc_id: activeDocId, page: currentPage, text: noteText }),
          cache: "no-store",
        }
      )
        .then((response) => {
          if (!response.ok) return;
          setNotePages((prev) => {
            const next = new Set(prev);
            if (noteText.trim()) next.add(currentPage);
            else next.delete(currentPage);
            return [...next].sort((a, b) => a - b);
          });
        })
        .catch(() => {
          /* offline → chỉ lưu local */
        });
    }
    const t1 = window.setTimeout(() => {
      setNoteState("saved");
      const t2 = window.setTimeout(() => setNoteState("idle"), 2000);
      noteTimersRef.current.push(t2);
    }, 400);
    noteTimersRef.current.push(t1);
  };

  /* ---------- Selection popup (F7): debounce 80ms + clamp ±16px ---------- */
  const clearSelection = useCallback(() => {
    setSelection((s) => (s.visible ? { visible: false, x: 0, y: 0, text: "" } : s));
  }, []);

  useEffect(() => {
    const handleSelectionChange = () => {
      if (selectionTimerRef.current) window.clearTimeout(selectionTimerRef.current);
      selectionTimerRef.current = window.setTimeout(() => {
        const sel = window.getSelection();
        if (!sel || !sel.toString().trim() || sel.rangeCount === 0) {
          clearSelection();
          return;
        }
        const container = scrollRef.current;
        if (!container) return;
        /* t38 — bug user: popup "Hỏi AI" hiện nhầm khi bôi đen NGOÀI vùng slide.
           Chỉ hiện khi selection thực sự thuộc vùng PDF/slide:
           1) chặn chọn trong textarea/input (vd panel Ghi chú nằm trong container);
           2) CẢ HAI đầu range phải nằm trong scrollRef (loại sidebar/chat/header
              — trước chỉ check trục dọc nên chọn chữ bên cạnh vẫn lọt);
           3) rect phải giao container theo CẢ HAI trục ngang + dọc. */
        const active = document.activeElement;
        if (
          active &&
          (active.tagName === "TEXTAREA" || active.tagName === "INPUT")
        ) {
          clearSelection();
          return;
        }
        const range = sel.getRangeAt(0);
        const startIn = container.contains(range.startContainer);
        const endIn = container.contains(range.endContainer);
        if (!startIn || !endIn) {
          clearSelection();
          return;
        }
        const containerRect = container.getBoundingClientRect();
        const rect = range.getBoundingClientRect();
        const intersects =
          rect.bottom > containerRect.top &&
          rect.top < containerRect.bottom &&
          rect.right > containerRect.left &&
          rect.left < containerRect.right;
        if (!intersects || rect.width === 0) {
          clearSelection();
          return;
        }
        setSelection({
          visible: true,
          x: rect.left + rect.width / 2 - containerRect.left + container.scrollLeft,
          y: rect.top - containerRect.top + container.scrollTop - 12,
          text: sel.toString().trim(),
        });
      }, 80);
    };

    document.addEventListener("selectionchange", handleSelectionChange);
    return () => {
      document.removeEventListener("selectionchange", handleSelectionChange);
      if (selectionTimerRef.current) window.clearTimeout(selectionTimerRef.current);
    };
  }, [clearSelection]);

  /* Clamp popup trong viewport ±16px */
  useLayoutEffect(() => {
    if (!selection.visible) return;
    const container = scrollRef.current;
    const popup = popupRef.current;
    if (!container || !popup) return;
    const cRect = container.getBoundingClientRect();
    const pRect = popup.getBoundingClientRect();
    const vx = cRect.left + (selection.x - container.scrollLeft);
    const half = pRect.width / 2;
    const minX = cRect.left + 16 + half;
    const maxX = cRect.right - 16 - half;
    const clamped = Math.min(Math.max(vx, minX), Math.max(minX, maxX));
    if (Math.abs(clamped - vx) > 0.5) {
      setSelection((s) => ({ ...s, x: clamped - cRect.left + container.scrollLeft }));
    }
  }, [selection]);

  const handleAskAI = () => {
    onAskAboutSelection?.(selection.text);
    setSelection({ visible: false, x: 0, y: 0, text: "" });
    window.getSelection()?.removeAllRanges();
  };

  const showQuote = selection.text.length > 120;
  const quoteText = showQuote ? `“${selection.text.slice(0, 120)}…”` : "";

  return (
    /* Bỏ padding-hack (F2): sidebar/chat chiếm chỗ thật trong flow ≥lg/≥xl */
    <div className="relative z-0 flex min-w-0 flex-1 flex-col bg-canvas">
      {/* Toolbar h-12 — draft A */}
      <header className="flex h-12 shrink-0 items-center justify-between border-b border-border bg-surface px-4">
        {/* Trái: doc switcher chip (F5) — ẩn khi đang xem paper (t28) */}
        <div className="relative flex min-w-0 items-center gap-3" ref={switcherRef}>
          {!viewingPaper && (
          <button
            type="button"
            onClick={() => setSwitcherOpen((o) => !o)}
            aria-haspopup="listbox"
            aria-expanded={switcherOpen}
            title="Đổi tài liệu"
            className="group flex min-w-0 items-center gap-2 rounded-md py-1.5 pl-1 pr-2 transition-colors duration-150 ease-quick hover:bg-surface-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2"
          >
            <span className="rounded bg-brand-50 px-1.5 py-0.5 text-caption font-bold uppercase tracking-tight text-brand-700 ring-1 ring-brand-100">
              {activeDoc?.code ?? "D01"}
            </span>
            <span className="truncate text-sm font-semibold tracking-tight text-ink-strong">
              {activeDoc?.title ?? "Tài liệu"}
            </span>
            <CaretDown size={16} aria-hidden="true" className="shrink-0 text-ink-faint transition-colors duration-150 ease-quick group-hover:text-ink" />
          </button>
          )}

          {/* Page indicator — mono, cập nhật theo page-in-view */}
          <span className="hidden text-mono text-ink-faint md:inline">
            Trang {currentPage}/{numPages}
          </span>

          {/* t28 — đang xem paper: badge + nút Thoát về slide */}
          {viewingPaper && paperView && (
            <div className="flex min-w-0 items-center gap-2">
              <span className="rounded-md bg-brand-50 px-2 py-1 font-mono text-caption font-semibold text-brand-700 ring-1 ring-brand-100">
                Paper · {paperView.source}
              </span>
              <button
                type="button"
                onClick={onExitPaper}
                aria-label="Thoát paper về slide"
                title="Quay lại slide"
                className="flex h-8 items-center gap-1 rounded-md border border-brand-300 px-2.5 text-xs font-semibold text-brand-700 transition-colors duration-150 ease-quick hover:bg-brand-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
              >
                <X size={14} aria-hidden="true" />
                Thoát
              </button>
            </div>
          )}

          {/* Dropdown đổi tài liệu */}
          {switcherOpen && (
            <div
              role="listbox"
              aria-label="Chọn tài liệu"
              className="absolute left-0 top-full z-40 mt-1 w-72 animate-scale-in rounded-lg bg-surface p-1 shadow-md ring-1 ring-brand-950/8"
            >
              {slideDocuments.map((doc) => {
                const selected = doc.id === activeDocId;
                return (
                  <button
                    key={doc.id}
                    role="option"
                    aria-selected={selected}
                    onClick={() => {
                      onSelectDoc?.(doc.id, doc.title, doc.pdfPath, doc.pages);
                      setSwitcherOpen(false);
                    }}
                    className={`flex w-full items-center gap-3 rounded-md px-3 py-2 text-left transition-colors duration-150 ease-quick focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400
                      ${selected ? "bg-brand-50" : "hover:bg-surface-2"}`}
                  >
                    <FilePdf size={16} aria-hidden="true" className={`shrink-0 ${selected ? "text-brand-600" : "text-ink-faint"}`} />
                    <span className="min-w-0 flex-1">
                      <span className={`block truncate text-sm font-medium ${selected ? "text-brand-700" : "text-ink"}`}>
                        {doc.title}
                      </span>
                      <span className="block text-mono uppercase tracking-tight text-ink-faint">
                        {doc.code} · {doc.pages} trang
                      </span>
                    </span>
                    {selected && <Check size={16} aria-hidden="true" className="shrink-0 text-brand-600" />}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Phải: cụm zoom trên track + ghi chú — draft A */}
        <div className="flex shrink-0 items-center gap-3">
          <div className="flex items-center rounded-md bg-surface-2 p-0.5 shadow-xs ring-1 ring-border/50">
            <button
              type="button"
              onClick={fitWidth}
              title="Vừa chiều rộng"
              aria-label="Vừa chiều rộng"
              className="flex h-8 w-8 items-center justify-center rounded text-ink-faint transition-colors duration-150 ease-quick hover:bg-surface hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
            >
              <CornersOut size={16} aria-hidden="true" />
            </button>
            <button
              type="button"
              onClick={zoomOut}
              title="Thu nhỏ"
              aria-label="Thu nhỏ"
              className="flex h-8 w-8 items-center justify-center rounded text-ink-faint transition-colors duration-150 ease-quick hover:bg-surface hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
            >
              <Minus size={16} aria-hidden="true" />
            </button>
            <button
              type="button"
              onClick={resetZoom}
              title="Đặt lại 100%"
              aria-label="Đặt lại 100%"
              className="h-8 rounded px-2 text-mono font-semibold text-ink-muted transition-colors duration-150 ease-quick hover:bg-surface hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
            >
              {Math.round(scale * 100)}%
            </button>
            <button
              type="button"
              onClick={zoomIn}
              title="Phóng to"
              aria-label="Phóng to"
              className="flex h-8 w-8 items-center justify-center rounded text-ink-faint transition-colors duration-150 ease-quick hover:bg-surface hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
            >
              <Plus size={16} aria-hidden="true" />
            </button>
          </div>

          <div className="h-5 w-px bg-border" aria-hidden="true" />

          <button
            type="button"
            onClick={() => setShowNotePanel((v) => !v)}
            aria-expanded={showNotePanel}
            aria-label="Ghi chú"
            title="Ghi chú"
            className={`flex h-8 w-8 items-center justify-center rounded-md transition-colors duration-150 ease-quick focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2
              ${showNotePanel ? "bg-brand-50 text-brand-600" : "text-ink-faint hover:bg-brand-50 hover:text-brand-600"}`}
          >
            <NotePencil size={16} aria-hidden="true" />
          </button>
        </div>
      </header>

      {/* PDF Viewer — scroll tất cả trang; canvas theo draft A */}
      <div ref={scrollRef} className="relative flex flex-1 overflow-auto custom-scrollbar">
        <div className="flex flex-1 justify-center p-8">
          {pdfPath ? (
            <PDFViewer
              pdfPath={viewerPdfPath}
              scale={scale}
              activeDocId={viewerDocId}
              onDocumentLoadSuccess={onDocumentLoadSuccess}
              onPageInView={onPageChange}
              onPageSize={handlePageSize}
              notePages={notePages}
            />
          ) : (
            /* Empty state — không có PDF */
            <div className="flex h-96 flex-col items-center justify-center text-center">
              <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-surface shadow-sm ring-1 ring-border">
                <FilePdf size={22} aria-hidden="true" className="text-ink-faint" />
              </div>
              <p className="text-sm font-medium text-ink-muted">Chưa có tài liệu nào</p>
              <p className="mt-1 text-xs text-ink-faint">Chọn một tài liệu từ học liệu để bắt đầu.</p>
            </div>
          )}
        </div>

        {/* Ghi chú panel (F3) */}
        {showNotePanel && (
          <div className="w-72 shrink-0 animate-fade-up bg-surface p-4 shadow-md">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-ink-strong">Ghi chú — Trang {currentPage}</h3>
              <button
                type="button"
                onClick={() => setShowNotePanel(false)}
                aria-label="Đóng ghi chú"
                className="rounded-md p-1 text-ink-faint transition-colors duration-150 ease-quick hover:bg-surface-2 hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2"
              >
                <X size={16} aria-hidden="true" />
              </button>
            </div>
            <textarea
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
              placeholder="Nhập ghi chú của bạn..."
              aria-label={`Ghi chú trang ${currentPage}`}
              className="h-40 w-full resize-none rounded-md border border-border p-3 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
            />
            <button
              type="button"
              onClick={handleSaveNote}
              disabled={noteState !== "idle"}
              className={`mt-3 flex h-9 w-full items-center justify-center gap-1.5 rounded-md text-sm font-medium transition-colors duration-150 ease-quick active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2
                ${noteState === "saved"
                  ? "bg-success text-white"
                  : "bg-brand-600 text-white hover:bg-brand-700 active:bg-brand-800"}`}
            >
              {noteState === "saving" && (
                <>
                  <CircleNotch size={16} aria-hidden="true" className="animate-spin" />
                  Đang lưu…
                </>
              )}
              {noteState === "saved" && (
                <>
                  <Check size={16} aria-hidden="true" />
                  Đã lưu
                </>
              )}
              {noteState === "idle" && "Lưu ghi chú"}
            </button>
          </div>
        )}

        {/* Selection popup "Hỏi AI" (F7) */}
        {selection.visible && (
          <div
            ref={popupRef}
            className="absolute z-30 w-fit animate-scale-in"
            style={{
              left: selection.x,
              top: selection.y,
              transform: "translate(-50%, -100%)",
            }}
          >
            <button
              type="button"
              onClick={handleAskAI}
              className="relative flex h-8 items-center gap-1.5 whitespace-nowrap rounded-md bg-brand-600 px-3 text-xs font-medium text-white shadow-lg transition-colors duration-150 ease-quick hover:bg-brand-700 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2"
            >
              <ChatCircleDots size={14} aria-hidden="true" />
              Hỏi AI
              {/* Mũi tên nhỏ */}
              <span
                aria-hidden="true"
                className="absolute -bottom-1 left-1/2 h-2 w-2 -translate-x-1/2 rotate-45 bg-brand-600"
              />
            </button>
            {/* Quote rút gọn khi >120 ký tự */}
            {showQuote && (
              <p className="mx-auto mt-2 w-fit max-w-[280px] truncate rounded-md bg-brand-950/80 px-2 py-1 text-caption leading-4 text-white/90">
                {quoteText}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
