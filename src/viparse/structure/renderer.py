"""Renderers: turn a :class:`NormalizedDoc` into the public :class:`Document`.

Three output formats share one metadata projection (SPEC-4 E4.1):

- ``text`` — the normalized flat text, already Unicode NFC (T4.1.1);
- ``markdown`` — headings as ``#``, tables as GFM pipe tables (T4.1.2);
- ``json`` — a stable, versioned block structure plus metadata (T4.1.3).

Markdown/JSON are driven by :attr:`NormalizedDoc.blocks`; when the engine supplied
no block structure the whole text is treated as a single paragraph, so every format
still round-trips a block-less document.
"""

from __future__ import annotations

import json
from typing import Any

from viparse.model import (
    SCHEMA_VERSION,
    Block,
    Document,
    DocumentMetadata,
    Heading,
    NormalizedDoc,
    Table,
    blocks_of,
)
from viparse.options import DEFAULT_OUTPUT_FORMAT, OutputFormat

_MAX_HEADING_LEVEL = 6  # Markdown/HTML have no heading deeper than <h6>.


class DocumentRenderer:
    """Serializes a normalized document to text, markdown, or JSON."""

    def render(self, doc: NormalizedDoc, fmt: OutputFormat = DEFAULT_OUTPUT_FORMAT) -> Document:
        if fmt == "text":
            body = _render_text(doc)
        elif fmt == "markdown":
            body = _render_markdown(doc)
        else:
            body = _render_json(doc)
        return Document(text=body, metadata=_metadata(doc))


def _provenance(doc: NormalizedDoc) -> dict[str, Any]:
    """The shared provenance/detection fields, used by both metadata and JSON output."""
    return {
        "source": doc.source,
        "content_type": doc.content_type,
        "page": doc.page,
        "sheet": doc.sheet,
        "lang": doc.lang,
        "encoding_detected": doc.encoding_detected,
        "encoding_confidence": doc.encoding_confidence,
        "engine": doc.engine,
        "warnings": list(doc.warnings),
    }


def _metadata(doc: NormalizedDoc) -> DocumentMetadata:
    """Project the normalizer's detection results onto the public metadata schema."""
    return DocumentMetadata(**_provenance(doc))


def _clamp_level(level: int) -> int:
    """Constrain a heading level to the renderable/HTML range ``[1, 6]``."""
    return min(max(level, 1), _MAX_HEADING_LEVEL)


def _render_text(doc: NormalizedDoc) -> str:
    """Plain text is the already-normalized flat text (T4.1.1)."""
    return doc.text


def _render_markdown(doc: NormalizedDoc) -> str:
    """Render blocks to markdown, preserving headings and tables (T4.1.2)."""
    parts: list[str] = []
    for block in blocks_of(doc):
        if isinstance(block, Heading):
            parts.append(f"{'#' * _clamp_level(block.level)} {block.text}")
        elif isinstance(block, Table):
            table = _render_table(block.rows)
            if table:
                parts.append(table)
        else:
            parts.append(block.text)
    return "\n\n".join(parts)


def _render_table(rows: list[list[str]]) -> str:
    """Render rows as a GFM pipe table; the first row is the header. Empty → ``""``."""
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    rendered = [_render_row(row, width) for row in rows]
    separator = "| " + " | ".join(["---"] * width) + " |"
    return "\n".join([rendered[0], separator, *rendered[1:]])


def _render_row(cells: list[str], width: int) -> str:
    """Render one table row, padding to ``width`` and escaping GFM cell syntax."""
    padded = cells + [""] * (width - len(cells))
    return "| " + " | ".join(_escape_cell(cell) for cell in padded) + " |"


def _escape_cell(text: str) -> str:
    """Escape characters that would break a GFM table cell (pipes, line breaks)."""
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("\n", "<br>")


def _render_json(doc: NormalizedDoc) -> str:
    """Render a stable, versioned JSON payload of blocks + metadata (T4.1.3)."""
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        **_provenance(doc),
        "blocks": [_block_to_dict(block) for block in blocks_of(doc)],
    }
    # ensure_ascii=False keeps Vietnamese characters literal (and NFC) in the output.
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _block_to_dict(block: Block) -> dict[str, Any]:
    """Map a typed block to its JSON object form."""
    if isinstance(block, Heading):
        return {"type": "heading", "level": _clamp_level(block.level), "text": block.text}
    if isinstance(block, Table):
        return {"type": "table", "rows": block.rows}
    return {"type": "paragraph", "text": block.text}
