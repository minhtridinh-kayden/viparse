"""Tests for the scanned-PDF OCR adapter.

The external OCR stack (pytesseract/pdf2image + the Tesseract/poppler binaries) is
mocked so the adapter logic is covered deterministically without those heavy, non-pip
dependencies. Page images are real Pillow images, so the preprocessing runs for real.
"""

from __future__ import annotations

import sys
import types

import pytest
from PIL import Image

from viparse.detect import CONTENT_TYPE_PDF
from viparse.engines.ocr import OcrEngine
from viparse.errors import ExtractionError, MissingDependency
from viparse.options import LoadOptions


class _TesseractNotFound(Exception):
    pass


class _PDFInfoNotInstalled(Exception):
    pass


def _page(words_and_confs: list[tuple[str, int]]) -> dict[str, list]:
    """A pytesseract image_to_data DICT for one page (parallel text/conf lists)."""
    return {
        "text": [word for word, _ in words_and_confs],
        "conf": [conf for _, conf in words_and_confs],
    }


def _install(
    monkeypatch: pytest.MonkeyPatch,
    *,
    pages: list[dict[str, list]] | None = None,
    convert_error: Exception | None = None,
    data_error: Exception | None = None,
) -> None:
    calls = {"i": 0}

    def image_to_data(
        image: object, lang: str, timeout: int, output_type: object
    ) -> dict[str, list]:
        if data_error is not None:
            raise data_error
        assert pages is not None
        page = pages[calls["i"]]
        calls["i"] += 1
        return page

    pytesseract = types.SimpleNamespace(
        image_to_data=image_to_data,
        Output=types.SimpleNamespace(DICT="dict"),
        TesseractNotFoundError=_TesseractNotFound,
    )

    def convert_from_path(path: str, dpi: int) -> list[Image.Image]:
        if convert_error is not None:
            raise convert_error
        count = len(pages) if pages is not None else 1
        return [Image.new("RGB", (8, 8), "white") for _ in range(count)]

    pdf2image = types.SimpleNamespace(
        convert_from_path=convert_from_path,
        exceptions=types.SimpleNamespace(PDFInfoNotInstalledError=_PDFInfoNotInstalled),
    )
    monkeypatch.setitem(sys.modules, "pytesseract", pytesseract)
    monkeypatch.setitem(sys.modules, "pdf2image", pdf2image)


def test_extract_ocrs_pages_into_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, pages=[_page([("Tiếng", 95), ("Việt", 90), ("", -1)])])
    raw = OcrEngine().extract("scan.pdf", LoadOptions())
    assert raw.engine == "ocr"
    assert raw.content_type == CONTENT_TYPE_PDF
    assert raw.signals["blocks"] == [{"type": "paragraph", "text": "Tiếng Việt"}]
    assert raw.signals["fonts"] == []  # OCR output carries no legacy font signal
    assert raw.warnings == []


def test_low_confidence_pages_warn(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, pages=[_page([("mờ", 40), ("nhòe", 45)])])
    raw = OcrEngine().extract("scan.pdf", LoadOptions())
    assert raw.text == "mờ nhòe"
    assert any("confidence" in w for w in raw.warnings)


def test_blank_words_with_confidence_are_dropped(monkeypatch: pytest.MonkeyPatch) -> None:
    # Tesseract can report a whitespace token with a real confidence; it counts toward
    # the confidence average but must not appear in the text.
    _install(monkeypatch, pages=[_page([("Có", 95), ("   ", 80)])])
    raw = OcrEngine().extract("scan.pdf", LoadOptions())
    assert raw.signals["blocks"] == [{"type": "paragraph", "text": "Có"}]


def test_empty_pages_are_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(
        monkeypatch,
        pages=[_page([("Trang", 88)]), _page([("", -1), ("  ", -1)])],
    )
    raw = OcrEngine().extract("scan.pdf", LoadOptions())
    assert raw.signals["blocks"] == [{"type": "paragraph", "text": "Trang"}]


def test_missing_python_libraries_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "pytesseract", None)
    with pytest.raises(MissingDependency, match=r"viparse\[ocr\]"):
        OcrEngine().extract("scan.pdf", LoadOptions())


def test_missing_tesseract_binary_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, pages=[_page([("x", 90)])], data_error=_TesseractNotFound())
    with pytest.raises(MissingDependency, match=r"tesseract-ocr"):
        OcrEngine().extract("scan.pdf", LoadOptions())


def test_missing_poppler_binary_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, convert_error=_PDFInfoNotInstalled())
    with pytest.raises(MissingDependency, match=r"poppler"):
        OcrEngine().extract("scan.pdf", LoadOptions())


def test_ocr_timeout_raises_extraction_error(monkeypatch: pytest.MonkeyPatch) -> None:
    # pytesseract raises RuntimeError on the per-page Tesseract timeout.
    _install(monkeypatch, pages=[_page([("x", 90)])], data_error=RuntimeError("Tesseract timeout"))
    with pytest.raises(ExtractionError, match="timed out"):
        OcrEngine().extract("scan.pdf", LoadOptions())


def test_supports_only_pdf() -> None:
    engine = OcrEngine()
    assert engine.supports(CONTENT_TYPE_PDF)
    assert not engine.supports(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


def test_marks_output_native_unicode(monkeypatch: pytest.MonkeyPatch) -> None:
    # So the normalizer skips encoding detection (OCR output is already Unicode).
    _install(monkeypatch, pages=[_page([("chào", 90)])])
    raw = OcrEngine().extract("scan.pdf", LoadOptions())
    assert raw.signals["native_unicode"] is True


def test_is_marked_as_an_ocr_engine() -> None:
    # The pipeline keys off this to run OCR only when options.ocr is True.
    assert OcrEngine.ocr is True
