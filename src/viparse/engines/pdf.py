"""Digital PDF extraction adapter, wrapping ``pdfplumber`` (extra ``viparse[pdf]``).

For each page the engine extracts the body text (excluding any table regions, so a
table's cells are not duplicated in the surrounding prose), each detected table as a
structured block, and every glyph's font name as a signal for the S3 detector (e.g.
``.VnTime`` → TCVN3). It applies no Vietnamese logic itself.

``pdfplumber`` is imported lazily inside :meth:`PdfEngine.extract`, so importing this
module never requires the dependency; only extraction does. This engine handles
**digital** PDFs (those with a text layer); scanned PDFs are the OCR engine's job (M3),
and a text-less page here simply yields no blocks.
"""

from __future__ import annotations

from typing import Any

from viparse.detect import CONTENT_TYPE_PDF
from viparse.engines._shared import blocks_to_text
from viparse.errors import MissingDependency
from viparse.model import RawExtraction
from viparse.options import LoadOptions
from viparse.protocols import DEFAULT_PRIORITY, Source

_INSTALL_HINT = (
    "pdfplumber is required for PDF extraction; install it with: pip install 'viparse[pdf]'"
)


def _import_pdfplumber() -> Any:
    """Import ``pdfplumber`` lazily, raising a clear error if it is missing."""
    try:
        import pdfplumber
    except ImportError as exc:
        raise MissingDependency(_INSTALL_HINT) from exc
    return pdfplumber


class PdfEngine:
    """Extracts ordered text, fonts, and tables from a digital ``.pdf`` file."""

    priority = DEFAULT_PRIORITY
    #: Dependency + extra reported by ``viparse doctor``.
    dependency = "pdfplumber"
    extra = "pdf"

    def supports(self, content_type: str) -> bool:
        return content_type == CONTENT_TYPE_PDF

    def extract(self, source: Source, options: LoadOptions) -> RawExtraction:
        pdfplumber = _import_pdfplumber()
        blocks: list[dict[str, Any]] = []
        fonts: set[str] = set()
        with pdfplumber.open(str(source)) as pdf:
            page_count = len(pdf.pages)
            for page in pdf.pages:
                page_blocks, page_fonts = _page_blocks(page)
                blocks.extend(page_blocks)
                fonts.update(page_fonts)
        # Record the page on metadata only for a single-page document; multi-page
        # provenance belongs with per-block/per-chunk metadata (later).
        page_number = 1 if page_count == 1 else None
        return RawExtraction(
            source=str(source),
            content_type=CONTENT_TYPE_PDF,
            text=blocks_to_text(blocks),
            engine="pdf",
            page=page_number,
            signals={"fonts": sorted(fonts), "blocks": blocks},
        )


def _page_blocks(page: Any) -> tuple[list[dict[str, Any]], set[str]]:
    """Extract one page into (blocks, font names), preserving top-to-bottom order.

    The page is scanned top to bottom: text in each vertical *band* between tables is
    emitted as a paragraph and each table as a table block, so a page laid out as
    ``[table][prose]`` keeps that order (rather than always emitting prose first). Text
    in a band is read from a vertical crop, so a table's cells never leak into the prose.
    """
    fonts = {char["fontname"] for char in page.chars}
    fonts.discard(None)
    tables = sorted(page.find_tables(), key=lambda table: table.bbox[1])
    blocks: list[dict[str, Any]] = []
    cursor = 0.0
    for table in tables:
        _top, bottom = table.bbox[1], table.bbox[3]
        _append_band(page, cursor, _top, blocks)
        blocks.append({"type": "table", "rows": _table_rows(table)})
        cursor = bottom
    _append_band(page, cursor, page.height, blocks)
    return blocks, fonts


def _append_band(page: Any, top: float, bottom: float, blocks: list[dict[str, Any]]) -> None:
    """Append a paragraph block for the text in the page's ``[top, bottom]`` vertical band."""
    if bottom - top < 1:  # no meaningful vertical space (e.g. a table flush to an edge)
        return
    text = (page.crop((0, top, page.width, bottom)).extract_text() or "").strip()
    if text:
        blocks.append({"type": "paragraph", "text": text})


def _table_rows(table: Any) -> list[list[str]]:
    """A pdfplumber table's cells as single-line strings (``None`` empties → ``""``).

    Intra-cell whitespace (including newlines from text that wraps inside a cell) is
    collapsed to single spaces, so a wrapped cell can't split a row when the block is
    later flattened to tab-separated text.
    """
    return [
        ["" if cell is None else " ".join(cell.split()) for cell in row] for row in table.extract()
    ]
