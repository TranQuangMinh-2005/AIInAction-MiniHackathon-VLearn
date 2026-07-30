"""
RAG module: Index toàn bộ slide PDF bằng embeddings để tìm kiếm semantic.
Chỉ trả về những trang liên quan nhất → tiết kiệm token.
"""

import numpy as np
from pathlib import Path
from pypdf import PdfReader
from agent.providers import build_embedding_model

PDF_DIR = Path(__file__).parent.parent.parent / "frontend" / "public"
PDF_FILES = {
    "d1": PDF_DIR / "d1-slide-hackathon.pdf",
    "d2": PDF_DIR / "d2-slide-hackathon.pdf",
}

class SlideIndex:
    def __init__(self):
        self.page_texts: list[dict] = []
        self.embeddings: np.ndarray | None = None
        self.embeddings_model = None
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
            self.embeddings = np.empty((0, 0))
            self.page_texts = []
            self._loaded = True
            return

        self.embeddings_model = build_embedding_model()
        self.embeddings = np.array(
            self.embeddings_model.embed_documents(texts),
            dtype=float,
        )
        self.page_texts = pages
        self._loaded = True

    def retrieve(self, query: str, doc_id: str | None = None, k: int = 5) -> list[dict]:
        if not self._loaded:
            self.load()

        if self.embeddings is None or not self.page_texts:
            return []

        query_embedding = np.array(
            self.embeddings_model.embed_query(query),
            dtype=float,
        )
        similarities = np.dot(self.embeddings, query_embedding) / (
            np.maximum(np.linalg.norm(self.embeddings, axis=1), 1e-12)
            * max(np.linalg.norm(query_embedding), 1e-12)
        )

        if doc_id:
            mask = np.array([p["doc_id"] == doc_id for p in self.page_texts])
            similarities = np.where(mask, similarities, -1)

        top_k = np.argsort(similarities)[-k:][::-1]

        results = []
        for idx in top_k:
            if similarities[idx] > 0.35:
                results.append(self.page_texts[idx])

        return results

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
