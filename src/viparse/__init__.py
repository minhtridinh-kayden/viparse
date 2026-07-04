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
    Chunk,
    Document,
    DocumentMetadata,
    NormalizedDoc,
    RawExtraction,
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

__version__ = "0.0.0"

__all__ = [
    "DEFAULT_PRIORITY",
    "Chunk",
    "DetectedFormat",
    "DocxEngine",
    "Document",
    "DocumentMetadata",
    "EncodingError",
    "Engine",
    "EngineRegistry",
    "EngineUnavailable",
    "ExtractionError",
    "LoadOptions",
    "MetricsHook",
    "MissingDependency",
    "NormalizeForm",
    "NormalizedDoc",
    "Normalizer",
    "OutputFormat",
    "Pipeline",
    "PipelineMetrics",
    "RawExtraction",
    "Renderer",
    "Source",
    "UnsupportedFormat",
    "VietnameseNormalizer",
    "ViparseError",
    "__version__",
    "detect_format",
]
