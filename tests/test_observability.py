"""Tests for pipeline observability: metrics hook + structured logging."""

from __future__ import annotations

import logging
import zipfile
from pathlib import Path

import pytest

from viparse.detect import CONTENT_TYPE_DOCX
from viparse.errors import ExtractionError
from viparse.model import Document, DocumentMetadata, NormalizedDoc, RawExtraction
from viparse.observability import MetricsHook, PipelineMetrics
from viparse.options import LoadOptions, OutputFormat
from viparse.pipeline import Pipeline
from viparse.protocols import Engine, Source
from viparse.registry import EngineRegistry


class OkEngine:
    priority = 100

    def supports(self, content_type: str) -> bool:
        return True

    def extract(self, source: Source, options: LoadOptions) -> RawExtraction:
        return RawExtraction(
            source=str(source), content_type=CONTENT_TYPE_DOCX, text="raw", engine="ok"
        )


class BoomEngine:
    priority = 100

    def supports(self, content_type: str) -> bool:
        return True

    def extract(self, source: Source, options: LoadOptions) -> RawExtraction:
        raise RuntimeError("boom")


class OkNormalizer:
    def normalize(self, raw: RawExtraction, options: LoadOptions) -> NormalizedDoc:
        return NormalizedDoc(
            source=raw.source,
            content_type=raw.content_type,
            text=raw.text,
            engine=raw.engine,
            encoding_detected="utf-8",
        )


class BugNormalizer:
    """A normalizer that raises a plain (non-viparse) programming error."""

    def normalize(self, raw: RawExtraction, options: LoadOptions) -> NormalizedDoc:
        raise KeyError("bug")


class OkRenderer:
    def render(self, doc: NormalizedDoc, fmt: OutputFormat = "markdown") -> Document:
        meta = DocumentMetadata(source=doc.source, content_type=doc.content_type, engine=doc.engine)
        return Document(text=doc.text, metadata=meta)


def _docx(path: Path) -> Path:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("word/document.xml", "<w:document/>")
    return path


def _pipeline(engine: Engine, hook: MetricsHook | None = None) -> Pipeline:
    reg = EngineRegistry()
    reg.register(engine)
    return Pipeline(reg, OkNormalizer(), OkRenderer(), metrics_hook=hook)


def test_metrics_hook_receives_success_record(tmp_path: Path) -> None:
    seen: list[PipelineMetrics] = []
    pipeline = _pipeline(OkEngine(), seen.append)
    pipeline.run(_docx(tmp_path / "a.docx"))
    assert len(seen) == 1
    m = seen[0]
    assert m.ok is True
    assert m.content_type == CONTENT_TYPE_DOCX
    assert m.engine == "ok"
    assert m.encoding_detected == "utf-8"
    assert m.error is None
    assert set(m.layer_seconds) == {"detect", "extract", "normalize", "render"}
    assert all(v >= 0 for v in m.layer_seconds.values())
    assert m.total_seconds >= 0


def test_metrics_hook_records_strict_failure_and_reraises(tmp_path: Path) -> None:
    seen: list[PipelineMetrics] = []
    pipeline = _pipeline(BoomEngine(), seen.append)
    with pytest.raises(ExtractionError):
        pipeline.run(_docx(tmp_path / "a.docx"))
    assert len(seen) == 1
    assert seen[0].ok is False
    assert seen[0].error is not None
    assert "detect" in seen[0].layer_seconds


def test_metrics_hook_records_lenient_degrade(tmp_path: Path) -> None:
    seen: list[PipelineMetrics] = []
    pipeline = _pipeline(BoomEngine(), seen.append)
    pipeline.run(_docx(tmp_path / "a.docx"), LoadOptions(strict=False))
    assert len(seen) == 1
    assert seen[0].ok is False
    assert seen[0].error is not None
    assert seen[0].engine is None


def test_raising_metrics_hook_does_not_break_pipeline(tmp_path: Path) -> None:
    def bad_hook(_: PipelineMetrics) -> None:
        raise ValueError("hook failed")

    pipeline = _pipeline(OkEngine(), bad_hook)
    doc = pipeline.run(_docx(tmp_path / "a.docx"))  # must not raise
    assert doc.text == "raw"


def test_metrics_records_non_viparse_bug(tmp_path: Path) -> None:
    """A plain bug (not a ViparseError) is still captured in the metrics record."""
    seen: list[PipelineMetrics] = []
    reg = EngineRegistry()
    reg.register(OkEngine())
    pipeline = Pipeline(reg, BugNormalizer(), OkRenderer(), metrics_hook=seen.append)
    with pytest.raises(KeyError):
        pipeline.run(_docx(tmp_path / "a.docx"))
    assert len(seen) == 1
    assert seen[0].ok is False
    assert seen[0].error is not None


def test_run_without_hook_still_works(tmp_path: Path) -> None:
    pipeline = _pipeline(OkEngine())
    doc = pipeline.run(_docx(tmp_path / "a.docx"))
    assert doc.text == "raw"


def test_run_emits_structured_log(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    pipeline = _pipeline(OkEngine())
    with caplog.at_level(logging.INFO, logger="viparse"):
        pipeline.run(_docx(tmp_path / "a.docx"))
    messages = [r.getMessage() for r in caplog.records]
    assert any("viparse.load" in m and "engine=ok" in m for m in messages)
