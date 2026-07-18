"""RTF extraction adapter, wrapping ``striprtf`` (extra ``viparse[rtf]``).

``striprtf`` turns the RTF control stream into plain text — resolving ``\\'XX`` escapes,
code pages, and ``\\par`` breaks. This adapter is deliberately **text-only**: it does not
lift the RTF font table as an encoding signal. An RTF font table lists the fonts a
document *declares*, not the fonts actually *applied* to text (templates routinely declare
a legacy ``.Vn*`` font while writing Unicode), and striprtf flattens the document, so the
best a font signal could be is document-wide — which would convert an entire mixed or
Unicode body through one legacy charmap and corrupt good text (the moat's cardinal sin,
and exactly the whole-document pitfall the per-block/per-run work removed for DOCX).

A legacy-encoded ``.rtf`` is therefore normalized like any other font-less source: via
content-based detection (``encoding="auto"``) or an explicit ``encoding=`` override. The
engine applies no Vietnamese logic itself.

``striprtf`` is imported lazily inside :meth:`RtfEngine.extract`, so importing this module
never requires the dependency; only extraction does.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from viparse.detect import CONTENT_TYPE_RTF
from viparse.engines._shared import blocks_to_text
from viparse.errors import MissingDependency
from viparse.model import RawExtraction
from viparse.options import LoadOptions
from viparse.protocols import DEFAULT_PRIORITY, Source

_INSTALL_HINT = (
    "striprtf is required for RTF extraction; install it with: pip install 'viparse[rtf]'"
)


def _import_rtf_to_text() -> Any:
    """Import ``striprtf.rtf_to_text`` lazily, raising a clear error if it is missing."""
    try:
        from striprtf.striprtf import rtf_to_text
    except ImportError as exc:
        raise MissingDependency(_INSTALL_HINT) from exc
    return rtf_to_text


class RtfEngine:
    """Extracts plain text and paragraph blocks from a ``.rtf`` file."""

    priority = DEFAULT_PRIORITY
    #: Import name of the parse library this engine needs, and the extra that ships it —
    #: read by ``viparse doctor`` to report availability.
    dependency = "striprtf"
    extra = "rtf"

    def supports(self, content_type: str) -> bool:
        return content_type == CONTENT_TYPE_RTF

    def extract(self, source: Source, options: LoadOptions) -> RawExtraction:
        rtf_to_text = _import_rtf_to_text()
        # RTF is an ASCII control stream (high bytes appear as ``\'XX`` escapes), so a
        # byte-preserving latin-1 decode is lossless and lets striprtf resolve the rest.
        raw = Path(str(source)).read_bytes().decode("latin-1")
        text: str = rtf_to_text(raw, errors="ignore")
        blocks: list[dict[str, Any]] = [
            {"type": "paragraph", "text": line} for line in text.splitlines() if line.strip()
        ]
        return RawExtraction(
            source=str(source),
            content_type=CONTENT_TYPE_RTF,
            text=blocks_to_text(blocks),
            engine="rtf",
            signals={"blocks": blocks},
        )
