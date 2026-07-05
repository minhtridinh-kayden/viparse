"""Guards against hostile input (SPEC-8 E8.3).

viparse ingests untrusted documents, so a file is checked *before* it is parsed:

- :func:`check_file_size` rejects an oversized file (the coarse first line of defence);
- :func:`check_zip_bomb` rejects an OOXML container that decompresses past a hard ceiling
  — a zip bomb — before any engine hands it to a parser.

Both raise :class:`~viparse.errors.UnsafeInput` so the caller fails fast with a clear
error instead of exhausting memory. Path traversal is not a concern here: viparse never
*extracts* zip members by name (the engines read specific parts through their libraries).
Entity-expansion (billion-laughs / XXE) inside the OOXML XML is bounded by these size
limits and the per-engine process timeouts; deeper parser-level hardening rides on the
maintained parse libraries (golden rule: swap the adapter on a CVE).
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from viparse.detect import CONTENT_TYPE_DOCX, CONTENT_TYPE_PPTX, CONTENT_TYPE_XLSX
from viparse.errors import UnsafeInput
from viparse.protocols import Source

_MAX_UNCOMPRESSED_BYTES = 1024 * 1024 * 1024  # 1 GiB total decompressed — well above real docs
_PROBE_CHUNK = 1024 * 1024  # decompress in 1 MiB chunks so a bomb never lands in memory

_OOXML_TYPES = frozenset({CONTENT_TYPE_DOCX, CONTENT_TYPE_XLSX, CONTENT_TYPE_PPTX})


def check_file_size(source: Source, max_bytes: int) -> None:
    """Reject a source file larger than ``max_bytes`` before any parsing happens."""
    size = Path(source).stat().st_size
    if size > max_bytes:
        raise UnsafeInput(
            f"input is {size} bytes, over the {max_bytes}-byte limit ({Path(source)!s})"
        )


def check_zip_bomb(source: Source, content_type: str) -> None:
    """Reject an OOXML container that decompresses past :data:`_MAX_UNCOMPRESSED_BYTES`.

    A no-op for non-OOXML content. Each entry is *actually* decompressed, but in bounded
    chunks with a running total — so the check measures the real expansion (declared ZIP
    sizes are attacker-controlled and cannot be trusted) yet never buffers a bomb in memory,
    aborting the moment the ceiling is crossed.
    """
    if content_type not in _OOXML_TYPES:
        return
    total = 0
    with zipfile.ZipFile(Path(source)) as zf:
        for info in zf.infolist():
            with zf.open(info) as stream:
                while chunk := stream.read(_PROBE_CHUNK):
                    total += len(chunk)
                    if total > _MAX_UNCOMPRESSED_BYTES:
                        raise UnsafeInput(
                            f"OOXML decompresses past the {_MAX_UNCOMPRESSED_BYTES}-byte "
                            f"limit ({Path(source)!s})"
                        )
