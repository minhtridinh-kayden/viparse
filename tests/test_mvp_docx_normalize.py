"""MVP integration: DOCX extraction → Vietnamese normalization (extract → normalize seam)."""

from __future__ import annotations

import unicodedata
from pathlib import Path

import pytest

from viparse.engines.docx import DocxEngine
from viparse.normalize.normalizer import VietnameseNormalizer
from viparse.options import LoadOptions

docx = pytest.importorskip("docx")  # python-docx; skipped without the office extra


def test_docx_tcvn3_extracts_then_normalizes_to_unicode(tmp_path: Path) -> None:
    document = docx.Document()
    run = document.add_paragraph().add_run("µ¸¶·¹")  # TCVN3 surface characters
    run.font.name = ".VnTime"
    path = tmp_path / "legacy.docx"
    document.save(str(path))

    raw = DocxEngine().extract(path, LoadOptions())
    assert ".VnTime" in raw.signals["fonts"]

    nd = VietnameseNormalizer().normalize(raw, LoadOptions())
    assert nd.encoding_detected == "tcvn3"
    assert "àáảãạ" in nd.text
    assert unicodedata.is_normalized("NFC", nd.text)
