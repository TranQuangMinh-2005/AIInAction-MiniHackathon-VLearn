"""
RAG module: Index toàn bộ slide PDF bằng embeddings để tìm kiếm semantic.
Chỉ trả về những trang liên quan nhất → tiết kiệm token.
"""

from pathlib import Path
from pypdf import PdfReader
from local_rag.retrieval import bm25_scores

PDF_DIR = Path(__file__).parent.parent.parent / "frontend" / "public"
PDF_FILES = {
    "d1": PDF_DIR / "d1-slide-hackathon.pdf",
    "d2": PDF_DIR / "d2-slide-hackathon.pdf",
}

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
                text = reader.pages[i].extract_text() or ""
                if not text.strip():
                    continue
                pages.append({
                    "doc_id": doc_id,
                    "page": i + 1,
                    "text": text.strip(),
                })

        texts = [p["text"] for p in pages]
        if not texts:
            self.page_texts = []
            self._loaded = True
            return

        self.page_texts = pages
        self._loaded = True

    def retrieve(self, query: str, doc_id: str | None = None, k: int = 5) -> list[dict]:
        if not self._loaded:
            self.load()

        if not self.page_texts:
            return []

        candidates = [
            page
            for page in self.page_texts
            if not doc_id or page["doc_id"] == doc_id
        ]
        if not candidates:
            return []
        # BM25 is deterministic, offline, and avoids blocking server startup
        # on an embedding quota just before a short demo.
        pseudo_chunks = [
            type("PageChunk", (), {"content": page["text"]})()
            for page in candidates
        ]
        scores = bm25_scores(query, pseudo_chunks)
        ranked = sorted(
            zip(candidates, scores),
            key=lambda item: item[1],
            reverse=True,
        )
        selected = [page for page, score in ranked[:k] if score > 0]
        return selected or [page for page, _score in ranked[:1]]

    def retrieve_context(self, query: str, doc_id: str | None = None, k: int = 5) -> tuple[str, list[str]]:
        results = self.retrieve(query, doc_id=doc_id, k=k)
        if not results:
            return "", []

        chunks = []
        citations = []
        for r in results:
            chunks.append(f"--- {r['doc_id'].upper()} - Trang {r['page']} ---\n{r['text']}")
            citations.append(f"{r['doc_id'].upper()} - Trang {r['page']}")

        return "\n\n".join(chunks), citations

slide_index = SlideIndex()
