"""
RAG module: Index toàn bộ slide PDF, retrieval cho Slide Scholar (A-02).

A-02 nâng cấp:
- DOC_TITLES: tên tài liệu đầy đủ (khớp slideDocs.ts) — thay hardcode d1/d2 ở server.
- Full-corpus: scope="auto" = tìm doc hiện tại trước (kèm page-in-view boost),
  nếu không có hit nào (điểm BM25 = 0) → fallback tìm TOÀN BỘ 17 tài liệu.
  Citations luôn mang tiền tố doc (D05 - Trang X) nên không bao giờ "nhảy" doc.
- Multi-query expansion: 1-3 biến thể (gốc + LLM + bản rút gọn) hợp nhất điểm;
  LLM lỗi/quota → fallback deterministic (bật/tắt bằng SLIDE_MULTI_QUERY, mặc định 1).
- Hybrid dense+BM25 tùy chọn (SLIDE_HYBRID=1): embed top-pool rồi rerank bằng
  HybridRetriever của libs/rag (dense 0.76 + BM25 + MMR); bất kỳ lỗi/quota
  nào cũng tự fallback về BM25 (giữ pattern paper RAG).
"""

import os
import re
from collections import namedtuple
from dataclasses import replace
from pathlib import Path

from pypdf import PdfReader
from local_rag.retrieval import bm25_scores

PDF_DIR = Path(__file__).parent.parent.parent / "web" / "public"
# A-11 — sidecar OCR text (day03 scan 66/71 trang ảnh): SlideIndex ưu tiên
# đọc text file, PDF extract_text chỉ là fallback (giữ nguyên bản gốc cho viewer).
OCR_TEXT_DIR = PDF_DIR / "day03-ocr"
PDF_FILES = {
    "d1": PDF_DIR / "d1-slide-hackathon.pdf",
    "d2": PDF_DIR / "d2-slide-hackathon.pdf",
    # 15 slide bài giảng full (AI Thực Chiến Phase 1) — bản đầy đủ, giữ nguyên d1/d2 hackathon
    "d3": PDF_DIR / "day01_ai-llm-model.pdf",
    "d4": PDF_DIR / "day02_xac-dinh-bai-toan-ai.pdf",
    "d5": PDF_DIR / "day03-design-pattern-react.pdf",
    "d6": PDF_DIR / "day04-prompt-engineering-tool-calling.pdf",
    "d7": PDF_DIR / "day05-lecture-slides.pdf",
    "day05-ref": PDF_DIR / "day05-reference-document.pdf",
    "d8": PDF_DIR / "day06-lecture-slides.pdf",
    "d9": PDF_DIR / "day07-lecture-slides.pdf",
    "d10": PDF_DIR / "day08-rag-pipeline.pdf",
    "d11": PDF_DIR / "day09-multi-agent-mcp-a2a.pdf",
    "d12": PDF_DIR / "day10-data-pipeline-observability.pdf",
    "d13": PDF_DIR / "day11-guardrails-ai-safety.pdf",
    "d14": PDF_DIR / "day13-monitoring-logging-observability.pdf",
    "d15": PDF_DIR / "day14-ai-evaluation-benchmarking.pdf",
    "d16": PDF_DIR / "day15-trien-khai-thuc-te.pdf",
}

# Tiêu đề tài liệu — khớp slideDocs.ts (frontend). Dùng cho slide_title + context.
DOC_TITLES = {
    "d1": "Day 1 — AI & LLM Foundation",
    "d2": "Day 2 — Xác định bài toán cho AI",
    "d3": "Day 1 — AI & LLM: Nền tảng mô hình ngôn ngữ (bản full)",
    "d4": "Day 2 — Xác định bài toán cho AI (bản full)",
    "d5": "Day 3 — Design Pattern & ReAct cho Agent",
    "d6": "Day 4 — Prompt Engineering & Tool Calling",
    "d7": "Day 5 — Thiết kế sản phẩm AI cho sự không chắc chắn",
    "day05-ref": "Day 5 — Tài liệu tham khảo: Thiết kế sản phẩm AI",
    "d8": "Day 6 — Hackathon: SPEC → Prototype → Demo",
    "d9": "Day 7 — Data Foundations: Embedding & Vector Store",
    "d10": "Day 8 — RAG Pipeline: Retrieval – Augmentation – Generation",
    "d11": "Day 9 — Multi-Agent, MCP & A2A",
    "d12": "Day 10 — Data Pipeline & Data Observability",
    "d13": "Day 11 — Guardrails & AI Safety",
    "d14": "Day 13 — Monitoring, Logging & Observability",
    "d15": "Day 14 — AI Evaluation & Benchmarking",
    "d16": "Day 15 — Triển khai thực tế, chi phí & định hướng",
}

