"""Tests for the pipeline orchestrator."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from viparse.detect import CONTENT_TYPE_DOCX
from viparse.errors import EngineUnavailable, ExtractionError, UnsupportedFormat
from viparse.model import Document, DocumentMetadata, NormalizedDoc, RawExtraction
from viparse.options import LoadOptions, OutputFormat
from viparse.pipeline import Pipeline
from viparse.protocols import Source
from viparse.registry import EngineRegistry


class RecordingEngine:
    priority = 100

    def __init__(self) -> None:
        self.seen_options: LoadOptions | None = None

    def supports(self, content_type: str) -> bool:
        return True

    def extract(self, source: Source, options: LoadOptions) -> RawExtraction:
        self.seen_options = options
        return RawExtraction(
            source=str(source), content_type=CONTENT_TYPE_DOCX, text="raw", engine="rec"
        )


class FailingEngine:
    priority = 200  # higher than RecordingEngine, so it is tried first

    def supports(self, content_type: str) -> bool:
        return True

    def extract(self, source: Source, options: LoadOptions) -> RawExtraction:
        raise RuntimeError("boom")


class RecordingNormalizer:
    def __init__(self) -> None:
        self.seen_options: LoadOptions | None = None

    def normalize(self, raw: RawExtraction, options: LoadOptions) -> NormalizedDoc:
        self.seen_options = options
        return NormalizedDoc(
            source=raw.source,
            content_type=raw.content_type,
            text=raw.text.upper(),
            engine=raw.engine,
        )


class RecordingRenderer:
    def __init__(self) -> None:
        self.seen_fmt: OutputFormat | None = None

    def render(self, doc: NormalizedDoc, fmt: OutputFormat = "markdown") -> Document:
        self.seen_fmt = fmt
        meta = DocumentMetadata(source=doc.source, content_type=doc.content_type, engine=doc.engine)
        return Document(text=doc.text, metadata=meta)


def _docx(path: Path) -> Path:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("word/document.xml", "<w:document/>")
    return path


def _digital_pdf(path: Path) -> Path:
    path.write_bytes(b"%PDF-1.7\n<< /Font 1 0 R >>\n")
    return path


def _fontless_pdf(path: Path) -> Path:
    path.write_bytes(b"%PDF-1.7\n<< /XObject 1 0 R >>\n")
    return path


def _pipeline() -> tuple[Pipeline, RecordingEngine, RecordingNormalizer, RecordingRenderer]:
    engine, normalizer, renderer = RecordingEngine(), RecordingNormalizer(), RecordingRenderer()
    reg = EngineRegistry()
    reg.register(engine)
    return Pipeline(reg, normalizer, renderer), engine, normalizer, renderer


def test_run_orchestrates_all_layers(tmp_path: Path) -> None:
    pipeline, *_ = _pipeline()
    doc = pipeline.run(_docx(tmp_path / "a.docx"))
    assert isinstance(doc, Document)
    assert doc.text == "RAW"
    assert doc.metadata.content_type == CONTENT_TYPE_DOCX


def test_run_threads_options_to_every_layer(tmp_path: Path) -> None:
    pipeline, engine, normalizer, renderer = _pipeline()
    opts = LoadOptions(fmt="json", encoding="tcvn3", ocr=True, normalize_form="NFC")
    pipeline.run(_docx(tmp_path / "a.docx"), opts)
    assert engine.seen_options is opts
    assert normalizer.seen_options is opts
    assert renderer.seen_fmt == "json"


def test_run_uses_default_options(tmp_path: Path) -> None:
    pipeline, engine, _, renderer = _pipeline()
    pipeline.run(_docx(tmp_path / "a.docx"))
    assert engine.seen_options == LoadOptions()
    assert renderer.seen_fmt == "markdown"


def test_run_raises_when_no_engine(tmp_path: Path) -> None:
    pipeline = Pipeline(EngineRegistry(), RecordingNormalizer(), RecordingRenderer())
    with pytest.raises(EngineUnavailable, match="no engine registered"):
        pipeline.run(_docx(tmp_path / "a.docx"))


def test_scanned_hint_resolves_ocr(tmp_path: Path) -> None:
    """A digital PDF (has /Font) resolves an unset ocr hook to False."""
    pipeline, engine, *_ = _pipeline()
    pipeline.run(_digital_pdf(tmp_path / "a.pdf"))
    assert engine.seen_options is not None
    assert engine.seen_options.ocr is False


def test_unknown_scan_hint_leaves_ocr_unset(tmp_path: Path) -> None:
    pipeline, engine, *_ = _pipeline()
    pipeline.run(_fontless_pdf(tmp_path / "a.pdf"))
    assert engine.seen_options is not None
    assert engine.seen_options.ocr is None


def test_explicit_ocr_overrides_scan_hint(tmp_path: Path) -> None:
    pipeline, engine, *_ = _pipeline()
    pipeline.run(_digital_pdf(tmp_path / "a.pdf"), LoadOptions(ocr=True))
    assert engine.seen_options is not None
    assert engine.seen_options.ocr is True


def test_run_falls_back_to_next_engine_on_failure(tmp_path: Path) -> None:
    engine = RecordingEngine()
    reg = EngineRegistry()
    reg.register(engine)  # priority 100
    reg.register(FailingEngine())  # priority 200 → tried first, raises
    pipeline = Pipeline(reg, RecordingNormalizer(), RecordingRenderer())
    doc = pipeline.run(_docx(tmp_path / "a.docx"))
    assert doc.text == "RAW"  # fell back to the recording engine
    assert engine.seen_options is not None


def test_strict_mode_raises_extraction_error_when_all_engines_fail(tmp_path: Path) -> None:
    reg = EngineRegistry()
    reg.register(FailingEngine())
    pipeline = Pipeline(reg, RecordingNormalizer(), RecordingRenderer())
    with pytest.raises(ExtractionError, match="boom") as excinfo:
        pipeline.run(_docx(tmp_path / "a.docx"))
    assert isinstance(excinfo.value.__cause__, RuntimeError)


def test_lenient_mode_returns_warning_document_on_extraction_failure(tmp_path: Path) -> None:
    reg = EngineRegistry()
    reg.register(FailingEngine())
    pipeline = Pipeline(reg, RecordingNormalizer(), RecordingRenderer())
    doc = pipeline.run(_docx(tmp_path / "a.docx"), LoadOptions(strict=False))
    assert doc.text == ""
    assert doc.metadata.content_type == CONTENT_TYPE_DOCX
    assert "boom" in doc.metadata.warnings[0]


def test_strict_mode_propagates_unsupported_format(tmp_path: Path) -> None:
    f = tmp_path / "a.txt"
    f.write_bytes(b"plain text, not a known format")
    pipeline, *_ = _pipeline()
    with pytest.raises(UnsupportedFormat):
        pipeline.run(f)


def test_lenient_mode_handles_unsupported_format(tmp_path: Path) -> None:
    """An unrecognized file (no __cause__) degrades to a warning document."""
    f = tmp_path / "a.txt"
    f.write_bytes(b"plain text, not a known format")
    pipeline, *_ = _pipeline()
    doc = pipeline.run(f, LoadOptions(strict=False))
    assert doc.text == ""
    assert doc.metadata.content_type == "application/octet-stream"
    assert doc.metadata.warnings


def test_lenient_mode_handles_missing_engine(tmp_path: Path) -> None:
    pipeline = Pipeline(EngineRegistry(), RecordingNormalizer(), RecordingRenderer())
    doc = pipeline.run(_docx(tmp_path / "a.docx"), LoadOptions(strict=False))
    assert doc.text == ""
    assert doc.metadata.content_type == CONTENT_TYPE_DOCX  # detected before engine lookup
    assert doc.metadata.warnings


def test_run_batch_returns_one_document_per_source(tmp_path: Path) -> None:
    pipeline, *_ = _pipeline()
    docs = pipeline.run_batch([_docx(tmp_path / "a.docx"), _docx(tmp_path / "b.docx")])
    assert len(docs) == 2
    assert all(isinstance(d, Document) for d in docs)
