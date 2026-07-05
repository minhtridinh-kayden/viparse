"""Helpers shared by the extraction engines (not part of the public API).

Engines emit the same block-dict shape into ``RawExtraction.signals["blocks"]``
(``{type: "heading"|"paragraph", ...}`` and ``{type: "table", rows}``); this module
holds the logic that is identical across adapters so it stays in one place.
"""

from __future__ import annotations

from typing import Any


def blocks_to_text(blocks: list[dict[str, Any]]) -> str:
    """Flatten ordered blocks into plain text (tables as tab-separated rows).

    This is the engine's own flat representation of ``RawExtraction.text``; the
    normalizer converts/cleans it (it never re-derives it from the blocks).
    """
    lines: list[str] = []
    for block in blocks:
        if block["type"] == "table":
            lines.extend("\t".join(row) for row in block["rows"])
        else:
            lines.append(block["text"])
    return "\n".join(lines)
