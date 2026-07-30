"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

interface PDFViewerProps {
  pdfPath: string;
  scale: number;
  activeDocId: string;
  onDocumentLoadSuccess: (numPages: number) => void;
  onPageInView?: (page: number) => void;
}

export default function PDFViewer({
  pdfPath,
  scale,
  activeDocId,
  onDocumentLoadSuccess,
  onPageInView,
}: PDFViewerProps) {
  const [numPages, setNumPages] = useState(0);
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
        file={pdfPath}
        onLoadSuccess={handleLoadSuccess}
        loading={
          <div className="flex items-center justify-center h-96 text-slate-400">
            <div className="text-center">
              <div className="w-8 h-8 border-2 border-[#134D8B] border-t-transparent rounded-full animate-spin mx-auto mb-3" />
              <p className="text-sm">Đang tải slide...</p>
            </div>
          </div>
        }
        error={
          <div className="flex items-center justify-center h-96 text-slate-400">
            <p className="text-sm">Không thể tải slide. Vui lòng thử lại.</p>
          </div>
        }
      >
        <div className="space-y-2 flex flex-col items-center">
          {Array.from({ length: numPages }, (_, i) => i + 1).map((pageNum) => (
            <div
              key={pageNum}
              id={`${activeDocId}-page-${pageNum}`}
              data-page={pageNum}
              className="shadow-lg bg-white scroll-mt-4"
            >
              <Page
                pageNumber={pageNum}
                scale={scale}
              renderTextLayer={true}
              renderAnnotationLayer={false}
              />
            </div>
          ))}
        </div>
      </Document>
    </div>
  );
}
