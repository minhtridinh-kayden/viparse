"""Tests for the untrusted-input safety guards."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from viparse.detect import CONTENT_TYPE_DOCX, CONTENT_TYPE_PDF
from viparse.errors import UnsafeInput
from viparse.safety import check_file_size, check_zip_bomb


def _zip(path: Path, members: dict[str, bytes], *, compression: int = zipfile.ZIP_STORED) -> Path:
    with zipfile.ZipFile(path, "w", compression=compression) as zf:
        for name, data in members.items():
            zf.writestr(name, data)
    return path


def test_file_within_limit_passes(tmp_path: Path) -> None:
    path = tmp_path / "small.bin"
    path.write_bytes(b"x" * 100)
    check_file_size(path, max_bytes=1000)  # no raise


def test_oversized_file_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "big.bin"
    path.write_bytes(b"x" * 5000)
    with pytest.raises(UnsafeInput, match="over the 1000-byte limit"):
        check_file_size(path, max_bytes=1000)


def test_non_ooxml_content_is_not_zip_checked(tmp_path: Path) -> None:
    # A PDF is not a ZIP; check_zip_bomb must be a no-op (and never open it as a zip).
    check_zip_bomb(tmp_path / "does-not-matter.pdf", CONTENT_TYPE_PDF)


def test_normal_ooxml_passes(tmp_path: Path) -> None:
    path = _zip(tmp_path / "ok.docx", {"word/document.xml": b"<w:document/>" * 50})
    check_zip_bomb(path, CONTENT_TYPE_DOCX)  # no raise


def test_decompression_bomb_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # 2 MiB of zeros compresses to almost nothing; the probe decompresses it for real and
    # aborts once it crosses the (patched-tiny) ceiling — declared sizes are never trusted.
    monkeypatch.setattr("viparse.safety._MAX_UNCOMPRESSED_BYTES", 100)
    path = _zip(
        tmp_path / "bomb.docx",
        {"word/document.xml": b"\x00" * (2 * 1024 * 1024)},
        compression=zipfile.ZIP_DEFLATED,
    )
    with pytest.raises(UnsafeInput, match="decompresses past"):
        check_zip_bomb(path, CONTENT_TYPE_DOCX)
