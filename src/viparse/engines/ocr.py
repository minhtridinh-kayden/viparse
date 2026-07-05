"""Scanned-PDF OCR adapter, wrapping ``pdf2image`` + ``pytesseract`` (extra ``viparse[ocr]``).

A scanned PDF has no text layer, so the digital :class:`~viparse.engines.pdf.PdfEngine`
yields nothing. This engine rasterizes each page, converts it to grayscale, and OCRs it
with the ``vie`` model, emitting one paragraph block per page plus a low-confidence
warning. Binarization is deliberately left to Tesseract's own adaptive thresholding — a
naive global threshold can crush the faint, thin Vietnamese tone marks this product
exists to preserve (adaptive/deskew preprocessing is a future refinement). The
recognized text is already Unicode, so it carries no font signal and the engine marks it
``native_unicode`` — the moat downstream only has to enforce NFC. No Vietnamese logic
lives here.

It is **heavy** (raster + OCR) and only meaningful for scanned input, so the pipeline
runs it solely when the caller sets ``options.ocr=True`` (CLI ``--ocr``). Both Python
libraries and the underlying Tesseract/poppler binaries are required only at call time;
their absence raises a clear :class:`~viparse.errors.MissingDependency`.
"""

from __future__ import annotations

from typing import Any

from viparse.detect import CONTENT_TYPE_PDF
from viparse.engines._shared import blocks_to_text
from viparse.errors import MissingDependency
from viparse.model import RawExtraction
from viparse.options import LoadOptions
from viparse.protocols import DEFAULT_PRIORITY, Source

_DPI = 300  # a good balance of OCR accuracy and speed for text documents
_LOW_OCR_CONFIDENCE = 60.0  # Tesseract word confidence is 0-100; below this is weak

_INSTALL_HINT = (
    "OCR needs pytesseract + pdf2image and the Tesseract/poppler binaries; install with: "
    "pip install 'viparse[ocr]' plus the system packages tesseract-ocr tesseract-ocr-vie poppler"
)


def _import_ocr() -> tuple[Any, Any]:
    """Import ``pytesseract`` and ``pdf2image`` lazily, raising a clear error if missing."""
    try:
        import pdf2image
        import pytesseract
    except ImportError as exc:
        raise MissingDependency(_INSTALL_HINT) from exc
    return pytesseract, pdf2image


class OcrEngine:
    """OCRs a scanned ``.pdf`` into one text block per page, with a confidence signal."""

    #: Below the digital PDF engine's baseline — though selection is really governed by
    #: :meth:`Pipeline._select_by_ocr`, which runs OCR only when ``options.ocr`` is True.
    priority = DEFAULT_PRIORITY - 10
    #: Dependency + extra reported by ``viparse doctor``.
    dependency = "pytesseract"
    extra = "ocr"
    #: Marks this as an OCR engine; the pipeline only selects it when ``options.ocr`` is True.
    ocr = True

    def supports(self, content_type: str) -> bool:
        return content_type == CONTENT_TYPE_PDF

    def extract(self, source: Source, options: LoadOptions) -> RawExtraction:
        pytesseract, pdf2image = _import_ocr()
        binary_missing = (
            pytesseract.TesseractNotFoundError,
            pdf2image.exceptions.PDFInfoNotInstalledError,
        )
        try:
            images = pdf2image.convert_from_path(str(source), dpi=_DPI)
            pages = [_ocr_page(pytesseract, image) for image in images]
        except binary_missing as exc:
            raise MissingDependency(_INSTALL_HINT) from exc

        blocks: list[dict[str, Any]] = []
        weak_pages = 0
        for text, confidence in pages:
            if not text:
                continue
            blocks.append({"type": "paragraph", "text": text})
            if confidence < _LOW_OCR_CONFIDENCE:
                weak_pages += 1
        warnings: list[str] = []
        if weak_pages:
            warnings.append(
                f"{weak_pages} page(s) OCR'd below {_LOW_OCR_CONFIDENCE:.0f}% confidence; "
                "the text may contain recognition errors"
            )
        return RawExtraction(
            source=str(source),
            content_type=CONTENT_TYPE_PDF,
            text=blocks_to_text(blocks),
            engine="ocr",
            # OCR output is Unicode with no font: no legacy-encoding question, so mark it
            # so the normalizer does not emit a spurious low-confidence encoding warning.
            signals={"fonts": [], "blocks": blocks, "native_unicode": True},
            warnings=warnings,
        )


def _ocr_page(pytesseract: Any, image: Any) -> tuple[str, float]:
    """OCR one page image (grayscale), returning its text and mean word confidence."""
    data = pytesseract.image_to_data(
        image.convert("L"), lang="vie", output_type=pytesseract.Output.DICT
    )
    words: list[str] = []
    confidences: list[float] = []
    for word, raw_conf in zip(data["text"], data["conf"], strict=True):
        conf = float(raw_conf)
        if conf < 0:  # Tesseract marks non-text regions with conf == -1
            continue
        confidences.append(conf)
        if word.strip():
            words.append(word)
    text = " ".join(words)
    confidence = sum(confidences) / len(confidences) if confidences else 0.0
    return text, confidence
