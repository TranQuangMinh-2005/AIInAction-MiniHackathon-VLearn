"""
RAG module: Index toàn bộ slide PDF bằng embeddings để tìm kiếm semantic.
Chỉ trả về những trang liên quan nhất → tiết kiệm token.
"""

import os
import numpy as np
from pathlib import Path
from pypdf import PdfReader
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

PDF_DIR = Path(__file__).parent.parent.parent / "frontend" / "public"
PDF_FILES = {
    "d1": PDF_DIR / "d1-slide-hackathon.pdf",
    "d2": PDF_DIR / "d2-slide-hackathon.pdf",
}

embeddings_model = OpenAIEmbeddings(
    model="text-embedding-3-small",
)

class SlideIndex:
    def __init__(self):
        self.page_texts: list[dict] = []
        self.embeddings: np.ndarray | None = None
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
        self.embeddings = np.array(embeddings_model.embed_documents(texts))
        self.page_texts = pages
        self._loaded = True

    def retrieve(self, query: str, doc_id: str | None = None, k: int = 5) -> list[dict]:
        if not self._loaded:
            self.load()

        query_embedding = np.array(embeddings_model.embed_query(query))
        similarities = np.dot(self.embeddings, query_embedding) / (
            np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_embedding)
        )

        if doc_id:
            mask = np.array([p["doc_id"] == doc_id for p in self.page_texts])
            similarities = np.where(mask, similarities, -1)

        top_k = np.argsort(similarities)[-k:][::-1]

        results = []
        for idx in top_k:
            if similarities[idx] > 0.5:
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
