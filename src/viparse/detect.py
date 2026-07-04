"""Format detection by magic bytes (the ``route`` layer's first step).

Detection is based on the real bytes of the file, never its extension. Modern
Office files (docx/xlsx/pptx) are ZIP containers distinguished by their internal
entries; PDFs start with ``%PDF-``; legacy ``.doc``/``.xls`` are OLE2 compound
documents.

This layer only names the *container*. It deliberately does **not** hand-roll a
compound-file parser to tell ``.doc`` from ``.xls`` (an order-dependent byte scan
misclassifies files with embedded objects and misses older BIFF variants) nor a
PDF parser to decide scanned-vs-digital. Those precise determinations belong to
the extraction engines (S2), which use maintained libraries. For PDFs we offer a
cheap, conservative *hint* only.
"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from viparse.errors import UnsupportedFormat
from viparse.protocols import Source

# --- Content types --------------------------------------------------------
CONTENT_TYPE_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
CONTENT_TYPE_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
CONTENT_TYPE_PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
CONTENT_TYPE_PDF = "application/pdf"
# Legacy OLE2 compound document (.doc/.xls). The engine resolves the exact kind
# (msword vs ms-excel) with a real compound-file library.
CONTENT_TYPE_OLE2 = "application/x-ole-storage"

# --- Magic signatures -----------------------------------------------------
_ZIP_MAGIC = b"PK\x03\x04"
_PDF_MAGIC = b"%PDF-"
_OLE2_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"

# How far to read past the header when sniffing the PDF text hint. This is a
# best-effort window; a miss just yields an unknown hint, never a wrong one.
_PDF_SCAN_WINDOW = 1 << 16


@dataclass(frozen=True, slots=True)
class DetectedFormat:
    """The detected format of a source file.

    ``is_scanned_pdf`` is a conservative hint for PDFs: ``False`` when a text
    layer is positively detected, otherwise ``None`` (unknown / not a PDF). The
    cheap detector never asserts ``True`` — only the PDF engine, which parses the
    document, can reliably conclude a PDF is scanned.
    """

    content_type: str
    is_scanned_pdf: bool | None = None


def detect_format(source: Source) -> DetectedFormat:
    """Detect the format of ``source`` from its magic bytes.

    Raises :class:`~viparse.errors.UnsupportedFormat` if the bytes match no
    supported format.
    """
    path = Path(source)
    with path.open("rb") as fh:
        header = fh.read(8)
        if header.startswith(_PDF_MAGIC):
            window = header + fh.read(_PDF_SCAN_WINDOW)
            return DetectedFormat(CONTENT_TYPE_PDF, is_scanned_pdf=_pdf_scanned_hint(window))
        if header.startswith(_OLE2_MAGIC):
            return DetectedFormat(CONTENT_TYPE_OLE2)
        if header.startswith(_ZIP_MAGIC):
            fh.seek(0)
            return DetectedFormat(_classify_zip(fh, path))
    raise UnsupportedFormat(f"unrecognized format for {path!s} (magic bytes {header[:4]!r})")


def _classify_zip(fh: BinaryIO, path: Path) -> str:
    """Classify an already-open ZIP container by its OOXML entries."""
    try:
        # ``fh`` was passed in, so ZipFile will not close it — the caller owns it.
        with zipfile.ZipFile(fh) as zf:
            names = set(zf.namelist())
    except zipfile.BadZipFile as exc:
        raise UnsupportedFormat(f"corrupt ZIP container: {path!s}") from exc
    if "word/document.xml" in names:
        return CONTENT_TYPE_DOCX
    if "xl/workbook.xml" in names:
        return CONTENT_TYPE_XLSX
    if "ppt/presentation.xml" in names:
        return CONTENT_TYPE_PPTX
    raise UnsupportedFormat(f"ZIP container is not a recognized OOXML document: {path!s}")


def _pdf_scanned_hint(window: bytes) -> bool | None:
    """Conservative digital-vs-scanned hint for a PDF from a prefix window.

    Returns ``False`` when a font reference (a text layer) is seen, else ``None``
    (unknown). It never returns ``True``: image XObjects alone do not prove a
    document is scanned (Form XObjects, logos, and watermarks appear in digital
    PDFs too), and asserting ``True`` would wrongly force expensive OCR. The PDF
    engine makes the real determination.
    """
    if b"/Font" in window:
        return False
    return None
