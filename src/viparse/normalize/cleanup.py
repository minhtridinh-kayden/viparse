"""Vietnamese text cleanup: strip junk, normalize whitespace, keep block structure.

Runs after encoding conversion + NFC. It is deliberately conservative so it never
corrupts Vietnamese text or the structure the extraction engine marked:

- **line breaks** separate blocks (headings/paragraphs/table rows) → preserved;
- **tabs** separate table cells → preserved;
- only *horizontal* whitespace inside a line is collapsed, control/format
  characters are stripped, and blank-line runs are capped.

Aggressive de-hyphenation (SPEC-3 T3.4.2) is intentionally deferred: DOCX
paragraphs are not line-wrapped, so joining across a block boundary would merge
distinct paragraphs. It belongs with the line-wrapping PDF engine (M2).
"""

from __future__ import annotations

import re
import unicodedata

from viparse.options import NormalizeForm

# Horizontal whitespace only — excludes tab (cell separator) and newline (block
# separator), which carry structure the engine marked.
_HORIZONTAL_WS = re.compile(r"[^\S\t\n]+")
_BLANK_RUN = re.compile(r"\n{3,}")
# Control characters that mark a break rather than junk — form feed (page break)
# and vertical tab. Mapped to a newline so adjacent blocks stay separated instead
# of being silently glued together when the char is stripped.
_LINE_BREAKING_CONTROLS = str.maketrans({"\x0c": "\n", "\x0b": "\n"})


def _strip_control_chars(text: str) -> str:
    """Drop control (Cc) and format (Cf) characters, keeping tab and newline."""
    return "".join(
        ch for ch in text if ch in "\t\n" or unicodedata.category(ch) not in ("Cc", "Cf")
    )


def clean_text(text: str, normalize_form: NormalizeForm = "NFC") -> str:
    """Normalize whitespace and strip junk characters, preserving block structure.

    Stripping format (Cf) characters can un-block a base letter + combining mark
    that a stray zero-width/formatting character was keeping apart, so the text is
    re-normalized to ``normalize_form`` (default NFC) as the final step.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.translate(_LINE_BREAKING_CONTROLS)
    text = _strip_control_chars(text)
    lines = [_HORIZONTAL_WS.sub(" ", line).strip(" ") for line in text.split("\n")]
    joined = _BLANK_RUN.sub("\n\n", "\n".join(lines))
    return unicodedata.normalize(normalize_form, joined.strip("\n"))
