"""Tests for layered configuration (SPEC-5 E5.4)."""

from __future__ import annotations

from pathlib import Path

import pytest

from viparse.config import Settings, load_settings
from viparse.errors import ConfigError
from viparse.options import DEFAULT_MAX_BYTES, DEFAULT_NORMALIZE_FORM, DEFAULT_OUTPUT_FORMAT


def _write(directory: Path, body: str) -> Path:
    (directory / "viparse.toml").write_text(body, encoding="utf-8")
    return directory


# --- defaults & sources ----------------------------------------------------------------


def test_defaults_when_no_config_or_env(tmp_path: Path) -> None:
    settings = load_settings(start_dir=tmp_path, environ={})
    assert settings == Settings(
        output=DEFAULT_OUTPUT_FORMAT,
        encoding=None,
        ocr=None,
        normalize=DEFAULT_NORMALIZE_FORM,
        max_bytes=DEFAULT_MAX_BYTES,
    )


def test_reads_top_level_config_file(tmp_path: Path) -> None:
    _write(tmp_path, 'output = "json"\nencoding = "tcvn3"\nocr = true\nmax_bytes = 2048\n')
    settings = load_settings(start_dir=tmp_path, environ={})
    assert settings.output == "json"
    assert settings.encoding == "tcvn3"
    assert settings.ocr is True
    assert settings.max_bytes == 2048


def test_reads_tool_viparse_table(tmp_path: Path) -> None:
    _write(tmp_path, '[tool.viparse]\noutput = "text"\nnormalize = "NFD"\n')
    settings = load_settings(start_dir=tmp_path, environ={})
    assert settings.output == "text"
    assert settings.normalize == "NFD"


def test_env_overrides_config_file(tmp_path: Path) -> None:
    _write(tmp_path, 'output = "text"\nocr = false\n')
    settings = load_settings(
        start_dir=tmp_path, environ={"VIPARSE_OUTPUT": "json", "VIPARSE_OCR": "true"}
    )
    assert settings.output == "json"  # env wins over file
    assert settings.ocr is True


def test_env_only(tmp_path: Path) -> None:
    settings = load_settings(start_dir=tmp_path, environ={"VIPARSE_MAX_BYTES": "4096"})
    assert settings.max_bytes == 4096


# --- validation ------------------------------------------------------------------------


def test_unknown_key_raises(tmp_path: Path) -> None:
    _write(tmp_path, "nonsense = 1\n")
    with pytest.raises(ConfigError, match="unknown config key"):
        load_settings(start_dir=tmp_path, environ={})


def test_invalid_output_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="output must be one of"):
        load_settings(start_dir=tmp_path, environ={"VIPARSE_OUTPUT": "pdf"})


def test_invalid_normalize_raises(tmp_path: Path) -> None:
    _write(tmp_path, 'normalize = "NFZ"\n')
    with pytest.raises(ConfigError, match="normalize must be one of"):
        load_settings(start_dir=tmp_path, environ={})


def test_non_int_max_bytes_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="max_bytes must be an integer"):
        load_settings(start_dir=tmp_path, environ={"VIPARSE_MAX_BYTES": "big"})


def test_boolean_max_bytes_raises(tmp_path: Path) -> None:
    _write(tmp_path, "max_bytes = true\n")
    with pytest.raises(ConfigError, match="max_bytes must be an integer, got a boolean"):
        load_settings(start_dir=tmp_path, environ={})


def test_non_positive_max_bytes_raises(tmp_path: Path) -> None:
    _write(tmp_path, "max_bytes = 0\n")
    with pytest.raises(ConfigError, match="max_bytes must be positive"):
        load_settings(start_dir=tmp_path, environ={})


def test_non_bool_ocr_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="ocr must be a boolean"):
        load_settings(start_dir=tmp_path, environ={"VIPARSE_OCR": "maybe"})


def test_non_bool_non_str_ocr_raises(tmp_path: Path) -> None:
    _write(tmp_path, "ocr = 3\n")  # a TOML integer is neither bool nor a truthy/falsy word
    with pytest.raises(ConfigError, match="ocr must be a boolean, got 3"):
        load_settings(start_dir=tmp_path, environ={})


def test_non_string_encoding_raises(tmp_path: Path) -> None:
    _write(tmp_path, "encoding = 5\n")
    with pytest.raises(ConfigError, match="encoding must be a string"):
        load_settings(start_dir=tmp_path, environ={})


