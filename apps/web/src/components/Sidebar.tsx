"use client";

import { useState } from "react";
import { CaretDown, FileText, Files, Folder, X } from "@phosphor-icons/react";
import { slideDocuments } from "@/components/slideDocs";

interface SidebarProps {
  activeDocId: string;
  onSelectDoc: (docId: string, docTitle: string, pdfPath: string, totalPages: number) => void;
  isOpen: boolean;
  onToggle: () => void;
}

export default function Sidebar({ activeDocId, onSelectDoc, isOpen, onToggle }: SidebarProps) {
  const [expanded, setExpanded] = useState(true);

  return (
    <>
      {/* Backdrop — chỉ overlay <lg, fade-in 200ms (v2 §5.2: bg-brand-950/30) */}
      {isOpen && (
        <div
          className="fixed inset-0 z-20 animate-fade-in bg-brand-950/30 lg:hidden"
          onClick={onToggle}
          aria-hidden="true"
        />
      )}

      <aside
        id="sidebar-panel"
        aria-label="Học liệu môn học"
        className={`fixed bottom-0 left-0 top-12 z-30 flex w-64 shrink-0 flex-col overflow-hidden bg-surface transition-transform duration-[240ms] ease-panel
          ${isOpen ? "translate-x-0 lg:static" : "-translate-x-full lg:absolute lg:bottom-0 lg:left-0 lg:top-0"}`}
      >
        {/* Header — overline 11/600 ink-faint (draft A) */}
        <div className="flex shrink-0 items-center justify-between p-4">
          <h2 className="text-overline uppercase text-ink-faint">Học liệu môn học</h2>
          {/* Nút ✕ chỉ hợp lý trên overlay <lg */}
          <button
            onClick={onToggle}
            aria-label="Đóng học liệu"
            className="rounded-md p-1 text-ink-faint transition-colors duration-150 ease-quick hover:bg-surface-2 hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2 lg:hidden"
          >
            <X size={16} aria-hidden="true" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-3 pb-3 custom-scrollbar">
          {/* Hàng group — draft A: folder icon + chevron-down */}
          <button
            onClick={() => setExpanded(!expanded)}
            aria-expanded={expanded}
            className="group flex w-full cursor-pointer items-center justify-between px-3 py-2 text-left transition-colors duration-150 ease-quick hover:bg-surface-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2"
          >
            <div className="flex min-w-0 items-center gap-2">
              <Folder size={16} aria-hidden="true" className="shrink-0 text-brand-600" />
              <span className="min-w-0">
                <span className="block truncate text-sm font-semibold text-ink-strong">
                  AI Thực Chiến — Hackathon
                </span>
                <span className="block text-caption text-ink-faint">
                  {slideDocuments.length} tài liệu
                </span>
              </span>
            </div>
            <CaretDown
              size={16}
              aria-hidden="true"
              className={`shrink-0 text-ink-faint transition-transform duration-150 ease-quick group-hover:text-ink ${expanded ? "" : "-rotate-90"}`}
            />
          </button>

          {expanded && (
            <div className="mt-1 space-y-1">
              {slideDocuments.length === 0 ? (
                /* Empty state — G6 (v2 §5.2) */
                <div className="flex flex-col items-center justify-center px-4 py-10 text-center">
                  <Files size={28} aria-hidden="true" className="text-ink-faint" />
                  <p className="mt-2 text-sm font-medium text-ink-muted">Chưa có tài liệu nào</p>
                </div>
              ) : (
                slideDocuments.map((doc) => {
                  const selected = activeDocId === doc.id;
                  return (
                    <button
                      key={doc.id}
                      onClick={() => onSelectDoc(doc.id, doc.title, doc.pdfPath, doc.pages)}
                      aria-current={selected ? "true" : undefined}
                      className={`block w-full rounded-lg px-3 py-2.5 text-left transition-all duration-150 ease-quick focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2
                        ${selected
                          ? "bg-brand-50 shadow-sm ring-1 ring-brand-200"
                          : "hover:bg-surface-2 active:bg-brand-100"}`}
                    >
                      <span className="flex gap-3">
                        <FileText
                          size={16}
                          aria-hidden="true"
                          className={`mt-0.5 shrink-0 ${selected ? "text-brand-600" : "text-ink-faint"}`}
                        />
                        <span className="min-w-0">
                          <span
                            className={`block truncate text-sm leading-tight ${
                              selected ? "font-semibold text-brand-700" : "font-medium text-ink"
                            }`}
                          >
                            {doc.title}
                          </span>
                          <span
                            className={`mt-1 block text-caption ${
                              selected ? "text-brand-500" : "text-ink-faint"
                            }`}
                          >
                            {doc.code} · {doc.pages} trang
                          </span>
                        </span>
                      </span>
                    </button>
                  );
                })
              )}
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
