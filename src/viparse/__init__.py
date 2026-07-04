"""viparse — a Vietnamese-first document loader for RAG."""

from __future__ import annotations

from viparse.model import (
    Chunk,
    Document,
    DocumentMetadata,
    NormalizedDoc,
    RawExtraction,
)

__version__ = "0.0.0"

__all__ = [
    "Chunk",
    "Document",
    "DocumentMetadata",
    "NormalizedDoc",
    "RawExtraction",
    "__version__",
]