def test_malformed_toml_raises(tmp_path: Path) -> None:
    _write(tmp_path, "output = = broken\n")
    with pytest.raises(ConfigError, match="not valid TOML"):
        load_settings(start_dir=tmp_path, environ={})


def test_non_positive_string_max_bytes_from_env(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="max_bytes must be positive"):
        load_settings(start_dir=tmp_path, environ={"VIPARSE_MAX_BYTES": "-1"})


def test_env_boolean_false_word(tmp_path: Path) -> None:
    settings = load_settings(start_dir=tmp_path, environ={"VIPARSE_OCR": "off"})
    assert settings.ocr is False


def test_float_max_bytes_raises(tmp_path: Path) -> None:
    _write(tmp_path, "max_bytes = 1.5\n")
    with pytest.raises(ConfigError, match="max_bytes must be an integer, got float"):
        load_settings(start_dir=tmp_path, environ={})


def test_unrelated_tool_table_is_ignored(tmp_path: Path) -> None:
    _write(tmp_path, 'output = "json"\n[tool.black]\nline-length = 100\n')
    settings = load_settings(start_dir=tmp_path, environ={})
    assert settings.output == "json"  # top-level keys read; the foreign [tool.*] table ignored


def test_both_top_level_and_tool_viparse_is_ambiguous(tmp_path: Path) -> None:
    _write(tmp_path, 'output = "json"\n[tool.viparse]\nnormalize = "NFD"\n')
    with pytest.raises(ConfigError, match="both a \\[tool.viparse\\] table and top-level"):
        load_settings(start_dir=tmp_path, environ={})


def test_typoed_top_level_key_with_tool_viparse_is_flagged(tmp_path: Path) -> None:
    # A misspelled top-level key next to [tool.viparse] must not silently vanish.
    _write(tmp_path, 'outptu = "json"\n[tool.viparse]\nnormalize = "NFD"\n')
    with pytest.raises(ConfigError, match="top-level config key"):
        load_settings(start_dir=tmp_path, environ={})


# --- Settings self-validates (constructed directly, not just via load_settings) --------


def test_settings_validates_output() -> None:
    with pytest.raises(ConfigError, match="output must be one of"):
        Settings(output="xml")  # type: ignore[arg-type]


def test_settings_validates_max_bytes() -> None:
    with pytest.raises(ConfigError, match="max_bytes must be positive"):
        Settings(max_bytes=-1)


def test_settings_defaults_are_valid() -> None:
    assert Settings().output == DEFAULT_OUTPUT_FORMAT  # constructing the defaults never raises


# --- precedence through the public load() API ------------------------------------------


def _docx(path: Path) -> Path:
    docx = pytest.importorskip("docx")
    document = docx.Document()
    document.add_paragraph("Xin chào")
    document.save(str(path))
    return path


def test_load_uses_settings_when_arg_unset(tmp_path: Path) -> None:
    from viparse import Settings, load

    (doc,) = load(_docx(tmp_path / "a.docx"), settings=Settings(output="json"))
    assert doc.text.lstrip().startswith("{")  # JSON output came from the settings default


def test_load_explicit_arg_overrides_settings(tmp_path: Path) -> None:
    from viparse import Settings, load

    (doc,) = load(_docx(tmp_path / "a.docx"), output="text", settings=Settings(output="json"))
    assert doc.text == "Xin chào"  # the explicit output="text" wins over the settings


def test_load_reads_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from viparse import load

    path = _docx(tmp_path / "a.docx")
    monkeypatch.chdir(tmp_path)  # no viparse.toml here, so the env var decides
    monkeypatch.setenv("VIPARSE_OUTPUT", "json")
    (doc,) = load(path)
    assert doc.text.lstrip().startswith("{")


def test_load_reads_config_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from viparse import load

    path = _docx(tmp_path / "a.docx")
    (tmp_path / "viparse.toml").write_text('output = "text"\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("VIPARSE_OUTPUT", raising=False)
    (doc,) = load(path)
    assert doc.text == "Xin chào"  # text format resolved from viparse.toml


def test_load_batch_config_error_is_eager(monkeypatch: pytest.MonkeyPatch) -> None:
    # A bad config must raise when load_batch() is called, not lazily on first iteration
    # (where it would escape the per-source error isolation).
    from viparse import load_batch

    monkeypatch.setenv("VIPARSE_OUTPUT", "bogus")
    with pytest.raises(ConfigError, match="output must be one of"):
        load_batch(["a.docx", "b.docx"])  # no iteration — the call itself resolves options