_PAGE_CHUNK = namedtuple("PageChunk", ["content"])

# Tiền tố hỏi thừa có thể rút gọn cho biến thể query ("giải thích tóm tắt về X" → "X").
_QUERY_PREFIX = re.compile(
    r"^(?:giải\s*thích|tóm\s*tắt|tổng\s*hợp|cho\s*mình\s*biết|explain|summarize)"
    r"\s+(?:về\s+|về\s+)?",
    re.IGNORECASE,
)

_EXPAND_PROMPT = """Bạn là chuyên gia truy vấn tài liệu slide cho khóa học AI/ML.
Cho câu hỏi của học viên, viết THÊM tối đa 2 biến thể truy vấn ngắn (mỗi biến thể
một dòng, 3-12 từ) giúp tìm đúng nội dung trên slide: 1 biến thể rút gọn/đúng trọng
tâm, 1 biến thể chuyển sang tiếng Anh nếu hợp lý (giữ thuật ngữ gốc như RAG, LLM...).
Không giải thích, không đánh số, không lặp lại câu gốc.
Câu hỏi: {question}"""


def _expand_queries(query: str) -> list[str]:
    """2-3 biến thể truy vấn (gốc + LLM nếu bật + rút gọn deterministic). Tối đa 3."""
    variants = [query]
    seen = {query.casefold()}

    if os.getenv("SLIDE_MULTI_QUERY", "1") == "1":
        try:
            from agent.llm import llm  # lazy: tránh phụ thuộc khi import thuần

            response = llm.invoke(_EXPAND_PROMPT.format(question=query[:500]))
            for line in response.content.splitlines():
                variant = line.strip().strip("-•*").strip()
                if 3 <= len(variant) <= 120 and variant.casefold() not in seen:
                    variants.append(variant)
                    seen.add(variant.casefold())
                if len(variants) >= 3:
                    break
        except Exception:
            pass  # LLM lỗi/quota → chỉ dùng deterministic

    stripped = _QUERY_PREFIX.sub("", query).strip()
    if stripped and stripped.casefold() not in seen:
        variants.append(stripped)
    return variants[:3]


def _page_boost(page: dict, current_page: int | None) -> float:
    """Ưu tiên nhẹ trang user đang xem (fix "trả lời sai trang" — A-02)."""
    if not current_page:
        return 0.0
    distance = abs(page["page"] - current_page)
    if distance == 0:
        return 0.12
    if distance <= 2:
        return 0.06
    return 0.0


