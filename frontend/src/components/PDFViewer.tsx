"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url
).toString();

interface PDFViewerProps {
  pdfPath: string;
  scale: number;
  onDocumentLoadSuccess: (numPages: number) => void;
  onPageInView: (page: number) => void;
}

export default function PDFViewer({ pdfPath, scale, onDocumentLoadSuccess, onPageInView }: PDFViewerProps) {
  const [numPages, setNumPages] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const pageRefs = useRef<Map<number, HTMLDivElement>>(new Map());
  const lastPageRef = useRef(0);
  const onPageInViewRef = useRef(onPageInView);
  onPageInViewRef.current = onPageInView;

  const handleLoadSuccess = useCallback(
    ({ numPages: pages }: { numPages: number }) => {
      setNumPages(pages);
      onDocumentLoadSuccess(pages);
    },
    [onDocumentLoadSuccess]
  );

  useEffect(() => {
    const container = containerRef.current;
    if (!container || numPages === 0) return;

    let ticking = false;
    const observer = new IntersectionObserver(
      (entries) => {
        if (ticking) return;
        ticking = true;
        requestAnimationFrame(() => {
          let maxVisible: { page: number; ratio: number } | null = null;
          entries.forEach((entry) => {
            const page = Number(entry.target.getAttribute("data-page"));
            if (entry.isIntersecting && entry.intersectionRatio > (maxVisible?.ratio ?? 0)) {
              maxVisible = { page, ratio: entry.intersectionRatio };
            }
          });
          if (maxVisible && maxVisible.page !== lastPageRef.current) {
            lastPageRef.current = maxVisible.page;
            onPageInViewRef.current(maxVisible.page);
          }
          ticking = false;
        });
      },
      { root: container, threshold: [0.25, 0.5, 0.75] }
    );

    pageRefs.current.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [numPages]);

  const setPageRef = useCallback((page: number, el: HTMLDivElement | null) => {
    if (el) pageRefs.current.set(page, el);
    else pageRefs.current.delete(page);
  }, []);

  return (
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
          <div className="text-center">
            <p className="text-sm">Không thể tải slide. Vui lòng thử lại.</p>
          </div>
        </div>
      }
    >
      <div ref={containerRef} className="space-y-2 flex flex-col items-center">
        {Array.from({ length: numPages }, (_, i) => i + 1).map((pageNum) => (
          <div
            key={pageNum}
            ref={(el) => setPageRef(pageNum, el)}
            data-page={pageNum}
            className="shadow-lg bg-white"
          >
            <Page
              pageNumber={pageNum}
              scale={scale}
              renderTextLayer={false}
              renderAnnotationLayer={false}
            />
          </div>
        ))}
      </div>
    </Document>
  );
}
