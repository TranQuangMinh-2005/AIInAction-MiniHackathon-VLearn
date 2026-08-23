"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import {
  ArrowSquareOut,
  BookOpen,
  CaretDown,
  CaretRight,
  CheckCircle,
  CircleNotch,
  FileText,
  Flask,
  PaperPlaneTilt,
  Robot,
  Sparkle,
  Stop,
  ThumbsDown,
  ThumbsUp,
  Trash,
  WarningCircle,
  X,
} from "@phosphor-icons/react";

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
  /* A-05 envelope từ backend (optional) */
  move?: string;
  misconceptions?: string[];
  followUps?: string[];
  askedCheckQuestion?: boolean;
  /* A-07 trace cho rating feedback */
  traceId?: string;
}

interface ChatPanelProps {
  activeDocId: string;
  currentPage: number;
  isOpen: boolean;
  onToggle: () => void;
  onJumpToDocPage?: (docId: string, page: number) => void;
  /* t28 — paper citation [S1] nhảy tới trang trong PDF paper */
  onOpenPaper?: (source: string, page: number) => void;
  selectionText?: string;
  onSelectionConsumed?: () => void;
  /* Đồng bộ trạng thái đang trả lời lên top bar (dot báo) — DESIGN.md §5.1 */
  onTypingChange?: (typing: boolean) => void;
}

const WELCOME_TEXT =
  "Xin chào! Mình là VLearn Tutor. Bạn có thể bôi đen một đoạn trên slide để hỏi hoặc gửi câu hỏi tự do nhé!";

/**
 * P0-1 (Scheme B — PO2 chốt) — decode nhãn citation slide → (doc_id, trang).
 * Mới: "D1 Full"/"D2 Full" = bản full Day1/Day2 (d3/d4) — phân biệt với short
 * d1/d2 "D1"/"D2". Nhận cả "D1-F" (scheme tạm lượt trước, backfill).
 * Legacy: "D3".."D16" theo doc_id (vẫn hiểu citation cũ), "DAY05-REF" → day05-ref.
 */
const CITATION_FULL_RE = /^(D[12](?:-F|\s*Full))\s*[-–]\s*Trang\s+(\d+)/i;
const CITATION_LEGACY_RE = /^(DAY05-REF|D\d{1,2})\s*[-–]\s*Trang\s+(\d+)/i;

function decodeCitationDoc(
  citation: string
): { docId: string; pageNum: number } | null {
  let match = citation.match(CITATION_FULL_RE);
  if (match) {
    return {
      docId: match[1].toLowerCase().startsWith("d1") ? "d3" : "d4",
      pageNum: parseInt(match[2], 10),
    };
  }
  match = citation.match(CITATION_LEGACY_RE);
  if (!match) return null;
  const raw = match[1].toLowerCase();
  const docId = raw === "day05-ref" ? "day05-ref" : raw;
  return { docId, pageNum: parseInt(match[2], 10) };
}

/**
 * t39 — linkify citations TRONG text markdown (giữ nguyên text hiển thị):
 * [D1 - Trang 4] · [D1 Full - Trang 6] · [arxiv-x.pdf - Trang N] · [S1] · [Trang X]
 * → markdown link vlearn://cite/<kind>?c=<encoded>; `a` renderer bắt scheme nhảy nguồn.
 * Markdown khác (bold/ul/code/link http) GIỮ NGUYÊN — chỉ thay đúng bracket citation.
 */
const CITE_SLIDE_RE = /\[((?:D[12](?:-F|\s*Full)|D\d{1,2}|DAY05-REF)\s*[-–]\s*Trang\s+\d+)\]/gi;
const CITE_PAPER_RE = /\[(arxiv-[A-Za-z0-9._-]+\.pdf[^\]]*)\]/gi;
const CITE_SLABEL_RE = /\[([Ss]\d+)\]/g;
const CITE_CURRENT_RE = /\[(Trang\s+\d+)\]/gi;

function linkifyCitations(text: string): string {
  return text
    .replace(CITE_SLIDE_RE, (_m, cite) => `[${cite}](vlearn://cite/slide?c=${encodeURIComponent(cite)})`)
    .replace(CITE_PAPER_RE, (_m, cite) => `[${cite}](vlearn://cite/paper?c=${encodeURIComponent(cite)})`)
    .replace(CITE_SLABEL_RE, (_m, cite) => `[${cite}](vlearn://cite/slabel?c=${encodeURIComponent(cite)})`)
    .replace(CITE_CURRENT_RE, (_m, cite) => `[${cite}](vlearn://cite/current?c=${encodeURIComponent(cite)})`);
}

function parseCiteHref(
  href: string
): { kind: string; cite: string } | null {
  if (!href.startsWith("vlearn://cite/")) return null;
  const rest = href.slice("vlearn://cite/".length);
  const [kind, query] = rest.split("?", 2);
  const params = new URLSearchParams(query ?? "");
  return { kind, cite: params.get("c") ?? "" };
}

/* t30 — follow-up chip: backend gửi CÂU HỎI của tutor ("Bạn có muốn mình … không?"),
   click chip phải điền PROMPT HÀNH ĐỘNG thật của học viên, không nhét câu hỏi tutor
   vào composer. Mapper thuần frontend — backend giữ nguyên. */
