"""Tests for the pipeline layer Protocols."""

from __future__ import annotations

from pathlib import Path

import viparse
from viparse.model import Document, DocumentMetadata, NormalizedDoc, RawExtraction
from viparse.options import LoadOptions, OutputFormat
from viparse.protocols import (
    DEFAULT_PRIORITY,
    Engine,
    Normalizer,
    Renderer,
    Source,
)


class FakeEngine:
    """A minimal in-memory Engine implementation for tests."""

    priority = DEFAULT_PRIORITY

    def supports(self, content_type: str) -> bool:
        return content_type == "text/plain"

    def extract(self, source: Source, options: LoadOptions) -> RawExtraction:
        return RawExtraction(
            source=str(source), content_type="text/plain", text="raw", engine="fake"
        )


class FakeNormalizer:
    def normalize(self, raw: RawExtraction, options: LoadOptions) -> NormalizedDoc:
        return NormalizedDoc(
            source=raw.source,
            content_type=raw.content_type,
            text=raw.text.upper(),
            engine=raw.engine,
            encoding_detected="utf-8",
            encoding_confidence=1.0,
        )


class FakeRenderer:
    def render(self, doc: NormalizedDoc, fmt: OutputFormat = "markdown") -> Document:
        meta = DocumentMetadata(
            source=doc.source,
            content_type=doc.content_type,
            engine=doc.engine,
            encoding_detected=doc.encoding_detected,
            encoding_confidence=doc.encoding_confidence,
        )
        return Document(text=doc.text, metadata=meta)


def test_protocols_exported_from_package_root() -> None:
    assert viparse.Engine is Engine
    assert viparse.Normalizer is Normalizer
    assert viparse.Renderer is Renderer
    assert viparse.DEFAULT_PRIORITY == DEFAULT_PRIORITY


def test_fakes_conform_structurally() -> None:
    assert isinstance(FakeEngine(), Engine)
    assert isinstance(FakeNormalizer(), Normalizer)
    assert isinstance(FakeRenderer(), Renderer)


def test_nonconforming_object_is_not_an_engine() -> None:
    class NotEngine:
        def supports(self, content_type: str) -> bool:  # missing extract() + priority
            return True

    assert not isinstance(NotEngine(), Engine)


def test_engine_supports_and_priority() -> None:
    engine = FakeEngine()
    assert engine.supports("text/plain")
    assert not engine.supports("application/pdf")
    assert engine.priority == DEFAULT_PRIORITY


def test_manual_pipeline_chain() -> None:
    """A fake Engine → Normalizer → Renderer runs end-to-end without heavy deps."""
    engine, normalizer, renderer = FakeEngine(), FakeNormalizer(), FakeRenderer()
    raw = engine.extract(Path("a.txt"), LoadOptions())
    nd = normalizer.normalize(raw, LoadOptions())
    doc = renderer.render(nd, "markdown")
    assert isinstance(doc, Document)
    assert doc.text == "RAW"
    assert doc.metadata.encoding_detected == "utf-8"


def test_renderer_default_format() -> None:
    doc = FakeRenderer().render(NormalizedDoc(source="s", content_type="t", text="x"))
    assert isinstance(doc, Document)
    assert doc.text == "x"