class SlideIndex:
    def __init__(self):
        self.page_texts: list[dict] = []
        self._loaded = False

    def load(self):
        if self._loaded:
            return

        pages = []
        for doc_id, path in PDF_FILES.items():
            if not path.exists():
                continue
            reader = PdfReader(str(path))
            for i in range(len(reader.pages)):
                # A-11 — ưu tiên sidecar OCR (day03-ocr/{doc}-p{n}.txt)
                sidecar = OCR_TEXT_DIR / f"{doc_id}-p{i + 1}.txt"
                if sidecar.exists():
                    text = sidecar.read_text(encoding="utf-8").strip()
                else:
                    text = reader.pages[i].extract_text() or ""
                if not text.strip():
                    continue
                pages.append({
                    "doc_id": doc_id,
                    "page": i + 1,
                    "text": text,
                })

        self.page_texts = pages
        self._loaded = True

    # ── Ranking lõi ─────────────────────────────────────────────────────────

    def _bm25_multi_rank(
        self,
        query: str,
        candidates: list[dict],
        k: int,
        current_page: int | None,
    ) -> list[dict]:
        """BM25 theo từng biến thể query → hợp nhất điểm max → top k."""
        variants = _expand_queries(query)
        best: dict[tuple[str, int], tuple[float, dict]] = {}
        for variant in variants:
            pseudo_chunks = [_PAGE_CHUNK(content=page["text"]) for page in candidates]
            scores = bm25_scores(variant, pseudo_chunks)
            for page, score in zip(candidates, scores):
                boosted = score + _page_boost(page, current_page)
                key = (page["doc_id"], page["page"])
                if boosted > best.get(key, (float("-inf"),))[0]:
                    best[key] = (boosted, page)
        ranked = sorted(best.values(), key=lambda item: item[0], reverse=True)
        return [page for score, page in ranked[:k] if score > 0]

    def _hybrid_rank(
        self,
        query: str,
        candidates: list[dict],
        k: int,
        pool_size: int = 24,
    ) -> list[dict]:
        """Hybrid dense+BM25 như paper RAG: embed top-pool rồi rerank (MMR).

        Chỉ chạy khi SLIDE_HYBRID=1; mọi lỗi phải được caller bắt → fallback BM25.
        """
        from local_rag.models import Chunk
        from local_rag.retrieval import HybridRetriever
        from local_rag.service import RAGService

        pseudo = [_PAGE_CHUNK(content=page["text"]) for page in candidates]
        scores = bm25_scores(query, pseudo)
        pool = [
            page
            for page, score in sorted(
                zip(candidates, scores), key=lambda item: item[1], reverse=True
            )[:pool_size]
        ]
        if not pool:
            return []

        embedder = RAGService.from_env().embedder
        chunks = [
            Chunk(
                id=f"{page['doc_id']}-p{page['page']}",
                document_id=page["doc_id"],
                source=page["doc_id"],
                title=page["doc_id"],
                page=page["page"],
                content=page["text"],
                word_count=len(page["text"].split()),
                section=page["doc_id"],
            )
            for page in pool
        ]
        vectors = embedder.embed_documents([chunk.content for chunk in chunks])
        chunks = [
            replace(chunk, embedding=tuple(vector))
            for chunk, vector in zip(chunks, vectors)
        ]
        results = HybridRetriever(embedder).search(query, chunks, top_k=k)

        by_id = {(page["doc_id"], page["page"]): page for page in pool}
        selected = [
            by_id[(result.source, result.page)]
            for result in results
            if (result.source, result.page) in by_id
        ]
        return selected or pool[:k]

    # ── API retrieval ────────────────────────────────────────────────────────

    def retrieve(
        self,
        query: str,
        doc_id: str | None = None,
        k: int = 5,
        *,
        current_page: int | None = None,
        scope: str = "auto",
    ) -> list[dict]:
        """scope='doc' → chỉ doc hiện tại · 'corpus' → toàn bộ 17 tài liệu ·
        'auto' (mặc định) → doc hiện tại trước, không hit thì toàn bộ corpus."""
        if not self._loaded:
            self.load()
        if not self.page_texts:
            return []

        target = (
            [page for page in self.page_texts if page["doc_id"] == doc_id]
            if doc_id
            else None
        )
        if scope == "doc" and not target:
            return []

        if scope == "corpus":
            candidates = self.page_texts
        elif scope == "doc":
            candidates = target or []
        else:  # "auto": doc hiện tại trước, corpus là fallback ở dưới
            candidates = target or self.page_texts

        hybrid = os.getenv("SLIDE_HYBRID", "0") == "1"
        if hybrid:
            try:
                results = self._hybrid_rank(query, candidates, k)
                if results:
                    return results
            except Exception:
                pass  # embed lỗi/quota → fallback BM25 offline (A-02)

        results = self._bm25_multi_rank(query, candidates, k, current_page)

        # scope='auto': doc hiện tại không có hit → tìm toàn corpus
        if scope == "auto" and not results and target:
            results = self._bm25_multi_rank(query, self.page_texts, k, current_page)

        # Best effort cuối (giữ hành vi cũ): không điểm nào > 0 → trả top-1
        if not results and candidates:
            pseudo = [_PAGE_CHUNK(content=page["text"]) for page in candidates]
            scores = bm25_scores(query, pseudo)
            ranked = sorted(
                zip(candidates, scores),
                key=lambda item: item[1],
                reverse=True,
            )
            results = [ranked[0][0]] if ranked else []
        return results

    def retrieve_context(
        self,
        query: str,
        doc_id: str | None = None,
        k: int = 5,
        *,
        current_page: int | None = None,
        scope: str = "auto",
    ) -> tuple[str, list[str]]:
        results = self.retrieve(
            query,
            doc_id=doc_id,
            k=k,
            current_page=current_page,
            scope=scope,
        )
        if not results:
            return "", []

        chunks = []
        citations = []
        for r in results:
            label = citation_label(r["doc_id"])
            chunks.append(f"--- {label} - Trang {r['page']} ---\n{r['text']}")
            citations.append(f"{label} - Trang {r['page']}")

        return "\n\n".join(chunks), citations


# P0-1 — nhãn citation DEDUPE (SCHEME B — PO2 chốt): bản short hackathon (d1/d2)
# giữ "D1"/"D2"; bản FULL cùng ngày (d3 = Day1 full, d4 = Day2 full) dùng
# "D1 Full"/"D2 Full" — rõ nghĩa với học viên + khớp ngôn ngữ sidebar "bản full".
# Các doc khác dùng doc_id.upper() (vốn unique). Legacy D3..D16/DAY05-REF vẫn
# decode theo doc_id (backward-compat history cũ).
_DOC_LABELS = {
    "d1": "D1",
    "d2": "D2",
    "d3": "D1 Full",
    "d4": "D2 Full",
}


def citation_label(doc_id: str) -> str:
    """Nhãn citation duy nhất cho doc_id (P0-1)."""
    return _DOC_LABELS.get(doc_id, doc_id.upper())


slide_index = SlideIndex()