const toActionPrompt = (followUp: string): string => {
  const text = followUp
    .replace(/\*\*(.+?)\*\*/g, "$1") /* bỏ markdown bold (vd **ReAct pattern**) */
    .replace(/\s+/g, " ")
    .trim();
  const base = text.replace(/[?!.。]+$/, "").trim();
  const lower = base.toLowerCase();
  const cap = (s: string) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : s);

  /* 1) Mời hỏi chung — server.py fallback */
  if (lower.startsWith("bạn muốn hỏi gì về slide")) {
    return "Giải thích nội dung slide đang xem";
  }
  /* 2) "Bạn muốn mình đào sâu hơn về X không?" → "Đào sâu hơn về X" */
  const deep = base.match(/đào sâu hơn về (.+?)( không)?$/i);
  if (deep && deep[1]) return `Đào sâu hơn về ${deep[1]}`;
  /* 3) "...hay nhắc lại ngắn gọn?" → yêu cầu nhắc lại */
  if (/nhắc lại ngắn gọn/i.test(base)) return "Nhắc lại ngắn gọn chủ đề này";
  /* 4) "...ví dụ thực tế hoặc câu hỏi ôn tập về phần này không?" → yêu cầu ví dụ/ôn tập */
  const example = base.match(/cho ví dụ thực tế hoặc câu hỏi ôn tập về (.+?)( không)?$/i);
  if (example && example[1]) {
    return `Cho mình ví dụ thực tế hoặc câu hỏi ôn tập về ${example[1]}`;
  }
  /* 5) "Bạn có định hỏi **ReAct pattern** trong slide … nhé?" → yêu cầu giải thích khái niệm */
  const react = base.match(/bạn có định hỏi (.+?) trong slide/i);
  if (react && react[1]) return `Giải thích ${react[1]}`;
  /* 6) Check-question LLM: "Bạn có thể … không?" → mệnh lệnh học viên */
  const can = base.match(/bạn có thể (.+?)( không)?$/i);
  if (can && can[1]) return cap(can[1]);
  /* 7) "Theo bạn, vì sao …?" → câu hỏi thật của học viên (giữ dấu ? nếu có) */
  const theo = base.match(/theo bạn,?\s*(.+)/i);
  if (theo && theo[1]) return cap(theo[1]) + (/[?？]$/.test(text) ? "?" : "");
  /* 8) "Bạn có muốn [mình] …?" → "Mình muốn …" */
  const want = base.match(/bạn có muốn (.+?)( không)?$/i);
  if (want && want[1]) {
    return `Mình muốn ${cap(want[1].replace(/^mình\s+/i, ""))}`;
  }
  /* 9) "Bạn hãy …" → "Hãy …" */
  const hay = base.match(/bạn hãy (.+)/i);
  if (hay && hay[1]) return `Hãy ${cap(hay[1])}`;
  /* 10) Fallback: bỏ " không" cuối (yes/no → yêu cầu) */
  if (lower.endsWith(" không")) {
    const trimmed = base.slice(0, -" không".length).trim();
    if (trimmed) return cap(trimmed);
  }
  return base || text;
};

/* t35 — misconceptions: ghi chú của tutor (dạng statement) → prompt hành động học viên */
const miscActionPrompt = (items: string[]): string =>
  items.length > 0
    ? `Giải thích lại để mình hiểu đúng: ${items.join("; ")}`
    : "Giải thích lại khái niệm này";

