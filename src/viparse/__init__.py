"""viparse — a Vietnamese-first document loader for RAG."""

from __future__ import annotations

from viparse.detect import DetectedFormat, detect_format
from viparse.engines.docx import DocxEngine
from viparse.errors import (
    EncodingError,
    EngineUnavailable,
    ExtractionError,
    MissingDependency,
    UnsupportedFormat,
    ViparseError,
)
from viparse.model import (
    Block,
    Chunk,
    Document,
    DocumentMetadata,
    Heading,
    NormalizedDoc,
    Paragraph,
    RawExtraction,
    Table,
)
from viparse.normalize.normalizer import VietnameseNormalizer
from viparse.observability import MetricsHook, PipelineMetrics
from viparse.options import LoadOptions, NormalizeForm, OutputFormat
from viparse.pipeline import Pipeline
from viparse.protocols import (
    DEFAULT_PRIORITY,
    Engine,
    Normalizer,
    Renderer,
    Source,
)
from viparse.registry import EngineRegistry
from viparse.structure import DocumentRenderer

__version__ = "0.0.0"

__all__ = [
    "DEFAULT_PRIORITY",
    "Block",
    "Chunk",
    "DetectedFormat",
    "DocumentRenderer",
    "DocxEngine",
    "Document",
    "DocumentMetadata",
    "EncodingError",
    "Engine",
    "EngineRegistry",
    "EngineUnavailable",
    "ExtractionError",
    "Heading",
    "LoadOptions",
    "MetricsHook",
    "MissingDependency",
    "NormalizeForm",
    "NormalizedDoc",
    "Normalizer",
    "OutputFormat",
    "Paragraph",
    "Pipeline",
    "PipelineMetrics",
    "RawExtraction",
    "Renderer",
    "Source",
    "Table",
    "UnsupportedFormat",
    "VietnameseNormalizer",
    "ViparseError",
    "__version__",
    "detect_format",
]
