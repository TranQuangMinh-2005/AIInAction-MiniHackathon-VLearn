"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import ReactMarkdown from "react-markdown";

interface CitationDetail {
  label: string;
  title: string;
  source: string;
  page?: number;
  line_start?: number;
  line_end?: number;
  quote: string;
  url?: string;
}

interface Paper {
  source: string;
  title: string;
  page_count: number;
}

interface Message {
  id: string;
  role: "tutor" | "user";
  content: string;
  context?: string;
  citations?: string[];
  citationDetails?: CitationDetail[];
}

interface ChatPanelProps {
  activeDocId: string;
  currentPage: number;
  isOpen: boolean;
  onToggle: () => void;
  onJumpToDocPage?: (docId: string, page: number) => void;
  selectionText?: string;
  onSelectionConsumed?: () => void;
}

export default function ChatPanel({ activeDocId, currentPage, isOpen, onToggle, onJumpToDocPage, selectionText, onSelectionConsumed }: ChatPanelProps) {
  const agentApiUrl = "/backend";
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "tutor",
      content:
        "Xin chào! Mình là VLearn Tutor. Bạn có thể bôi đen một đoạn trên slide để hỏi hoặc gửi câu hỏi tự do nhé!",
    },
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [researchMode, setResearchMode] = useState(false);
  const [papers, setPapers] = useState<Paper[]>([]);
  const [selectedPaper, setSelectedPaper] = useState("");
  const [arxivQuery, setArxivQuery] = useState("");
  const [isImporting, setIsImporting] = useState(false);
  const [paperError, setPaperError] = useState("");
  const chatEndRef = useRef<HTMLDivElement>(null);
  const sendingRef = useRef(false);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (!selectionText) return;

    const timer = window.setTimeout(() => {
      setInput(`Giải thích: "${selectionText}"`);
      onSelectionConsumed?.();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [selectionText, onSelectionConsumed]);

  const loadPapers = useCallback(async () => {
    const response = await fetch(`${agentApiUrl}/api/papers`);
    if (!response.ok) throw new Error("Không tải được danh sách paper.");
    const data = await response.json();
    const nextPapers: Paper[] = data.papers || [];
    setPapers(nextPapers);
    setSelectedPaper((current) => {
      if (nextPapers.some((paper) => paper.source === current)) {
        return current;
      }
      return "";
    });
  }, [agentApiUrl]);

  useEffect(() => {
    if (!researchMode) return;
    const timer = window.setTimeout(() => {
      loadPapers().catch(() => {
        setPaperError("Không kết nối được kho paper.");
      });
    }, 0);
    return () => window.clearTimeout(timer);
  }, [researchMode, loadPapers]);

  const handleImportArxiv = async () => {
    const query = arxivQuery.trim();
    if (!query || isImporting) return;
    setIsImporting(true);
    setPaperError("");
    try {
      const response = await fetch(`${agentApiUrl}/api/papers/import-arxiv`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Không thể import paper từ arXiv.");
      }
      await loadPapers();
      if (data.paper?.source) setSelectedPaper(data.paper.source);
      setArxivQuery("");
      setMessages((previous) => [
        ...previous,
        {
          id: `import-${Date.now()}`,
          role: "tutor",
          content:
            `✅ Đã tải và index **${data.paper?.title || data.arxiv?.title}**. ` +
            "Paper này đang được chọn để focus. Bạn có thể chuyển lại chế độ tự động bất cứ lúc nào.",
        },
      ]);
    } catch (error) {
      setPaperError(
        error instanceof Error ? error.message : "Import paper thất bại."
      );
    } finally {
      setIsImporting(false);
    }
  };

  const handleSend = async () => {
    if (sendingRef.current) return;
    const trimmed = input.trim();
    if (!trimmed) return;
    sendingRef.current = true;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: trimmed,
    };

    const aiMsgId = (Date.now() + 1).toString();
    const aiMsg: Message = {
      id: aiMsgId,
      role: "tutor",
      content: "",
      citations: [],
      citationDetails: [],
    };

    setMessages((prev) => [...prev, userMsg, aiMsg]);
    setInput("");
    setIsTyping(true);

    try {
      const res = await fetch(`${agentApiUrl}/api/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: trimmed,
          active_doc_id: activeDocId,
          current_page: currentPage,
          mode: researchMode ? "research" : "normal",
          paper_source: researchMode ? selectedPaper : null,
          history: messages.slice(-5).map((m) => ({
            role: m.role === "tutor" ? "assistant" : "user",
            content: m.content.slice(0, 150),
          })),
        }),
      });
      if (!res.ok) {
        throw new Error(`AI server returned HTTP ${res.status}`);
      }

      const reader = res.body?.getReader();
      if (!reader) throw new Error("No reader");

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const data = JSON.parse(line.slice(6));
            if (data.token) {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === aiMsgId
                    ? { ...m, content: m.content + data.token }
                    : m
                )
              );
            }
            if (data.done) {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === aiMsgId
                    ? {
                        ...m,
                        citations: data.citations || [],
                        citationDetails: data.citation_details || [],
                      }
                    : m
                )
              );
            }
            if (data.error) {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === aiMsgId
                    ? { ...m, content: data.error }
                    : m
                )
              );
            }
          } catch {}
        }
      }
    } catch {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === aiMsgId && !m.content
            ? { ...m, content: "Không thể kết nối đến AI server. Vui lòng thử lại." }
            : m
        )
      );
    } finally {
      setIsTyping(false);
      sendingRef.current = false;
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleClearChat = () => {
    setMessages([
      {
        id: "welcome",
        role: "tutor",
        content: "Xin chào! Mình là VLearn Tutor. Bạn có thể bôi đen một đoạn trên slide để hỏi hoặc gửi câu hỏi tự do nhé!",
      },
    ]);
  };

  const handleCitationClick = (citation: string) => {
    const match = citation.match(/(D\d)\s*[-–]\s*Trang\s+(\d+)/i);
    if (!match) return;

    const docId = match[1].toLowerCase();
    const pageNum = parseInt(match[2], 10);

    if (docId !== activeDocId && onJumpToDocPage) {
      onJumpToDocPage(docId, pageNum);
      return;
    }

    const el = document.getElementById(`${activeDocId}-page-${pageNum}`);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  return (
    <>
      {/* Toggle button — always visible on right edge */}
      {!isOpen && (
        <button
          onClick={onToggle}
          className="fixed right-0 top-1/2 -translate-y-1/2 z-20 w-10 h-24 bg-[#134D8B] text-white rounded-l-xl shadow-lg flex flex-col items-center justify-center gap-1 hover:bg-[#0d3b6e] hover:w-11 transition-all group"
          title="Mở trợ lý AI"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
          <span className="text-[10px] font-medium leading-tight text-center opacity-80 group-hover:opacity-100">AI</span>
        </button>
      )}

      {/* Chat panel — slides in from right */}
      <div
        className={`fixed right-0 top-12 bottom-0 z-20 w-96 bg-white border-l border-slate-200 flex flex-col shadow-xl transition-transform duration-300
          ${isOpen ? "translate-x-0" : "translate-x-full"}`}
      >
        {/* Chat header */}
        <div className="px-4 py-3 border-b border-slate-200 flex items-center justify-between shrink-0">
          <div>
            <h3 className="text-sm font-semibold text-slate-700">Trợ lý học theo ngữ cảnh</h3>
            <p className="text-xs text-slate-400 mt-0.5">
              {researchMode
                ? "Mở rộng kiến thức bằng paper từ arXiv"
                : `Ngữ cảnh: Slide trang ${currentPage}`}
            </p>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={handleClearChat}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
              title="Xoá hội thoại"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 6h18M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
              </svg>
            </button>
            <button
              onClick={onToggle}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
              title="Đóng"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M18 6 6 18M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Explicit mode selector */}
        <div className="px-3 py-2 border-b border-slate-200 bg-slate-50 shrink-0">
          <div className="grid grid-cols-2 gap-1 rounded-lg bg-slate-200 p-1">
            <button
              type="button"
              onClick={() => {
                setResearchMode(false);
                setPaperError("");
              }}
              className={`rounded-md px-3 py-1.5 text-xs font-semibold transition-all ${
                !researchMode
                  ? "bg-white text-[#134D8B] shadow-sm"
                  : "text-slate-500 hover:text-slate-700"
              }`}
            >
              📖 Normal
            </button>
            <button
              type="button"
              onClick={() => setResearchMode(true)}
              className={`rounded-md px-3 py-1.5 text-xs font-semibold transition-all ${
                researchMode
                  ? "bg-amber-500 text-white shadow-sm"
                  : "text-slate-500 hover:text-slate-700"
              }`}
            >
              🔬 Research
            </button>
          </div>

          {researchMode && (
            <div className="mt-2 space-y-2 rounded-lg border border-amber-200 bg-amber-50 p-2">
              <label className="block text-[11px] font-semibold text-amber-900">
                Nguồn Research (không bắt buộc)
              </label>
              <select
                value={selectedPaper}
                onChange={(event) => {
                  setSelectedPaper(event.target.value);
                  setPaperError("");
                }}
                className="w-full rounded-md border border-amber-200 bg-white px-2 py-1.5 text-xs text-slate-700 outline-none focus:border-amber-500"
              >
                <option value="">
                  Tự động tìm paper phù hợp trên arXiv
                </option>
                {papers.map((paper) => (
                  <option key={paper.source} value={paper.source}>
                    {paper.title} ({paper.page_count} trang)
                  </option>
                ))}
              </select>

              <div className="flex gap-1">
                <input
                  value={arxivQuery}
                  onChange={(event) => setArxivQuery(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      event.preventDefault();
                      handleImportArxiv();
                    }
                  }}
                  placeholder="Tìm và thêm 1 paper từ arXiv"
                  className="min-w-0 flex-1 rounded-md border border-amber-200 bg-white px-2 py-1.5 text-xs outline-none focus:border-amber-500"
                />
                <button
                  type="button"
                  onClick={handleImportArxiv}
                  disabled={!arxivQuery.trim() || isImporting}
                  className="rounded-md bg-amber-500 px-2.5 py-1.5 text-xs font-semibold text-white hover:bg-amber-600 disabled:opacity-50"
                >
                  {isImporting ? "Đang index…" : "Thêm"}
                </button>
              </div>
              {paperError && (
                <p className="text-[11px] text-red-600">{paperError}</p>
              )}
            </div>
          )}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto custom-scrollbar px-4 py-3 space-y-3">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] rounded-xl px-3.5 py-2.5 text-sm leading-relaxed
                  ${msg.role === "tutor"
                    ? "bg-slate-100 text-slate-700 rounded-tl-sm"
                    : "bg-[#134D8B] text-white rounded-tr-sm"
                  }`}
              >
                {msg.context && (
                  <div className="text-xs opacity-60 mb-1">Ngữ cảnh: {msg.context}</div>
                )}
                {msg.role === "tutor" ? (
                  <div>
                    <div className="prose prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-li:my-0.5 prose-headings:my-2 prose-strong:text-slate-800 prose-a:text-[#134D8B] prose-a:underline">
                      <ReactMarkdown
                        components={{
                          a: ({ href, children }) => (
                            <a href={href} target="_blank" rel="noopener noreferrer">
                              {children}
                            </a>
                          ),
                        }}
                      >
                        {msg.content}
                      </ReactMarkdown>
                    </div>
                    {msg.citationDetails && msg.citationDetails.length > 0 && (
                      <div className="mt-2 space-y-1.5 border-t border-slate-200 pt-2">
                        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                          Bằng chứng trong paper
                        </p>
                        {msg.citationDetails.map((citation) => (
                          <details
                            key={citation.label}
                            className="rounded-md border border-slate-200 bg-white text-xs"
                          >
                            <summary className="cursor-pointer px-2 py-1.5 font-medium text-[#134D8B]">
                              [{citation.label}] {citation.source}
                              {citation.page
                                ? ` · Trang ${citation.page}, dòng ${citation.line_start}-${citation.line_end}`
                                : ""}
                            </summary>
                            <div className="border-t border-slate-100 px-2 py-2">
                              <p className="mb-1 text-[11px] font-medium text-slate-500">
                                Trích nguyên văn:
                              </p>
                              <blockquote className="border-l-2 border-amber-400 pl-2 text-[11px] leading-relaxed text-slate-600">
                                “{citation.quote}”
                              </blockquote>
                              {citation.url && (
                                <a
                                  href={citation.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="mt-1 inline-block text-[#134D8B] underline"
                                >
                                  Mở nguồn
                                </a>
                              )}
                            </div>
                          </details>
                        ))}
                      </div>
                    )}
                    {(!msg.citationDetails ||
                      msg.citationDetails.length === 0) &&
                      msg.citations &&
                      msg.citations.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-slate-200">
                        <div className="flex items-center gap-1 text-xs text-slate-400">
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
                          </svg>
                          {msg.citations
                            .filter((c) => c !== "Web search" && !c.startsWith("http"))
                            .map((c, i) => {
                              const url = c.match(/https?:\/\/\S+$/)?.[0];
                              if (url) {
                                return (
                                  <a
                                    key={i}
                                    href={url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="bg-slate-200 hover:bg-[#134D8B] hover:text-white px-1.5 py-0.5 rounded text-slate-600 transition-colors text-xs"
                                    title="Mở nguồn arXiv"
                                  >
                                    🔗 {c.replace(/\s*-\s*https?:\/\/\S+$/, "")}
                                  </a>
                                );
                              }

                              const isSlide = /^D\d+\s*[-–]\s*Trang\s+\d+/i.test(c);
                              if (isSlide) {
                                return (
                                  <button
                                    key={i}
                                    onClick={() => handleCitationClick(c)}
                                    className="bg-slate-200 hover:bg-[#134D8B] hover:text-white px-1.5 py-0.5 rounded text-slate-600 transition-colors cursor-pointer text-xs"
                                    title="Nhấn để chuyển đến trang slide"
                                  >
                                    📄 {c}
                                  </button>
                                );
                              }

                              return (
                                <span
                                  key={i}
                                  className="bg-slate-200 px-1.5 py-0.5 rounded text-slate-600 text-xs"
                                  title="Nguồn PDF đã index"
                                >
                                  📄 {c}
                                </span>
                              );
                            })}
                        </div>
                      </div>
                      )}
                  </div>
                ) : (
                  <p>{msg.content}</p>
                )}
              </div>
            </div>
          ))}

          {isTyping && (
            <div className="flex justify-start">
              <div className="bg-slate-100 rounded-xl rounded-tl-sm px-4 py-3">
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                  <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                  <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                </div>
              </div>
            </div>
          )}

          <div ref={chatEndRef} />
        </div>

        {/* Input area */}
        <div className="p-3 border-t border-slate-200 shrink-0">
          <div className="flex items-end gap-2 bg-slate-50 rounded-xl border border-slate-200 focus-within:border-[#134D8B] focus-within:ring-2 focus-within:ring-[#134D8B]/10 transition-all">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                researchMode
                  ? "Hỏi sâu hơn — Research sẽ tìm paper..."
                  : "Nhập câu hỏi về slide..."
              }
              rows={1}
              className="flex-1 bg-transparent px-3 py-2.5 text-sm resize-none outline-none placeholder:text-slate-400 max-h-32"
              style={{ minHeight: "40px" }}
            />
            <button
              type="button"
              onClick={handleSend}
              disabled={!input.trim()}
              className="p-2 m-1 rounded-lg bg-[#134D8B] text-white hover:bg-[#0d3b6e] transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