export default function ChatPanel({ activeDocId, currentPage, isOpen, onToggle, onJumpToDocPage, onOpenPaper, selectionText, onSelectionConsumed, onTypingChange }: ChatPanelProps) {
  const agentApiUrl =
    process.env.NEXT_PUBLIC_AGENT_API_URL || "";
  const [messages, setMessages] = useState<Message[]>([
    { id: "welcome", role: "tutor", content: WELCOME_TEXT },
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [elapsedSec, setElapsedSec] = useState(0);
  const [researchMode, setResearchMode] = useState(false);
  const [papers, setPapers] = useState<Paper[]>([]);
  const [papersLoading, setPapersLoading] = useState(false);
  const [selectedPaper, setSelectedPaper] = useState("");
  const [arxivQuery, setArxivQuery] = useState("");
  const [isImporting, setIsImporting] = useState(false);
  const [paperError, setPaperError] = useState("");
  const [chatError, setChatError] = useState("");
  const [toast, setToast] = useState<string | null>(null);
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  /* A-04 — phase thật từ backend (status event SSE); null = server cũ → fallback đồng hồ */
  const [statusPhase, setStatusPhase] = useState<string | null>(null);
  /* A-06 — learner_id ẩn danh per-browser (localStorage, không PII) */
  const [learnerId] = useState<string>(() => {
    if (typeof window === "undefined") return "";
    try {
      let id = window.localStorage.getItem("vlearn-learner-id");
      if (!id) {
        id =
          (window.crypto?.randomUUID?.() ??
            `anon-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`);
        window.localStorage.setItem("vlearn-learner-id", id);
      }
      return id;
    } catch {
      return "";
    }
  });
  /* A-07 — đã rating cho từng message (1 👍 / -1 👎) */
  const [ratedFeedback, setRatedFeedback] = useState<Record<string, number>>({});
  /* t35 — misconceptions đã dismiss theo message (ẩn card, không hiện lại) */
  const [dismissedMisc, setDismissedMisc] = useState<Record<string, boolean>>({});

  const chatEndRef = useRef<HTMLDivElement>(null);
  const composerRef = useRef<HTMLTextAreaElement>(null);
  const sendingRef = useRef(false);
  const abortRef = useRef<AbortController | null>(null);
  const stopRequestedRef = useRef(false);
  const lastQuestionRef = useRef<string>("");
  const typingStartedAtRef = useRef(0);
  const clearRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  useEffect(() => {
    onTypingChange?.(isTyping);
  }, [isTyping, onTypingChange]);

  useEffect(() => {
    if (!selectionText) return;

    const timer = window.setTimeout(() => {
      setInput(`Giải thích: "${selectionText}"`);
      onSelectionConsumed?.();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [selectionText, onSelectionConsumed]);

  /* F4 — đồng hồ giây khi chờ stream */
  useEffect(() => {
    if (!isTyping) {
      setElapsedSec(0);
      return;
    }
    typingStartedAtRef.current = Date.now();
    const timer = window.setInterval(() => {
      setElapsedSec(Math.floor((Date.now() - typingStartedAtRef.current) / 1000));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [isTyping]);

  /* Toast auto-hide 3s */
  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 3000);
    return () => window.clearTimeout(timer);
  }, [toast]);

  /* Confirm popover — đóng khi click ngoài */
  useEffect(() => {
    if (!showClearConfirm) return;
    const onDown = (e: MouseEvent) => {
      if (clearRef.current && !clearRef.current.contains(e.target as Node)) {
        setShowClearConfirm(false);
      }
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [showClearConfirm]);

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
      setPapersLoading(true);
      loadPapers()
        .catch(() => {
          setPaperError("Không kết nối được kho paper.");
        })
        .finally(() => setPapersLoading(false));
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
      setToast("Đã thêm paper · chọn làm focus");
    } catch (error) {
      setPaperError(
        error instanceof Error ? error.message : "Import paper thất bại."
      );
    } finally {
      setIsImporting(false);
    }
  };

  /* Gửi câu hỏi — logic stream giữ nguyên; thêm AbortController cho nút Dừng (F8) */
  const handleSend = async (preset?: string) => {
    if (sendingRef.current) return;
    const trimmed = (preset ?? input).trim();
    if (!trimmed) return;
    sendingRef.current = true;
    lastQuestionRef.current = trimmed;
    setChatError("");

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
    setStatusPhase(null);
    stopRequestedRef.current = false;
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const res = await fetch(`${agentApiUrl}/api/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: controller.signal,
        body: JSON.stringify({
          question: trimmed,
          active_doc_id: activeDocId,
          current_page: currentPage,
          mode: researchMode ? "research" : "normal",
          paper_source: researchMode ? selectedPaper : null,
          history: messages.slice(-5).map((m) => ({
            role: m.role === "tutor" ? "assistant" : "user",
            content: m.content.slice(0, 150),
            /* t27 — giữ nguồn paper/citation trong history để follow-up
               "tóm tắt paper này" sau Research tóm tắt ĐÚNG paper */
            ...(m.role === "tutor"
              ? {
                  sources:
                    m.citationDetails
                      ?.map((d) => d.source)
                      .filter(Boolean)
                      .slice(0, 3) ?? [],
                  citations: (m.citations ?? []).slice(0, 5),
                }
              : {}),
          })),
          /* A-06 — learner_id ẩn danh per-browser (localStorage) */
          learner_id: learnerId,
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
            if (data.status) {
              /* A-04 — status event thật từ backend (backward-compat: server cũ không gửi) */
              setStatusPhase(data.status as string);
            }
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
                        /* A-05 envelope (optional — backend cũ không gửi) */
                        move: data.move,
                        misconceptions: data.misconceptions || [],
                        followUps: data.follow_ups || [],
                        askedCheckQuestion: data.asked_check_question,
                        /* A-07 trace id cho rating */
                        traceId: data.trace_id,
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
      if (stopRequestedRef.current) {
        /* Dừng chủ động — giữ phần đã stream */
      } else {
        setChatError("Không thể kết nối đến AI server. Vui lòng thử lại.");
        setMessages((prev) =>
          prev.filter((m) => !(m.id === aiMsgId && !m.content))
        );
      }
    } finally {
      setIsTyping(false);
      sendingRef.current = false;
      abortRef.current = null;
    }
  };

  /* Nút Dừng khi đang stream (F8) */
  const handleStop = () => {
    stopRequestedRef.current = true;
    abortRef.current?.abort();
    setIsTyping(false);
    sendingRef.current = false;
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  /* Auto-grow tới 6 dòng (132px) — F8 */
  const handleComposerInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    const el = e.target;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 132)}px`;
  };

  const handleClearChat = () => {
    setMessages([{ id: "welcome", role: "tutor", content: WELCOME_TEXT }]);
    setShowClearConfirm(false);
  };

  /* A-07 — rating 👍👎 gắn trace_id → /api/feedback (1 lần/message) */
  const sendFeedback = async (msg: Message, rating: number) => {
    if (!msg.traceId || ratedFeedback[msg.id]) return;
    try {
      await fetch(`${agentApiUrl}/api/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ trace_id: msg.traceId, rating }),
      });
      setRatedFeedback((prev) => ({ ...prev, [msg.id]: rating }));
      setToast(
        rating === 1
          ? "Cảm ơn phản hồi 👍"
          : "Đã ghi nhận — mình sẽ cải thiện 👎"
      );
    } catch {
      /* lỗi mạng — im lặng, không chặn UX */
    }
  };

  const handleCitationClick = (citation: string) => {
    /* P0-1 — decode nhãn citation: mới "D1-F/D2-F" (full Day1/Day2) + legacy
       "D1..D16" (doc_id-based, vẫn hiểu citation cũ trong history) + DAY05-REF */
    const decoded = decodeCitationDoc(citation);
    if (!decoded) return;

    const { docId, pageNum } = decoded;
    if (docId !== activeDocId && onJumpToDocPage) {
      onJumpToDocPage(docId, pageNum);
      return;
    }

    const el = document.getElementById(`${activeDocId}-page-${pageNum}`);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
      /* Flash highlight 1.2s trang đích */
      el.classList.remove("page-flash");
      void el.offsetWidth; /* reflow để chạy lại animation */
      el.classList.add("page-flash");
      window.setTimeout(() => el.classList.remove("page-flash"), 1300);
    }
  };

  /* t39 — citation inline trong text markdown (vlearn://cite/*) */
  const handleInlineCite = (msg: Message, kind: string, cite: string) => {
    const flashPage = (docId: string, pageNum: number) => {
      if (docId !== activeDocId && onJumpToDocPage) {
        onJumpToDocPage(docId, pageNum);
        return;
      }
      const el = document.getElementById(`${activeDocId}-page-${pageNum}`);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "start" });
        el.classList.remove("page-flash");
        void el.offsetWidth;
        el.classList.add("page-flash");
        window.setTimeout(() => el.classList.remove("page-flash"), 1300);
      }
    };
    if (kind === "slide") {
      const decoded = decodeCitationDoc(cite);
      if (decoded) flashPage(decoded.docId, decoded.pageNum);
      return;
    }
    if (kind === "current") {
      const match = cite.match(/Trang\s+(\d+)/i);
      if (match) flashPage(activeDocId, parseInt(match[1], 10));
      return;
    }
    if (kind === "paper") {
      const match = cite.match(
        /(arxiv-[A-Za-z0-9._-]+\.pdf)\s*[-–,]\s*Trang\s+(\d+)/i
      );
      if (match) {
        onOpenPaper?.(match[1], parseInt(match[2], 10));
        return;
      }
      const src = cite.match(/(arxiv-[A-Za-z0-9._-]+\.pdf)/i);
      if (src) onOpenPaper?.(src[1], 1);
      return;
    }
    if (kind === "slabel") {
      const detail = (msg.citationDetails ?? []).find(
        (d) => (d.label ?? "").toLowerCase() === cite.toLowerCase()
      );
      if (detail?.source && detail.page) onOpenPaper?.(detail.source, detail.page);
    }
  };

  /* A-04 — trạng thái theo status event THẬT từ backend; fallback đồng hồ khi server cũ */
  const STATUS_LABELS: Record<string, string> = {
    routing: "Đang phân tích câu hỏi…",
    searching_slide: "Đang tìm trong slide…",
    summarizing: "Đang tóm tắt tài liệu…",
    rewriting_query: "Đang phân tích câu hỏi…",
    searching_arxiv: "Đang tìm paper trên arXiv…",
    reading_paper: "Đang đọc & kiểm chứng paper…",
    answering: "Đang viết câu trả lời…",
  };
  /* A-05 — nhãn move cho badge envelope */
  const MOVE_LABELS: Record<string, string> = {
    review_concept: "Ôn khái niệm",
    give_example: "Ví dụ thực tế",
    give_hint: "Gợi ý",
    validate: "Xác nhận hiểu",
    explain: "Giải thích",
  };
  const heuristicStatus = researchMode
    ? elapsedSec < 4
      ? "Đang tìm paper trên arXiv…"
      : elapsedSec <= 15
        ? "Đang tải & index paper…"
        : "Đang viết câu trả lời…"
    : "Đang tìm trong slide…";
  const typingStatus = statusPhase
    ? (STATUS_LABELS[statusPhase] ?? "Đang xử lý…")
    : heuristicStatus;

  return (
    <>
      {/* Backdrop — chỉ overlay <xl, fade-in */}
      {isOpen && (
        <div
          className="fixed inset-0 z-20 animate-fade-in bg-brand-950/30 xl:hidden"
          onClick={onToggle}
          aria-hidden="true"
        />
      )}

      {/* Edge toggle pill — luôn hiển thị khi đóng (mọi kích thước) — draft A §5.5 */}
      {!isOpen && (
        <button
          type="button"
          onClick={onToggle}
          aria-label="Mở trợ lý AI"
          aria-expanded="false"
          aria-controls="chat-panel"
          title="Mở trợ lý AI"
          className="fixed right-0 top-1/2 z-20 flex h-20 w-9 -translate-y-1/2 flex-col items-center justify-center gap-1 rounded-l-full border-r border-white/10 bg-brand-600 text-white opacity-85 shadow-md transition-[transform,opacity,background-color] duration-150 ease-quick hover:bg-brand-700 hover:opacity-100 focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2"
        >
          <Sparkle size={18} aria-hidden="true" />
          <span className="text-overline font-bold uppercase leading-none tracking-widest [writing-mode:vertical-rl]">AI</span>
        </button>
      )}

      {/* Chat panel — in-flow ≥xl (w-96) · overlay <xl (slide in from right) */}
      <div
        id="chat-panel"
        role="complementary"
        aria-label="Trợ lý học tập AI"
        className={`fixed bottom-0 right-0 top-12 z-30 flex w-96 shrink-0 flex-col overflow-hidden border-l border-border bg-surface shadow-lg transition-transform duration-[240ms] ease-panel xl:shadow-none
          ${isOpen ? "translate-x-0 xl:relative xl:bottom-auto xl:top-auto" : "translate-x-full xl:absolute xl:bottom-0 xl:right-0 xl:top-0"}`}
      >
        {/* Header — draft A: avatar + context */}
        <div className="flex shrink-0 items-center justify-between p-4">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-600 shadow-sm">
              <Robot size={18} aria-hidden="true" className="text-white" />
            </div>
            <div className="min-w-0">
              <h2 className="truncate text-base font-semibold text-ink-strong">VLearn Tutor</h2>
              <p className="mt-1 text-caption leading-none text-ink-faint">
                {researchMode
                  ? "Research · tự động tìm paper trên arXiv"
                  : `Ngữ cảnh: Slide trang ${currentPage}`}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            {/* Clear chat — confirm nhẹ khi >1 turn */}
            <div className="relative" ref={clearRef}>
              <button
                type="button"
                onClick={() =>
                  messages.length > 1 ? setShowClearConfirm((v) => !v) : handleClearChat()
                }
                aria-label="Xoá hội thoại"
                aria-expanded={showClearConfirm}
                title="Xoá hội thoại"
                className="flex h-8 w-8 items-center justify-center rounded-md text-ink-faint transition-colors duration-150 ease-quick hover:bg-surface-2 hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2"
              >
                <Trash size={16} aria-hidden="true" />
              </button>
              {showClearConfirm && (
                <div className="absolute right-0 top-full z-40 mt-1 w-44 animate-scale-in rounded-lg bg-surface p-2 shadow-md ring-1 ring-brand-950/8">
                  <p className="px-1 pb-1.5 text-body-sm font-medium text-ink-strong">Xoá hội thoại?</p>
                  <div className="flex gap-1">
                    <button
                      type="button"
                      onClick={() => setShowClearConfirm(false)}
                      className="flex-1 rounded-md px-2 py-1.5 text-xs font-semibold text-ink-muted transition-colors duration-150 ease-quick hover:bg-surface-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
                    >
                      Huỷ
                    </button>
                    <button
                      type="button"
                      onClick={handleClearChat}
                      className="flex-1 rounded-md bg-danger px-2 py-1.5 text-xs font-semibold text-white transition-colors duration-150 ease-quick hover:bg-danger/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2"
                    >
                      Xoá
                    </button>
                  </div>
                </div>
              )}
            </div>
            <button
              type="button"
              onClick={onToggle}
              aria-label="Đóng trợ lý AI"
              title="Đóng"
              className="flex h-8 w-8 items-center justify-center rounded-md text-ink-faint transition-colors duration-150 ease-quick hover:bg-surface-2 hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2 xl:hidden"
            >
              <X size={16} aria-hidden="true" />
            </button>
          </div>
        </div>

        {/* Mode selector — segmented đồng ngôn ngữ thị giác (G3: không accent thứ 2) — draft A */}
        <div className="px-4 pb-4">
          <div className="flex rounded-lg bg-surface-2 p-0.5 shadow-xs ring-1 ring-border/50">
            <button
              type="button"
              onClick={() => {
                setResearchMode(false);
                setPaperError("");
              }}
              aria-pressed={!researchMode}
              className={`flex flex-1 items-center justify-center gap-2 rounded-md py-1.5 text-xs font-semibold transition-all duration-150 ease-quick focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400
                ${!researchMode
                  ? "bg-surface text-brand-700 shadow-sm"
                  : "text-ink-muted hover:text-ink"}`}
            >
              <BookOpen size={16} aria-hidden="true" />
              Normal
            </button>
            <button
              type="button"
              onClick={() => setResearchMode(true)}
              aria-pressed={researchMode}
              className={`flex flex-1 items-center justify-center gap-2 rounded-md py-1.5 text-xs font-semibold transition-all duration-150 ease-quick focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400
                ${researchMode
                  ? "bg-surface text-brand-700 shadow-sm"
                  : "text-ink-muted hover:text-ink"}`}
            >
              <Flask size={16} aria-hidden="true" />
              Research
            </button>
          </div>

          {/* Research config — card trung tính (bỏ amber — G3) */}
          {researchMode && (
            <div className="mt-2 space-y-2 rounded-lg bg-surface-2 p-2.5 ring-1 ring-border/50">
              <label className="text-overline block uppercase text-ink-faint">
                Nguồn research · tuỳ chọn
              </label>
              <div className="relative">
                <select
                  value={selectedPaper}
                  onChange={(event) => {
                    setSelectedPaper(event.target.value);
                    setPaperError("");
                  }}
                  disabled={papersLoading}
                  aria-label="Chọn nguồn paper"
                  className="h-9 w-full appearance-none rounded-md border border-border bg-surface pl-2.5 pr-8 text-body-sm text-ink outline-none transition-colors duration-150 ease-quick focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <option value="">
                    {papersLoading ? "Đang tải paper…" : "Tự động tìm paper phù hợp trên arXiv"}
                  </option>
                  {papers.map((paper) => (
                    <option key={paper.source} value={paper.source}>
                      {paper.title} ({paper.page_count} trang)
                    </option>
                  ))}
                  {!papersLoading && papers.length === 0 && (
                    <option value="" disabled>
                      Chưa có paper — nhập chủ đề để thêm
                    </option>
                  )}
                </select>
                <CaretDown
                  size={14}
                  aria-hidden="true"
                  className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-ink-faint"
                />
              </div>

              {/* F9 — control chuẩn h-9, thẳng hàng */}
              <div className="flex gap-1.5">
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
                  aria-label="Chủ đề paper trên arXiv"
                  className="h-9 min-w-0 flex-1 rounded-md border border-border bg-surface px-2.5 text-body-sm text-ink outline-none transition-colors duration-150 ease-quick placeholder:text-ink-faint focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20"
                />
                <button
                  type="button"
                  onClick={handleImportArxiv}
                  disabled={!arxivQuery.trim() || isImporting}
                  className="flex h-9 shrink-0 items-center gap-1.5 rounded-md border border-brand-300 px-3 text-xs font-semibold text-brand-700 transition-colors duration-150 ease-quick hover:bg-brand-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {isImporting ? (
                    <>
                      <CircleNotch size={14} aria-hidden="true" className="animate-spin" />
                      Đang index…
                    </>
                  ) : (
                    "Thêm"
                  )}
                </button>
              </div>
              {paperError && (
                <div className="flex items-center justify-between gap-2">
                  <p className="flex items-center gap-1.5 text-caption text-danger">
                    <WarningCircle size={12} aria-hidden="true" className="shrink-0" />
                    {paperError}
                  </p>
                  <button
                    type="button"
                    onClick={handleImportArxiv}
                    disabled={isImporting}
                    className="shrink-0 rounded-md border border-danger/30 px-2 py-0.5 text-[11px] font-semibold text-danger transition-colors duration-150 ease-quick hover:bg-danger/10 disabled:opacity-40"
                  >
                    Thử lại
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Toast — import thành công (không nhét vào message) */}
        {toast && (
          <div
            role="status"
            className="absolute inset-x-3 top-14 z-30 flex animate-fade-up items-center gap-2 rounded-lg bg-success px-3 py-2 text-xs font-medium text-white shadow-md"
          >
            <CheckCircle size={16} aria-hidden="true" />
            {toast}
          </div>
        )}

        {/* Messages — draft A: card trắng + ring mảnh; gap thoáng */}
        <div className="flex-1 space-y-5 overflow-y-auto px-4 py-2 custom-scrollbar">
          {/* Empty state — suggested chips theo mode/trang (G6) */}
          {messages.length === 1 && (
            <div className="flex flex-col gap-2 pt-2">
              <span className="text-overline mb-1 uppercase tracking-[0.05em] text-ink-faint">
                Gợi ý hỏi
              </span>
              <button
                type="button"
                onClick={() => setInput("Tóm tắt trang này")}
                className="rounded-lg border border-brand-300 bg-surface px-3 py-2 text-left text-xs font-medium text-brand-700 transition-colors duration-150 ease-quick hover:bg-brand-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
              >
                Tóm tắt trang này
              </button>
              <button
                type="button"
                onClick={() => setInput("Giải thích khái niệm chính trang này")}
                className="rounded-lg border border-brand-300 bg-surface px-3 py-2 text-left text-xs font-medium text-brand-700 transition-colors duration-150 ease-quick hover:bg-brand-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
              >
                Giải thích khái niệm chính trang này
              </button>
              <button
                type="button"
                onClick={() =>
                  setInput(
                    researchMode
                      ? "Tìm paper về chủ đề trang này"
                      : "Gợi ý câu hỏi kiểm tra trang này"
                  )
                }
                className="rounded-lg border border-brand-300 bg-surface px-3 py-2 text-left text-xs font-medium text-brand-700 transition-colors duration-150 ease-quick hover:bg-brand-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
              >
                {researchMode
                  ? "Tìm paper về chủ đề trang này"
                  : "Gợi ý câu hỏi kiểm tra trang này"}
              </button>
            </div>
          )}

          {messages.map((msg, mIdx) =>
            msg.role === "user" ? (
              <div key={msg.id} className="flex animate-fade-up justify-end" style={{ animationDelay: `${Math.min(mIdx, 5) * 40}ms` }}>
                <div className="max-w-[88%] rounded-xl rounded-tr-xs bg-brand-600 px-4 py-2.5 text-sm text-white shadow-sm">
                  <p>{msg.content}</p>
                </div>
              </div>
            ) : (
              <div key={msg.id} className="flex animate-fade-up flex-col items-start gap-2" style={{ animationDelay: `${Math.min(mIdx, 5) * 40}ms` }}>
                <div className="max-w-[88%] rounded-xl rounded-tl-xs bg-surface p-3.5 text-sm leading-relaxed text-ink shadow-sm ring-1 ring-brand-950/8">
                  {msg.context && (
                    <div className="mb-1 text-xs opacity-60">Ngữ cảnh: {msg.context}</div>
                  )}
                  <div className="prose prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-li:my-0.5 prose-headings:my-2 prose-strong:text-ink-strong prose-a:text-brand-600 prose-a:underline">
                    <ReactMarkdown
                      components={{
                        a: ({ href, children }) => {
                          /* t39 — citation inline: bắt scheme vlearn://cite/* */
                          const parsed = href ? parseCiteHref(href) : null;
                          if (parsed) {
                            const titles: Record<string, string> = {
                              slide: "Nhấn để đến đúng trang slide",
                              current: "Nhấn để đến trang này",
                              paper: "Nhấn để xem đúng trang của paper",
                              slabel: "Nhấn để mở bằng chứng tương ứng",
                            };
                            return (
                              <button
                                type="button"
                                onClick={() =>
                                  handleInlineCite(msg, parsed.kind, parsed.cite)
                                }
                                title={
                                  titles[parsed.kind as keyof typeof titles] ??
                                  "Nhấn để xem nguồn"
                                }
                                className="rounded-sm font-mono text-xs font-semibold text-brand-700 underline decoration-brand-300 decoration-dotted underline-offset-2 transition-colors duration-150 ease-quick hover:bg-brand-50 hover:text-brand-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
                              >
                                {children}
                              </button>
                            );
                          }
                          return (
                            <a href={href} target="_blank" rel="noopener noreferrer">
                              {children}
                            </a>
                          );
                        },
                      }}
                    >
                      {linkifyCitations(msg.content)}
                    </ReactMarkdown>
                  </div>
                </div>

                {/* BẰNG CHỨNG — citation cards (draft A) */}
                {msg.citationDetails && msg.citationDetails.length > 0 && (
                  <div className="w-full space-y-1.5">
                    <span className="text-overline ml-1 uppercase tracking-[0.08em] text-ink-faint">
                      Bằng chứng
                    </span>
                    {msg.citationDetails.map((citation, i) => (
                      <details
                        key={citation.label}
                        className="group animate-fade-up overflow-hidden rounded-lg border border-brand-950/8 bg-surface shadow-sm"
                        style={{ animationDelay: `${Math.min(i, 5) * 40}ms` }}
                      >
                        <summary className="flex w-full cursor-pointer list-none items-center justify-between px-3 py-2 text-mono font-semibold text-brand-700 transition-colors duration-150 ease-quick hover:bg-surface-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 [&::-webkit-details-marker]:hidden"
                        >
                          <span className="flex min-w-0 items-center gap-2">
                            <FileText size={12} aria-hidden="true" className="shrink-0 text-brand-500" />
                            <span className="truncate">
                              [{citation.label}] {citation.source}
                              {citation.page
                                ? ` · Trang ${citation.page}, dòng ${citation.line_start}-${citation.line_end}`
                                : ""}
                            </span>
                          </span>
                          <CaretRight
                            size={12}
                            aria-hidden="true"
                            className="shrink-0 text-ink-faint transition-transform duration-150 ease-quick group-open:rotate-90"
                          />
                        </summary>
                        <div className="border-t border-brand-950/8 bg-surface-2 p-3">
                          <blockquote className="border-l-2 border-brand-300 py-0.5 pl-3 font-mono text-xs leading-relaxed text-ink-muted">
                            “{citation.quote}”
                          </blockquote>
                          <div className="mt-2 flex flex-wrap items-center gap-2">
                            {/* t28 — nhảy tới đúng trang paper trong viewer */}
                            {citation.page && citation.source && (
                              <button
                                type="button"
                                onClick={() =>
                                  onOpenPaper?.(citation.source!, citation.page!)
                                }
                                className="inline-flex items-center gap-1 rounded-md border border-brand-300 bg-surface px-2 py-1 text-caption font-semibold text-brand-700 transition-colors duration-150 ease-quick hover:bg-brand-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
                              >
                                <FileText size={12} aria-hidden="true" />
                                Xem trang {citation.page}
                              </button>
                            )}
                            {citation.url && (
                              <a
                                href={citation.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 text-caption font-medium text-brand-700 underline decoration-brand-300 underline-offset-2 transition-colors duration-150 ease-quick hover:text-brand-600"
                              >
                                <ArrowSquareOut size={12} aria-hidden="true" />
                                Mở nguồn (arXiv)
                              </a>
                            )}
                          </div>
                        </div>
                      </details>
                    ))}
                  </div>
                )}

                {/* Slide-cite chips — clickable nhảy trang + flash highlight */}
                {(!msg.citationDetails || msg.citationDetails.length === 0) &&
                  msg.citations &&
                  msg.citations.length > 0 && (
                    <div className="flex flex-wrap items-center gap-1.5">
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
                                className="flex animate-fade-up items-center gap-1 rounded-md bg-brand-50 px-2 py-1 text-caption font-medium text-brand-700 ring-1 ring-brand-100 transition-colors duration-150 ease-quick hover:bg-brand-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
                                style={{ animationDelay: `${Math.min(i, 5) * 40}ms` }}
                                title="Mở nguồn arXiv"
                              >
                                <ArrowSquareOut size={12} aria-hidden="true" />
                                {c.replace(/\s*-\s*https?:\/\/\S+$/, "")}
                              </a>
                            );
                          }

                          const isSlide = /^(?:D[12](?:-F|\s*Full)|D\d{1,2})\s*[-–]\s*Trang\s+\d+/i.test(c);
                          /* t28 — paper citation: "arxiv-xxx.pdf - Trang N ... [S1]" → nhảy trang */
                          const paperMatch = c.match(
                            /(arxiv-[A-Za-z0-9._-]+\.pdf)\s*[-–,]\s*Trang\s+(\d+)/i
                          );
                          if (paperMatch) {
                            return (
                              <button
                                key={i}
                                type="button"
                                onClick={() =>
                                  onOpenPaper?.(
                                    paperMatch[1],
                                    parseInt(paperMatch[2], 10)
                                  )
                                }
                                className="flex animate-fade-up items-center gap-1 rounded-md bg-brand-50 px-2 py-1 text-caption font-medium text-brand-700 ring-1 ring-brand-100 transition-colors duration-150 ease-quick hover:bg-brand-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
                                style={{ animationDelay: `${Math.min(i, 5) * 40}ms` }}
                                title="Nhấn để xem đúng trang của paper"
                              >
                                <FileText size={12} aria-hidden="true" />
                                {c}
                              </button>
                            );
                          }
                          if (isSlide) {
                            return (
                              <button
                                key={i}
                                type="button"
                                onClick={() => handleCitationClick(c)}
                                className="flex animate-fade-up items-center gap-1 rounded-md bg-brand-50 px-2 py-1 text-caption font-medium text-brand-700 ring-1 ring-brand-100 transition-colors duration-150 ease-quick hover:bg-brand-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
                                style={{ animationDelay: `${Math.min(i, 5) * 40}ms` }}
                                title="Nhấn để chuyển đến trang slide"
                              >
                                <FileText size={12} aria-hidden="true" />
                                {c}
                              </button>
                            );
                          }

                          return (
                            <span
                              key={i}
                              className="flex animate-fade-up items-center gap-1 rounded-md bg-surface-2 px-2 py-1 text-caption text-ink-muted ring-1 ring-border/50"
                              style={{ animationDelay: `${Math.min(i, 5) * 40}ms` }}
                              title="Nguồn PDF đã index"
                            >
                              <FileText size={12} aria-hidden="true" />
                              {c}
                            </span>
                          );
                        })}
                    </div>
                  )}

                {/* A-05 — envelope: badge move + follow-up chips (t30 — click → điền PROMPT HÀNH ĐỘNG thật, không nhét câu hỏi tutor) */}
                {(msg.move || (msg.followUps && msg.followUps.length > 0)) && (
                  <div className="animate-fade-up flex flex-col items-start gap-1.5 pl-1">
                    {msg.move && MOVE_LABELS[msg.move] && (
                      <span className="text-overline uppercase text-ink-faint">
                        {MOVE_LABELS[msg.move]}
                      </span>
                    )}
                    {msg.followUps && msg.followUps.length > 0 && (
                      <div className="flex flex-wrap gap-1.5">
                        {msg.followUps.map((followUp, index) => {
                          const action = toActionPrompt(followUp);
                          return (
                            <button
                              key={index}
                              type="button"
                              onClick={() => {
                                setInput(action);
                                composerRef.current?.focus();
                              }}
                              className="rounded-lg border border-brand-300 bg-surface px-3 py-1.5 text-left text-xs font-medium text-brand-700 transition-colors duration-150 ease-quick hover:bg-brand-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
                              title="Nhấn để điền vào ô hỏi"
                            >
                              {action}
                            </button>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}

                {/* t35 — P0-2: card misconception từ Tutor Coach A-05 (envelope misconceptions[]) */}
                {msg.misconceptions &&
                  msg.misconceptions.length > 0 &&
                  !dismissedMisc[msg.id] && (
                    <div className="animate-fade-up w-full rounded-lg border border-warning/40 bg-warning/5 p-3 ring-1 ring-warning/10">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex min-w-0 items-start gap-2">
                          <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-warning/15 text-warning">
                            <WarningCircle size={14} aria-hidden="true" />
                          </span>
                          <ul className="min-w-0 space-y-1">
                            {msg.misconceptions.map((misc, index) => (
                              <li key={index} className="text-xs leading-relaxed text-ink">
                                Có thể bạn đang hiểu nhầm: <span className="font-medium text-ink-strong">{misc}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                        <button
                          type="button"
                          onClick={() =>
                            setDismissedMisc((prev) => ({ ...prev, [msg.id]: true }))
                          }
                          aria-label="Bỏ qua ghi chú hiểu nhầm"
                          title="Bỏ qua"
                          className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-ink-faint transition-colors duration-150 ease-quick hover:bg-surface-2 hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
                        >
                          <X size={13} aria-hidden="true" />
                        </button>
                      </div>
                      <div className="mt-2 flex flex-wrap gap-1.5 pl-8">
                        <button
                          type="button"
                          onClick={() => {
                            setInput(miscActionPrompt(msg.misconceptions!));
                            composerRef.current?.focus();
                          }}
                          className="rounded-md bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white transition-colors duration-150 ease-quick hover:bg-brand-700 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2"
                          title="Điền câu hỏi giải thích lại vào ô hỏi"
                        >
                          Giải thích lại
                        </button>
                      </div>
                    </div>
                  )}

                {/* A-07 — rating 👍👎 dưới câu trả lời tutor (gắn trace_id) */}
                {msg.traceId && (
                  <div className="flex items-center gap-1 pl-1">
                    <button
                      type="button"
                      onClick={() => sendFeedback(msg, 1)}
                      disabled={!!ratedFeedback[msg.id]}
                      aria-label="Phản hồi hữu ích"
                      title="Hữu ích"
                      className={`flex h-6 w-6 items-center justify-center rounded-md transition-colors duration-150 ease-quick focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 ${
                        ratedFeedback[msg.id] === 1
                          ? "bg-brand-50 text-brand-600"
                          : "text-ink-faint hover:bg-surface-2 hover:text-ink"
                      } disabled:opacity-50`}
                    >
                      <ThumbsUp size={13} aria-hidden="true" />
                    </button>
                    <button
                      type="button"
                      onClick={() => sendFeedback(msg, -1)}
                      disabled={!!ratedFeedback[msg.id]}
                      aria-label="Phản hồi chưa hữu ích"
                      title="Chưa hữu ích"
                      className={`flex h-6 w-6 items-center justify-center rounded-md transition-colors duration-150 ease-quick focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 ${
                        ratedFeedback[msg.id] === -1
                          ? "bg-brand-50 text-brand-600"
                          : "text-ink-faint hover:bg-surface-2 hover:text-ink"
                      } disabled:opacity-50`}
                    >
                      <ThumbsDown size={13} aria-hidden="true" />
                    </button>
                  </div>
                )}
              </div>
            )
          )}

          {/* Typing indicator — F4: 3 dot brand + trạng thái bước + đồng hồ */}
          {isTyping && (
            <div className="flex items-center gap-3 px-1" role="status" aria-live="polite">
              <div className="flex gap-1">
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-brand-400" style={{ animationDelay: "0ms" }} />
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-brand-400" style={{ animationDelay: "150ms" }} />
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-brand-400" style={{ animationDelay: "300ms" }} />
              </div>
              <span className="text-caption font-medium text-brand-600">
                {typingStatus}{" "}
                <span className="font-mono">{elapsedSec}s</span>
              </span>
            </div>
          )}

          <div ref={chatEndRef} />
        </div>

        {/* Banner lỗi mạng + nút Thử lại (gửi lại turn cuối) */}
        {chatError && (
          <div
            role="alert"
            className="mx-4 mb-3 flex items-start gap-2 rounded-lg bg-danger/5 px-3 py-2.5 ring-1 ring-danger/20"
          >
            <WarningCircle size={16} aria-hidden="true" className="mt-0.5 shrink-0 text-danger" />
            <p className="flex-1 text-body-sm text-danger">{chatError}</p>
            <button
              type="button"
              onClick={() => handleSend(lastQuestionRef.current)}
              className="shrink-0 rounded-md border border-danger/30 px-2 py-1 text-[11px] font-semibold text-danger transition-colors duration-150 ease-quick hover:bg-danger/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
            >
              Thử lại
            </button>
          </div>
        )}

        {/* Composer — draft A: card 2 tầng, auto-grow, send ↔ Dừng (F8) */}
        <div className="shrink-0 border-t border-border p-4">
          <div className="flex flex-col rounded-lg border border-border/50 bg-surface-2 p-1.5 transition-all duration-150 ease-quick focus-within:border-brand-300 focus-within:ring-2 focus-within:ring-brand-100">
            <textarea
              ref={composerRef}
              value={input}
              onChange={handleComposerInput}
              onKeyDown={handleKeyDown}
              placeholder={
                researchMode
                  ? "Hỏi sâu hơn — Research sẽ tìm paper…"
                  : "Nhập câu hỏi về slide…"
              }
              rows={1}
              aria-label="Nhập câu hỏi"
              className="w-full resize-none border-none bg-transparent px-3 py-2 text-sm outline-none placeholder:text-ink-faint focus:ring-0 custom-scrollbar"
              style={{ maxHeight: 132 }}
            />
            <div className="flex items-center justify-between px-2 pb-1">
              <span className="text-caption text-ink-faint">
                Enter gửi · Shift+Enter xuống dòng
              </span>
              {isTyping ? (
                <button
                  type="button"
                  onClick={handleStop}
                  aria-label="Dừng trả lời"
                  title="Dừng"
                  className="flex h-8 w-8 items-center justify-center rounded-lg bg-danger text-white shadow-sm transition-colors duration-150 ease-quick hover:bg-danger/90 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2"
                >
                  <Stop size={16} aria-hidden="true" />
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => handleSend()}
                  disabled={!input.trim()}
                  aria-label="Gửi câu hỏi"
                  className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-white shadow-sm transition-colors duration-150 ease-quick hover:bg-brand-700 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2"
                >
                  <PaperPlaneTilt size={16} aria-hidden="true" />
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
