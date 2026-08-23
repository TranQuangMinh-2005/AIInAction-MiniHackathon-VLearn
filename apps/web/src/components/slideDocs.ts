export interface SlideDoc {
  id: string;
  title: string;
  code: string;
  pdfPath: string;
  pages: number;
}

/* Danh sách học liệu — dùng chung cho Sidebar + doc switcher (SlideViewer).
   id khớp doc_id trong src/agent/agent/rag.py (PDF_FILES). */
export const slideDocuments: SlideDoc[] = [
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
  {
    id: "d3",
    title: "Day 1 — AI & LLM: Nền tảng mô hình ngôn ngữ (bản full)",
    code: "D1 Full",
    pdfPath: "/day01_ai-llm-model.pdf",
    pages: 78,
  },
  {
    id: "d4",
    title: "Day 2 — Xác định bài toán cho AI (bản full)",
    code: "D2 Full",
    pdfPath: "/day02_xac-dinh-bai-toan-ai.pdf",
    pages: 57,
  },
  {
    id: "d5",
    title: "Day 3 — Design Pattern & ReAct cho Agent",
    code: "D03",
    pdfPath: "/day03-design-pattern-react.pdf",
    pages: 71,
  },
  {
    id: "d6",
    title: "Day 4 — Prompt Engineering & Tool Calling",
    code: "D04",
    pdfPath: "/day04-prompt-engineering-tool-calling.pdf",
    pages: 132,
  },
  {
    id: "d7",
    title: "Day 5 — Thiết kế sản phẩm AI cho sự không chắc chắn",
    code: "D05",
    pdfPath: "/day05-lecture-slides.pdf",
    pages: 52,
  },
  {
    id: "day05-ref",
    title: "Day 5 — Tài liệu tham khảo: Thiết kế sản phẩm AI",
    code: "D05R",
    pdfPath: "/day05-reference-document.pdf",
    pages: 8,
  },
  {
    id: "d8",
    title: "Day 6 — Hackathon: SPEC → Prototype → Demo",
    code: "D06",
    pdfPath: "/day06-lecture-slides.pdf",
    pages: 20,
  },
  {
    id: "d9",
    title: "Day 7 — Data Foundations: Embedding & Vector Store",
    code: "D07",
    pdfPath: "/day07-lecture-slides.pdf",
    pages: 49,
  },
  {
    id: "d10",
    title: "Day 8 — RAG Pipeline: Retrieval – Augmentation – Generation",
    code: "D08",
    pdfPath: "/day08-rag-pipeline.pdf",
    pages: 53,
  },
  {
    id: "d11",
    title: "Day 9 — Multi-Agent, MCP & A2A",
    code: "D09",
    pdfPath: "/day09-multi-agent-mcp-a2a.pdf",
    pages: 79,
  },
  {
    id: "d12",
    title: "Day 10 — Data Pipeline & Data Observability",
    code: "D10",
    pdfPath: "/day10-data-pipeline-observability.pdf",
    pages: 46,
  },
  {
    id: "d13",
    title: "Day 11 — Guardrails & AI Safety",
    code: "D11",
    pdfPath: "/day11-guardrails-ai-safety.pdf",
    pages: 60,
  },
  {
    id: "d14",
    title: "Day 13 — Monitoring, Logging & Observability",
    code: "D13",
    pdfPath: "/day13-monitoring-logging-observability.pdf",
    pages: 78,
  },
  {
    id: "d15",
    title: "Day 14 — AI Evaluation & Benchmarking",
    code: "D14",
    pdfPath: "/day14-ai-evaluation-benchmarking.pdf",
    pages: 115,
  },
  {
    id: "d16",
    title: "Day 15 — Triển khai thực tế, chi phí & định hướng",
    code: "D15",
    pdfPath: "/day15-trien-khai-thuc-te.pdf",
    pages: 35,
  },
];