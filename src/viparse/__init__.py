"""viparse — a Vietnamese-first document loader for RAG."""

from __future__ import annotations

from viparse.api import load, load_batch
from viparse.detect import DetectedFormat, detect_format
from viparse.engines.docx import DocxEngine
from viparse.engines.pdf import PdfEngine
from viparse.engines.xlsx import XlsxEngine
from viparse.errors import (
    EncodingError,
    EngineUnavailable,
    ExtractionError,
    MissingDependency,
    UnsupportedFormat,
    ViparseError,
)
from viparse.model import (
    SCHEMA_VERSION,
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
    "load",
    "load_batch",
    "MetricsHook",
    "MissingDependency",
    "NormalizeForm",
    "NormalizedDoc",
    "Normalizer",
    "OutputFormat",
    "Paragraph",
    "PdfEngine",
    "Pipeline",
    "PipelineMetrics",
    "RawExtraction",
    "Renderer",
    "SCHEMA_VERSION",
    "Source",
    "Table",
    "UnsupportedFormat",
    "VietnameseNormalizer",
    "ViparseError",
    "XlsxEngine",
    "__version__",
    "detect_format",
]
