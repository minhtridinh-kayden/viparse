"""Tests for the core domain model."""

from __future__ import annotations

import dataclasses

import pytest

import viparse
from viparse.model import (
    Chunk,
    Document,
    DocumentMetadata,
    NormalizedDoc,
    RawExtraction,
)


def _sample(cls: type) -> object:
    """Construct a minimal valid instance of each domain type."""
    meta = DocumentMetadata(source="s", content_type="t")
    return {
        DocumentMetadata: meta,
        Chunk: Chunk(text="x", metadata={}, index=0),
        Document: Document(text="x", metadata=meta),
        RawExtraction: RawExtraction(source="s", content_type="t", text="x"),
        NormalizedDoc: NormalizedDoc(source="s", content_type="t", text="x"),
    }[cls]


ALL_TYPES = [DocumentMetadata, Chunk, Document, RawExtraction, NormalizedDoc]


def test_public_exports() -> None:
    """The domain types are importable from the package root."""
    assert viparse.Document is Document
    assert viparse.Chunk is Chunk
    assert viparse.DocumentMetadata is DocumentMetadata
    assert viparse.RawExtraction is RawExtraction
    assert viparse.NormalizedDoc is NormalizedDoc


def test_document_metadata_defaults() -> None:
    meta = DocumentMetadata(source="a.docx", content_type="application/vnd.docx")
    assert meta.source == "a.docx"
    assert meta.page is None
    assert meta.encoding_confidence is None
    assert meta.warnings == []
    assert meta.extra == {}


def test_document_holds_metadata_and_chunks() -> None:
    meta = DocumentMetadata(source="a.docx", content_type="text/plain")
    doc = Document(
        text="Tiếng Việt",
        metadata=meta,
        chunks=[
            Chunk(text="Tiếng", metadata={}, index=0),
            Chunk(text="Việt", metadata={}, index=1),
        ],
    )
    assert doc.text == "Tiếng Việt"
    assert doc.metadata is meta
    assert [c.index for c in doc.chunks] == [0, 1]


def test_mutable_defaults_are_independent() -> None:
    """Default containers must not be shared across instances."""
    d1 = Document(text="x", metadata=DocumentMetadata(source="s", content_type="t"))
    d2 = Document(text="y", metadata=DocumentMetadata(source="s", content_type="t"))
    assert d1.chunks == [] and d2.chunks == []
    assert d1.chunks is not d2.chunks

    m1 = DocumentMetadata(source="s", content_type="t")
    m2 = DocumentMetadata(source="s", content_type="t")
    assert m1.extra is not m2.extra


def test_chunk_positional_order_matches_spec() -> None:
    """SPEC-1 T1.1.2 pins Chunk(text, metadata, index) — construct positionally."""
    chunk = Chunk("body", {"page": 1}, 3)
    assert chunk.text == "body"
    assert chunk.metadata == {"page": 1}
    assert chunk.index == 3


@pytest.mark.parametrize("cls", ALL_TYPES)
def test_types_are_frozen(cls: type) -> None:
    """Every domain type is an immutable dataclass; assignment is rejected."""
    assert dataclasses.is_dataclass(cls)
    instance = _sample(cls)
    first_field = dataclasses.fields(cls)[0].name
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(instance, first_field, "mutated")


@pytest.mark.parametrize("cls", ALL_TYPES)
def test_types_are_hashable(cls: type) -> None:
    """Frozen types stay hashable despite carrying dict/list fields (usable in a set)."""
    instance = _sample(cls)
    assert isinstance(hash(instance), int)
    assert instance in {instance}


def test_raw_extraction_carries_signals() -> None:
    raw = RawExtraction(
        source="a.docx",
        content_type="application/vnd.docx",
        text="raw",
        engine="docx",
        signals={"font": ".VnTime"},
    )
    assert raw.signals["font"] == ".VnTime"
    assert raw.warnings == []


def test_normalized_doc_records_detection() -> None:
    nd = NormalizedDoc(
        source="a.docx",
        content_type="application/vnd.docx",
        text="normalized",
        encoding_detected="tcvn3",
        encoding_confidence=0.95,
        lang="vi",
    )
    assert nd.encoding_detected == "tcvn3"
    assert nd.encoding_confidence == pytest.approx(0.95)
    assert nd.lang == "vi"
