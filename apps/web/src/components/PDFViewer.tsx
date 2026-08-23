"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import { CloudX } from "@phosphor-icons/react";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

interface PDFViewerProps {
  pdfPath: string;
  scale: number;
  activeDocId: string;
  onDocumentLoadSuccess: (numPages: number) => void;
  onPageInView?: (page: number) => void;
  /* Kích thước trang gốc (scale 1) — dùng cho Fit-width */
  onPageSize?: (width: number, height: number) => void;
  /* P0-4 — danh sách trang có note (dot đánh dấu) */
  notePages?: number[];
}

export default function PDFViewer({
  pdfPath,
  scale,
  activeDocId,
  onDocumentLoadSuccess,
  onPageInView,
  onPageSize,
  notePages,
}: PDFViewerProps) {
  const [numPages, setNumPages] = useState(0);
  const [retryKey, setRetryKey] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const observerRef = useRef<IntersectionObserver | null>(null);

  const handleLoadSuccess = useCallback(
    ({ numPages: pages }: { numPages: number }) => {
      setNumPages(pages);
      onDocumentLoadSuccess(pages);
    },
    [onDocumentLoadSuccess]
  );

  useEffect(() => {
    if (numPages === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting);
        if (visible.length === 0) return;

        const topEntry = visible.reduce((prev, curr) =>
          prev.boundingClientRect.top < curr.boundingClientRect.top ? prev : curr
        );
        const page = parseInt(topEntry.target.getAttribute("data-page") || "1", 10);
        onPageInView?.(page);
      },
      { threshold: 0.3, rootMargin: "-20% 0px -20% 0px" }
    );

    observerRef.current = observer;

    const elements = containerRef.current?.querySelectorAll("[data-page]");
    elements?.forEach((el) => observer.observe(el));

    return () => {
      observer.disconnect();
    };
  }, [numPages, onPageInView]);

  return (
    <div ref={containerRef}>
      <Document
        key={retryKey}
        file={pdfPath}
        onLoadSuccess={handleLoadSuccess}
        loading={
          /* Skeleton trang + trạng thái — không spinner trần giữa canvas (DESIGN.md §5.3) */
          <div className="flex w-full flex-col items-center gap-4 py-4" role="status" aria-live="polite">
            <div className="skeleton aspect-[4/3] w-full max-w-3xl rounded-lg" />
            <div className="skeleton aspect-[4/3] w-full max-w-3xl rounded-lg opacity-60" />
            <p className="flex items-center gap-2 text-caption text-ink-faint">
              <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" aria-hidden="true" />
              Đang tải slide…
            </p>
          </div>
        }
        error={
          /* Error state + nút Thử lại (G6) */
          <div className="flex flex-col items-center justify-center py-16 text-center" role="alert">
            <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-danger/10">
              <CloudX size={22} aria-hidden="true" className="text-danger" />
            </div>
            <p className="text-sm font-medium text-ink-muted">Không thể tải slide. Kiểm tra kết nối.</p>
            <button
              type="button"
              onClick={() => setRetryKey((k) => k + 1)}
              className="mt-3 h-9 rounded-md bg-brand-600 px-4 text-sm font-medium text-white transition-colors duration-150 ease-quick hover:bg-brand-700 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2"
            >
              Thử lại
            </button>
          </div>
        }
      >
        {/* Trang PDF: gap 24px (quyết định PO — theo draft A; khác DESIGN.md §5.3 cũ) · radius-lg · shadow-page · ring mảnh */}
        <div className="flex flex-col items-center gap-6">
          {Array.from({ length: numPages }, (_, i) => i + 1).map((pageNum) => (
            <div
              key={pageNum}
              id={`${activeDocId}-page-${pageNum}`}
              data-page={pageNum}
              className="relative overflow-hidden rounded-lg bg-surface shadow-page ring-1 ring-brand-950/8 scroll-mt-4"
            >
              {/* P0-4 — dot đánh dấu trang có note */}
              {notePages?.includes(pageNum) && (
                <span
                  aria-hidden="true"
                  className="absolute right-2 top-2 z-10 h-2 w-2 rounded-full bg-brand-500 ring-2 ring-white"
                  title="Có ghi chú"
                />
              )}
              <Page
                pageNumber={pageNum}
                scale={scale}
                renderTextLayer={true}
                renderAnnotationLayer={false}
                onLoadSuccess={
                  pageNum === 1
                    ? (page) => onPageSize?.(page.originalWidth, page.originalHeight)
                    : undefined
                }
              />
            </div>
          ))}
        </div>
      </Document>
    </div>
  );
}
