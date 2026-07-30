"use client";

import { useState } from "react";
import Sidebar from "@/components/Sidebar";
import SlideViewer from "@/components/SlideViewer";
import ChatPanel from "@/components/ChatPanel";

export default function Home() {
  const [activeDocId, setActiveDocId] = useState("d1");
  const [pdfPath, setPdfPath] = useState("/d1-slide-hackathon.pdf");
  const [totalPages, setTotalPages] = useState(29);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);

  const handleSelectDoc = (docId: string, _title: string, path: string, pages: number) => {
    setActiveDocId(docId);
    setPdfPath(path);
    setTotalPages(pages);
    setCurrentPage(1);
  };

  return (
    <div className="h-full flex flex-col">
      {/* Top bar */}
      <header className="h-12 bg-[#134D8B] text-white flex items-center px-4 shrink-0 z-10">
        <button
          onClick={() => window.history.back()}
          className="flex items-center gap-1 text-sm text-white/80 hover:text-white transition-colors mr-4"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="m15 18-6-6 6-6" />
          </svg>
          Quay lại
        </button>
        <div className="flex items-center gap-2">
          <svg width="22" height="22" viewBox="0 0 38 38" fill="none">
            <rect width="38" height="38" rx="8" fill="white" />
            <text x="9" y="26" fill="#134D8B" fontSize="18" fontWeight="900">V</text>
          </svg>
          <span className="text-sm font-semibold">COMP2010 — AI Thực Chiến</span>
        </div>
        <div className="flex-1" />
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="p-1.5 rounded-lg text-white/70 hover:text-white hover:bg-white/10 transition-colors"
          title="Mở sidebar"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M3 12h18M3 6h18M3 18h18" />
          </svg>
        </button>
      </header>

      {/* Main 3-panel layout */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Sidebar toggle button — left edge, matches chat toggle style */}
        {!sidebarOpen && (
          <button
            onClick={() => setSidebarOpen(true)}
            className="absolute left-0 top-1/2 -translate-y-1/2 z-20 w-10 h-24 bg-[#134D8B] text-white rounded-r-xl shadow-lg flex flex-col items-center justify-center gap-1 hover:bg-[#0d3b6e] hover:w-11 transition-all group"
            title="Mở danh sách slide"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
              <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
            </svg>
            <span className="text-[10px] font-medium leading-tight text-center opacity-80 group-hover:opacity-100">Slide</span>
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
          sidebarOpen={sidebarOpen}
          onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
          currentPage={currentPage}
          onPageChange={setCurrentPage}
        />
        <div className="hidden xl:block">
          <ChatPanel 
            activeDocId={activeDocId} 
            currentPage={currentPage} 
            isOpen={chatOpen}
            onToggle={() => setChatOpen(!chatOpen)}
          />
        </div>
      </div>
    </div>
  );
}
