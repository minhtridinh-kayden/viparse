"""Legacy binary ``.doc``/``.xls`` adapter, via headless LibreOffice (extra ``viparse[office]``).

Old OLE2 compound documents (Word 97-2003 ``.doc``, Excel 97-2003 ``.xls``) are detected
generically as :data:`~viparse.detect.CONTENT_TYPE_OLE2`. This engine uses ``olefile`` to
tell a Word document from a spreadsheet (by its internal streams), converts it to the
modern ``.docx``/``.xlsx`` with headless LibreOffice, then delegates to the existing
:class:`~viparse.engines.docx.DocxEngine` / :class:`~viparse.engines.xlsx.XlsxEngine`. No
binary format is parsed by hand; legacy Vietnamese fonts survive the conversion, so the
S3 moat still applies downstream.

``olefile`` is a lazy import and LibreOffice is an external ``soffice`` binary; either
being absent raises a clear :class:`~viparse.errors.MissingDependency`. The conversion
runs with a timeout and its temporary files are always cleaned up.
"""

from __future__ import annotations

import subprocess
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Any

from viparse.detect import CONTENT_TYPE_OLE2
from viparse.engines.docx import DocxEngine
from viparse.engines.xlsx import XlsxEngine
from viparse.errors import ExtractionError, MissingDependency
from viparse.model import RawExtraction
from viparse.options import LoadOptions
from viparse.protocols import DEFAULT_PRIORITY, Source

_SOFFICE = "soffice"
_TIMEOUT_SECONDS = 120

_INSTALL_HINT = (
    "legacy .doc/.xls need the olefile package and a LibreOffice install; install with: "
    "pip install 'viparse[office]' plus the system package libreoffice (the 'soffice' binary)"
)

# OLE2 stream names that identify the document kind, mapped to (target extension, engine).
_WORD_STREAMS = frozenset({"WordDocument"})
_EXCEL_STREAMS = frozenset({"Workbook", "Book"})


def _import_olefile() -> Any:
    """Import ``olefile`` lazily, raising a clear error if it is missing."""
    try:
        import olefile
    except ImportError as exc:
        raise MissingDependency(_INSTALL_HINT) from exc
    return olefile


class LegacyOfficeEngine:
    """Converts a legacy ``.doc``/``.xls`` and delegates to the modern-format engine."""

    priority = DEFAULT_PRIORITY
    #: Reported by ``viparse doctor``: the olefile pip package and the external soffice binary.
    dependency = "olefile"
    extra = "office"
    binary = "soffice"

    def supports(self, content_type: str) -> bool:
        return content_type == CONTENT_TYPE_OLE2

    def extract(self, source: Source, options: LoadOptions) -> RawExtraction:
        olefile = _import_olefile()
        target, delegate = _classify(olefile, source)
        with tempfile.TemporaryDirectory(prefix="viparse-") as tmp:
            converted = _convert(source, target, tmp)
            raw = delegate.extract(converted, options)
        # Re-stamp provenance onto the original legacy file (the modern temp file is gone).
        return replace(
            raw, source=str(source), content_type=CONTENT_TYPE_OLE2, engine="libreoffice"
        )


def _classify(olefile: Any, source: Source) -> tuple[str, DocxEngine | XlsxEngine]:
    """Determine (target extension, delegate engine) from the OLE2 document's streams."""
    streams = _ole_streams(olefile, source)
    if streams & _WORD_STREAMS:
        return "docx", DocxEngine()
    if streams & _EXCEL_STREAMS:
        return "xlsx", XlsxEngine()
    raise ExtractionError(f"unrecognized OLE2 document (streams: {sorted(streams)}): {source!s}")


def _ole_streams(olefile: Any, source: Source) -> set[str]:
    """Read the OLE2 top-level stream names, mapping any read failure to an ExtractionError.

    ``detect`` only matched the 8-byte OLE2 magic, so the container may still be truncated,
    corrupt, or password-protected — olefile would raise its own (non-viparse) exception.
    """
    ole = None
    try:
        ole = olefile.OleFileIO(str(source))
        return {entry[0] for entry in ole.listdir()}
    except Exception as exc:  # noqa: BLE001 — any olefile read failure is an extraction failure
        raise ExtractionError(f"could not read OLE2 document {source!s}: {exc}") from exc
    finally:
        if ole is not None:
            ole.close()


def _convert(source: Source, target: str, out_dir: str) -> Path:
    """Convert ``source`` to ``target`` (docx/xlsx) in ``out_dir`` via headless LibreOffice."""
    # A per-call LibreOffice user profile (inside the temp dir) isolates concurrent headless
    # invocations, which otherwise share a single instance and can silently interfere.
    profile = f"-env:UserInstallation=file://{Path(out_dir) / 'lo-profile'}"
    try:
        subprocess.run(
            [
                _SOFFICE,
                "--headless",
                profile,
                "--convert-to",
                target,
                "--outdir",
                out_dir,
                str(source),
            ],
            capture_output=True,
            timeout=_TIMEOUT_SECONDS,
            check=True,
        )
    except FileNotFoundError as exc:
        raise MissingDependency(_INSTALL_HINT) from exc
    except subprocess.TimeoutExpired as exc:
        raise ExtractionError(f"LibreOffice timed out converting {source!s}") from exc
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.decode("utf-8", "replace").strip() if exc.stderr else ""
        raise ExtractionError(f"LibreOffice failed to convert {source!s}: {detail}") from exc
    converted = Path(out_dir) / f"{Path(str(source)).stem}.{target}"
    if not converted.exists():
        raise ExtractionError(f"LibreOffice produced no output for {source!s}")
    return converted
