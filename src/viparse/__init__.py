"""viparse — a Vietnamese-first document loader for RAG."""

from __future__ import annotations

from viparse.model import (
    Chunk,
    Document,
    DocumentMetadata,
    NormalizedDoc,
    RawExtraction,
)
from viparse.protocols import (
    DEFAULT_PRIORITY,
    Engine,
    Normalizer,
    OutputFormat,
    Renderer,
    Source,
)

__version__ = "0.0.0"

__all__ = [
    "DEFAULT_PRIORITY",
    "Chunk",
    "Document",
    "DocumentMetadata",
    "Engine",
    "NormalizedDoc",
    "Normalizer",
    "OutputFormat",
    "RawExtraction",
    "Renderer",
    "Source",
    "__version__",
]
