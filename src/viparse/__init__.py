"""viparse — a Vietnamese-first document loader for RAG."""

from __future__ import annotations

from viparse.api import load, load_batch
from viparse.cache import Cache, DiskCache, MemoryCache
from viparse.chunk import ChunkOptions, chunk_document
from viparse.detect import DetectedFormat, detect_format
from viparse.engines.docx import DocxEngine
from viparse.engines.legacy import LegacyOfficeEngine
from viparse.engines.ocr import OcrEngine
from viparse.engines.pdf import PdfEngine
from viparse.engines.xlsx import XlsxEngine
from viparse.errors import (
    EncodingError,
    EngineUnavailable,
    ExtractionError,
    MissingDependency,
    UnsafeInput,
    UnsupportedFormat,
    ViparseError,
)
from viparse.integrations import to_langchain_documents, to_llamaindex_documents
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
    "Cache",
    "Chunk",
    "ChunkOptions",
    "chunk_document",
    "DetectedFormat",
    "DiskCache",
    "MemoryCache",
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
    "LegacyOfficeEngine",
    "LoadOptions",
    "load",
    "load_batch",
    "MetricsHook",
    "MissingDependency",
    "NormalizeForm",
    "NormalizedDoc",
    "Normalizer",
    "OcrEngine",
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
    "to_langchain_documents",
    "to_llamaindex_documents",
    "UnsafeInput",
    "UnsupportedFormat",
    "VietnameseNormalizer",
    "ViparseError",
    "XlsxEngine",
    "__version__",
    "detect_format",
]
