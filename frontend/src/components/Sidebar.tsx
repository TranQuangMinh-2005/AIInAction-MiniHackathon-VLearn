"use client";

import { useState } from "react";

interface SlideDoc {
  id: string;
  title: string;
  code: string;
  pdfPath: string;
  pages: number;
}

const slideDocuments: SlideDoc[] = [
  {
    id: "d1",
    title: "Day 1 — AI & LLM Foundation",
    code: "D01",
    pdfPath: "/d1-slide-hackathon.pdf",
    pages: 29,
  },
  {
    id: "d2",
    title: "Day 2 — Xác định bài toán cho AI",
    code: "D02",
    pdfPath: "/d2-slide-hackathon.pdf",
    pages: 29,
  },
];

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
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/30 z-20"
          onClick={onToggle}
        />
      )}

      <aside
        className={`fixed lg:relative z-30 h-full w-80 bg-white border-r border-slate-200 flex flex-col shrink-0 transition-transform duration-300 overflow-hidden
          ${isOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0 lg:w-0 lg:border-0"}`}
      >
        <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between shrink-0">
          <div>
            <h2 className="text-sm font-semibold text-slate-800">Học liệu môn học</h2>
            <p className="text-xs text-slate-500 mt-0.5">Slide bài giảng hackathon</p>
          </div>
          <button
            onClick={onToggle}
            className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto custom-scrollbar">
          <div className="border-b border-slate-100">
            <button
              onClick={() => setExpanded(!expanded)}
              className="w-full px-5 py-3 flex items-center justify-between hover:bg-slate-50 transition-colors text-left"
            >
              <div className="flex-1 min-w-0">
                <h3 className="text-sm font-medium text-slate-700 truncate">
                  AI Thực Chiến — Hackathon
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  {slideDocuments.length} tài liệu
                </p>
              </div>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                className={`text-slate-400 transition-transform ${expanded ? "rotate-90" : ""}`}>
                <path d="m9 18 6-6-6-6" />
              </svg>
            </button>

            {expanded && (
              <div className="pb-1">
                {slideDocuments.map((doc) => (
                  <button
                    key={doc.id}
                    onClick={() => onSelectDoc(doc.id, doc.title, doc.pdfPath, doc.pages)}
                    className={`w-full px-5 pl-10 py-2.5 flex items-center gap-3 text-left transition-colors
                      ${activeDocId === doc.id
                        ? "bg-[#134D8B]/10 text-[#134D8B] border-r-2 border-[#134D8B]"
                        : "text-slate-600 hover:bg-slate-50"
                      }`}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="shrink-0">
                      <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
                      <polyline points="14 2 14 8 20 8" />
                    </svg>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm truncate">{doc.title}</p>
                      <p className="text-xs text-slate-400">{doc.code} · {doc.pages} trang</p>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </aside>
    </>
  );
}
