"""Tests for the ``viparse`` command-line interface."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from viparse import cli

docx = pytest.importorskip("docx")  # python-docx; skipped without the office extra


def _write_docx(path: Path, text: str, font: str | None = None) -> Path:
    document = docx.Document()
    run = document.add_paragraph().add_run(text)
    if font is not None:
        run.font.name = font
    document.save(str(path))
    return path


def test_renders_single_file_to_stdout(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = _write_docx(tmp_path / "a.docx", "Tiếng Việt")
    assert cli.main([str(path)]) == 0
    assert capsys.readouterr().out == "Tiếng Việt\n"


def test_output_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = _write_docx(tmp_path / "a.docx", "Xin chào")
    assert cli.main([str(path), "-o", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["blocks"] == [{"type": "paragraph", "text": "Xin chào"}]


def test_encoding_override(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = _write_docx(tmp_path / "legacy.docx", "µ¸¶·¹", font=".VnTime")
    assert cli.main([str(path), "-o", "text", "--encoding", "tcvn3"]) == 0
    assert capsys.readouterr().out == "àáảãạ\n"


def test_normalize_form_flag(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    import unicodedata

    path = _write_docx(tmp_path / "a.docx", "Việt")
    assert cli.main([str(path), "-o", "text", "--normalize", "NFD"]) == 0
    assert capsys.readouterr().out == unicodedata.normalize("NFD", "Việt") + "\n"


def test_ocr_flag_is_accepted(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = _write_docx(tmp_path / "a.docx", "ok")
    assert cli.main([str(path), "--no-ocr", "-o", "text"]) == 0
    assert capsys.readouterr().out == "ok\n"


def test_multiple_files_are_separated_on_stdout(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    a = _write_docx(tmp_path / "a.docx", "Một")
    b = _write_docx(tmp_path / "b.docx", "Hai")
    assert cli.main([str(a), str(b), "-o", "text"]) == 0
    assert capsys.readouterr().out == "Một\n\nHai\n"


def test_out_dir_writes_one_file_per_input(tmp_path: Path) -> None:
    path = _write_docx(tmp_path / "a.docx", "Nội dung")
    out = tmp_path / "rendered"
    assert cli.main([str(path), "-o", "md", "--out", str(out)]) == 0
    assert (out / "a.md").read_text(encoding="utf-8") == "Nội dung\n"


def test_directory_argument_is_expanded(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    sub = tmp_path / "docs"
    sub.mkdir()
    _write_docx(sub / "a.docx", "Trong thư mục")
    assert cli.main([str(tmp_path), "-o", "text"]) == 0
    assert capsys.readouterr().out == "Trong thư mục\n"


def test_glob_argument_is_expanded(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_docx(tmp_path / "a.docx", "A")
    _write_docx(tmp_path / "b.docx", "B")
    assert cli.main([str(tmp_path / "*.docx"), "-o", "text"]) == 0
    assert capsys.readouterr().out == "A\n\nB\n"


def test_duplicate_paths_are_deduplicated(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _write_docx(tmp_path / "a.docx", "Once")
    assert cli.main([str(path), str(path), "-o", "text"]) == 0
    assert capsys.readouterr().out == "Once\n"


def test_literal_bracketed_filename_is_not_treated_as_glob(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _write_docx(tmp_path / "Report[Final].docx", "Bản cuối")
    assert cli.main([str(path), "-o", "text"]) == 0
    assert capsys.readouterr().out == "Bản cuối\n"


def test_out_dir_disambiguates_basename_collisions(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    first = _write_docx(tmp_path / "a" / "report.docx", "Một")
    second = _write_docx(tmp_path / "b" / "report.docx", "Hai")
    out = tmp_path / "rendered"
    assert cli.main([str(first), str(second), "-o", "text", "--out", str(out)]) == 0
    assert (out / "report.txt").read_text(encoding="utf-8") == "Một\n"
    assert (out / "report-1.txt").read_text(encoding="utf-8") == "Hai\n"


def test_no_match_reports_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main([str(tmp_path / "nothing" / "*.docx")]) == 1
    assert "no input files matched" in capsys.readouterr().err


def test_missing_file_reports_failure(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main([str(tmp_path / "ghost.docx")]) == 1
    assert "viparse:" in capsys.readouterr().err


def test_unsupported_file_reports_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "note.txt"
    bad.write_text("plain text", encoding="utf-8")
    assert cli.main([str(bad)]) == 1
    assert "viparse:" in capsys.readouterr().err


def test_doctor_reports_the_docx_engine(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["doctor"]) == 0
    out = capsys.readouterr().out
    assert "viparse" in out
    assert "DocxEngine (docx): available" in out  # python-docx is installed under [office]


class _StdlibEngine:
    dependency = None
    extra = None


class _MissingEngine:
    dependency = "no_such_module_zzz"
    extra = "ghost"


def test_doctor_flags_available_and_missing_dependencies(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli, "_default_engines", lambda: [_StdlibEngine(), _MissingEngine()])
    assert cli.main(["doctor"]) == 0
    out = capsys.readouterr().out
    assert "_StdlibEngine (stdlib): available" in out
    assert "_MissingEngine (no_such_module_zzz): unavailable — pip install 'viparse[ghost]'" in out
