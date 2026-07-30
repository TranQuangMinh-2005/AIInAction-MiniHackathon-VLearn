"use client";

import { useState, useRef, useEffect } from "react";

interface Message {
  id: string;
  role: "tutor" | "user";
  content: string;
  context?: string;
}

interface ChatPanelProps {
  activeDocId: string;
  currentPage: number;
  isOpen: boolean;
  onToggle: () => void;
}

export default function ChatPanel({ activeDocId, currentPage, isOpen, onToggle }: ChatPanelProps) {
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
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: trimmed,
      context: `Slide trang ${currentPage}`,
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsTyping(true);

    setTimeout(() => {
      const responses = [
        "Đây là câu trả lời mẫu từ VLearn Tutor. Trong bản hoàn chỉnh, AI sẽ trả lời dựa trên nội dung slide và ngữ cảnh hiện tại.",
        "Rất tiếc, hiện tại tôi chưa có đủ thông tin để trả lời câu hỏi này. Bạn có thể thử hỏi một câu khác hoặc bôi đen đoạn văn bản cụ thể trên slide.",
        "Dựa trên nội dung slide, đây là giải thích cho câu hỏi của bạn. Bạn có muốn tôi giải thích sâu hơn không?",
      ];
      const random = responses[Math.floor(Math.random() * responses.length)];

      const aiMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "tutor",
        content: random,
      };
      setMessages((prev) => [...prev, aiMsg]);
      setIsTyping(false);
    }, 1000);
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
              Ngữ cảnh: Slide trang {currentPage}
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
                <p>{msg.content}</p>
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
              placeholder="Nhập câu hỏi của bạn..."
              rows={1}
              className="flex-1 bg-transparent px-3 py-2.5 text-sm resize-none outline-none placeholder:text-slate-400 max-h-32"
              style={{ minHeight: "40px" }}
            />
            <button
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
