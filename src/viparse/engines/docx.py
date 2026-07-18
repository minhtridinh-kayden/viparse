"""DOCX extraction adapter, wrapping ``python-docx`` (extra ``viparse[office]``).

The engine walks the document body in order so headings, paragraphs, and tables
keep their original sequence, and records each run's **font name** as a signal —
that is how the S3 normalizer recognizes a legacy encoding (e.g. ``.VnTime`` →
TCVN3). It applies no Vietnamese logic itself.

``python-docx`` is imported lazily inside :meth:`DocxEngine.extract`, so importing
this module never requires the dependency; only extraction does.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from viparse.detect import CONTENT_TYPE_DOCX
from viparse.engines._shared import blocks_to_text
from viparse.errors import MissingDependency
from viparse.model import RawExtraction
from viparse.options import LoadOptions
from viparse.protocols import DEFAULT_PRIORITY, Source

_INSTALL_HINT = (
    "python-docx is required for DOCX extraction; install it with: pip install 'viparse[office]'"
)


def _import_docx() -> Any:
    """Import ``python-docx`` lazily, raising a clear error if it is missing."""
    try:
        import docx
    except ImportError as exc:
        raise MissingDependency(_INSTALL_HINT) from exc
    return docx


class DocxEngine:
    """Extracts ordered text, run fonts, and block structure from a ``.docx`` file."""

    priority = DEFAULT_PRIORITY
    #: Import name of the parse library this engine needs, and the extra that ships
    #: it — read by ``viparse doctor`` to report availability (``None`` = stdlib-only).
    dependency = "docx"
    extra = "office"

    def supports(self, content_type: str) -> bool:
        return content_type == CONTENT_TYPE_DOCX

    def extract(self, source: Source, options: LoadOptions) -> RawExtraction:
        docx = _import_docx()
        document = docx.Document(str(source))
        blocks: list[dict[str, Any]] = []
        fonts: set[str] = set()
        for kind, item in _iter_block_items(document):
            if kind == "paragraph":
                block_fonts: set[str] = set()
                _collect_fonts(item, block_fonts)
                fonts.update(block_fonts)
                block = _paragraph_block(item)
                if block is not None:
                    # Per-block font signal (SPEC-3 T3.2.4): lets the normalizer detect a
                    # mixed-encoding document and convert each block by its own encoding.
                    if block_fonts:
                        block["fonts"] = sorted(block_fonts)
                    blocks.append(block)
            else:  # table
                rows, table_fonts = _table_block(item)
                fonts.update(table_fonts)
                table_block: dict[str, Any] = {"type": "table", "rows": rows}
                if table_fonts:
                    table_block["fonts"] = sorted(table_fonts)
                blocks.append(table_block)
        signals: dict[str, Any] = {"fonts": sorted(fonts), "blocks": blocks}
        return RawExtraction(
            source=str(source),
            content_type=CONTENT_TYPE_DOCX,
            text=blocks_to_text(blocks),
            engine="docx",
            signals=signals,
        )


def _iter_block_items(document: Any) -> Iterator[tuple[str, Any]]:
    """Yield ``("paragraph"|"table", obj)`` for each body block, in document order.

    Descends into ``w:sdt`` content controls (Word form fields), whose blocks would
    otherwise be skipped — a common structure in Vietnamese government templates.
    """
    from docx.oxml.ns import qn
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    p_tag, tbl_tag, sdt_tag, content_tag = (qn("w:p"), qn("w:tbl"), qn("w:sdt"), qn("w:sdtContent"))

    def walk(parent: Any) -> Iterator[tuple[str, Any]]:
        for child in parent.iterchildren():
            if child.tag == p_tag:
                yield "paragraph", Paragraph(child, document)
            elif child.tag == tbl_tag:
                yield "table", Table(child, document)
            elif child.tag == sdt_tag:
                content = child.find(content_tag)
                if content is not None:
                    yield from walk(content)

    yield from walk(document.element.body)


def _style_font(style: Any) -> str | None:
    """Return the font name declared on a paragraph/character style, if any."""
    if style is None:
        return None
    name: str | None = style.font.name
    return name


def _collect_fonts(paragraph: Any, fonts: set[str]) -> None:
    """Add every run's font name (the S3 encoding signal) to ``fonts``.

    Legacy documents often set the font once at the paragraph or character *style*
    level rather than per run, so ``run.font.name`` is ``None``; the style fonts are
    collected too, otherwise the encoding hint would be lost.
    """
    para_font = _style_font(paragraph.style)
    if para_font:
        fonts.add(para_font)
    for run in paragraph.runs:
        if run.font.name:
            fonts.add(run.font.name)
        run_style_font = _style_font(run.style)
        if run_style_font:
            fonts.add(run_style_font)


def _run_font(run: Any, paragraph: Any) -> str | None:
    """The effective font for a run: its own, else its character style, else the paragraph's.

    Mirrors the inheritance in :func:`_collect_fonts` but resolved *per run*, so the S3
    normalizer can detect a paragraph that mixes a legacy-font run with a Unicode one.
    """
    if run.font.name:
        name: str = run.font.name
        return name
    return _style_font(run.style) or _style_font(paragraph.style)


def _paragraph_runs(paragraph: Any) -> list[dict[str, Any]]:
    """Per-run ``{text, font}`` segments whose texts concatenate back to ``paragraph.text``.

    Empty runs are dropped (they contribute nothing to the text); this keeps the segment
    list faithful so the normalizer can trust it for per-run conversion.
    """
    return [
        {"text": run.text, "font": _run_font(run, paragraph)} for run in paragraph.runs if run.text
    ]


def _paragraph_block(paragraph: Any) -> dict[str, Any] | None:
    """Map a paragraph to a heading/paragraph block, or ``None`` if empty."""
    text = paragraph.text
    style = paragraph.style.name if paragraph.style is not None else ""
    if style.startswith("Heading"):
        block: dict[str, Any] = {"type": "heading", "level": _heading_level(style), "text": text}
    elif not text.strip():
        return None
    else:
        block = {"type": "paragraph", "text": text}
    # Per-run font signal (SPEC-3 T3.2.4): lets the normalizer convert a paragraph that
    # mixes a legacy-font run with a Unicode one at run granularity, not whole-block.
    runs = _paragraph_runs(paragraph)
    if runs:
        block["runs"] = runs
    return block


def _heading_level(style_name: str) -> int:
    """Parse the level from a heading style name (``"Heading 2"`` → 2)."""
    tail = style_name.split()[-1]
    return int(tail) if tail.isdigit() else 1


def _table_block(table: Any) -> tuple[list[list[str]], set[str]]:
    """Extract a table's cell text (rows × cols) and any run fonts within it.

    Horizontally-merged cells share one underlying element and would otherwise be
    read once per spanned column; consecutive repeats are collapsed so the value
    appears a single time.
    """
    rows: list[list[str]] = []
    fonts: set[str] = set()
    for row in table.rows:
        cells: list[str] = []
        previous_tc: Any = None
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                _collect_fonts(paragraph, fonts)
            if cell._tc is previous_tc:
                continue  # part of a horizontal merge already captured
            previous_tc = cell._tc
            cells.append(cell.text)
        rows.append(cells)
    return rows, fonts
