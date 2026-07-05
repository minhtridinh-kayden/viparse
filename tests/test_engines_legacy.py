"""Tests for the legacy binary .doc/.xls adapter.

``olefile`` and the LibreOffice ``soffice`` subprocess are mocked so the adapter logic
runs deterministically without those non-pip dependencies. The mocked conversion writes
a real .docx/.xlsx, so the delegated DocxEngine/XlsxEngine extraction runs for real.
"""

from __future__ import annotations

import subprocess
import sys
import types
from pathlib import Path

import pytest

from viparse.detect import CONTENT_TYPE_OLE2
from viparse.engines.legacy import LegacyOfficeEngine
from viparse.errors import ExtractionError, MissingDependency
from viparse.options import LoadOptions

docx = pytest.importorskip("docx")
openpyxl = pytest.importorskip("openpyxl")


def _install_olefile(monkeypatch: pytest.MonkeyPatch, streams: list[str]) -> None:
    class _Ole:
        def __init__(self, path: str) -> None:
            pass

        def listdir(self) -> list[list[str]]:
            return [[name] for name in streams]

        def close(self) -> None:
            pass

    monkeypatch.setitem(sys.modules, "olefile", types.SimpleNamespace(OleFileIO=_Ole))


def _install_soffice(monkeypatch: pytest.MonkeyPatch, *, kind: str, text: str) -> None:
    def run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        out_dir = cmd[cmd.index("--outdir") + 1]
        target = cmd[cmd.index("--convert-to") + 1]
        stem = Path(cmd[-1]).stem
        dest = Path(out_dir) / f"{stem}.{target}"
        if kind == "docx":
            document = docx.Document()
            document.add_paragraph(text)
            document.save(str(dest))
        else:
            wb = openpyxl.Workbook()
            wb.active["A1"] = text
            wb.save(str(dest))
        return subprocess.CompletedProcess(cmd, 0, b"", b"")

    monkeypatch.setattr("viparse.engines.legacy.subprocess.run", run)


def _doc(tmp_path: Path) -> Path:
    path = tmp_path / "old.doc"
    path.write_bytes(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")  # OLE2 magic (content is mocked away)
    return path


def test_doc_converts_and_delegates_to_docx(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _install_olefile(monkeypatch, ["WordDocument", "1Table"])
    _install_soffice(monkeypatch, kind="docx", text="Tài liệu cũ")
    raw = LegacyOfficeEngine().extract(_doc(tmp_path), LoadOptions())
    assert raw.engine == "libreoffice"
    assert raw.content_type == CONTENT_TYPE_OLE2  # provenance is the original legacy file
    assert raw.source.endswith("old.doc")
    assert "Tài liệu cũ" in raw.text


def test_xls_converts_and_delegates_to_xlsx(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _install_olefile(monkeypatch, ["Workbook"])
    _install_soffice(monkeypatch, kind="xlsx", text="Bảng cũ")
    raw = LegacyOfficeEngine().extract(_doc(tmp_path), LoadOptions())
    assert raw.engine == "libreoffice"
    assert "Bảng cũ" in raw.text


def test_unrecognized_ole2_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _install_olefile(monkeypatch, ["PowerPoint Document"])
    with pytest.raises(ExtractionError, match="unrecognized OLE2"):
        LegacyOfficeEngine().extract(_doc(tmp_path), LoadOptions())


def test_missing_olefile_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setitem(sys.modules, "olefile", None)
    with pytest.raises(MissingDependency, match=r"viparse\[office\]"):
        LegacyOfficeEngine().extract(_doc(tmp_path), LoadOptions())


def test_missing_soffice_binary_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _install_olefile(monkeypatch, ["WordDocument"])

    def run(cmd: list[str], **kwargs: object) -> object:
        raise FileNotFoundError("soffice")

    monkeypatch.setattr("viparse.engines.legacy.subprocess.run", run)
    with pytest.raises(MissingDependency, match="libreoffice"):
        LegacyOfficeEngine().extract(_doc(tmp_path), LoadOptions())


def test_conversion_timeout_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _install_olefile(monkeypatch, ["WordDocument"])

    def run(cmd: list[str], **kwargs: object) -> object:
        raise subprocess.TimeoutExpired(cmd, 120)

    monkeypatch.setattr("viparse.engines.legacy.subprocess.run", run)
    with pytest.raises(ExtractionError, match="timed out"):
        LegacyOfficeEngine().extract(_doc(tmp_path), LoadOptions())


@pytest.mark.parametrize(
    ("stderr", "expected"),
    [(b"filter error", "filter error"), (None, "failed to convert")],
)
def test_conversion_failure_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, stderr: bytes | None, expected: str
) -> None:
    _install_olefile(monkeypatch, ["WordDocument"])

    def run(cmd: list[str], **kwargs: object) -> object:
        raise subprocess.CalledProcessError(1, cmd, stderr=stderr)

    monkeypatch.setattr("viparse.engines.legacy.subprocess.run", run)
    with pytest.raises(ExtractionError, match=expected):
        LegacyOfficeEngine().extract(_doc(tmp_path), LoadOptions())


def test_no_output_produced_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _install_olefile(monkeypatch, ["WordDocument"])

    def run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(cmd, 0, b"", b"")  # writes nothing

    monkeypatch.setattr("viparse.engines.legacy.subprocess.run", run)
    with pytest.raises(ExtractionError, match="no output"):
        LegacyOfficeEngine().extract(_doc(tmp_path), LoadOptions())


def test_corrupt_ole2_raises_extraction_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # detect only matched the 8-byte magic; a truncated/encrypted OLE2 makes olefile raise.
    class _BadOle:
        def __init__(self, path: str) -> None:
            raise OSError("not an OLE2 structured storage file")

    monkeypatch.setitem(sys.modules, "olefile", types.SimpleNamespace(OleFileIO=_BadOle))
    with pytest.raises(ExtractionError, match="could not read OLE2"):
        LegacyOfficeEngine().extract(_doc(tmp_path), LoadOptions())


def test_supports_only_ole2() -> None:
    engine = LegacyOfficeEngine()
    assert engine.supports(CONTENT_TYPE_OLE2)
    assert not engine.supports("application/pdf")
