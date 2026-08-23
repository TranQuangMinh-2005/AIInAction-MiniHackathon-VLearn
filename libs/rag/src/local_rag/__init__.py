"""Local PDF retrieval-augmented generation package."""

from .config import Settings
from .service import RAGService

__all__ = ["RAGService", "Settings"]
__version__ = "0.1.0"
