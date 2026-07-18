"""Tests for the RTF extraction adapter."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from viparse.detect import CONTENT_TYPE_RTF
from viparse.engines.rtf import RtfEngine
from viparse.errors import MissingDependency
from viparse.options import LoadOptions
from viparse.registry import EngineRegistry

pytest.importorskip("striprtf.striprtf")  # skipped if the rtf extra is absent


def _write_rtf(path: Path, body: str) -> Path:
    """Write a minimal RTF document (latin-1, as RTF is an ASCII control stream)."""
    path.write_bytes(body.encode("latin-1"))
    return path


_SIMPLE = (
    r"{\rtf1\ansi\ansicpg1252\deff0"
    r"{\fonttbl{\f0\fnil\fcharset0 .VnTime;}{\f1\fswiss\fcharset0 Arial;}}"
    r"\f0 xin chao\par \f1 world\par}"
)


def test_extract_returns_text(tmp_path: Path) -> None:
    raw = RtfEngine().extract(_write_rtf(tmp_path / "a.rtf", _SIMPLE), LoadOptions())
    assert raw.engine == "rtf"
    assert raw.content_type == CONTENT_TYPE_RTF
    assert "xin chao" in raw.text
    assert "world" in raw.text


def test_builds_paragraph_blocks(tmp_path: Path) -> None:
    raw = RtfEngine().extract(_write_rtf(tmp_path / "a.rtf", _SIMPLE), LoadOptions())
    assert [b["text"] for b in raw.signals["blocks"]] == ["xin chao", "world"]


def test_attaches_no_font_signal(tmp_path: Path) -> None:
    """RTF is text-only: a font table is *declared* fonts, not applied ones, so lifting it
    would risk converting a Unicode body through a legacy charmap. No ``fonts`` signal."""
    raw = RtfEngine().extract(_write_rtf(tmp_path / "a.rtf", _SIMPLE), LoadOptions())
    assert "fonts" not in raw.signals


def test_declared_legacy_font_does_not_corrupt_unicode_body(tmp_path: Path) -> None:
    """A Unicode RTF that merely *declares* a legacy .VnTime font must pass through
    untouched — the engine emits no font signal, so nothing forces a legacy conversion."""
    from viparse.normalize.normalizer import VietnameseNormalizer

    rtf = (
        r"{\rtf1\ansi\ansicpg1252\deff0"
        r"{\fonttbl{\f0\fnil\fcharset0 .VnTime;}{\f1\fswiss Arial;}}"
        r"\f1 viparse\'ae 2026\par}"  # Unicode body (Arial); \'ae = ®
    )
    raw = RtfEngine().extract(_write_rtf(tmp_path / "u.rtf", rtf), LoadOptions())
    nd = VietnameseNormalizer().normalize(raw, LoadOptions())
    assert nd.text == "viparse® 2026"  # "®" preserved, NOT mapped to "đ"
    assert nd.encoding_detected is None


def test_legacy_rtf_converts_with_explicit_encoding(tmp_path: Path) -> None:
    """The moat still works through RTF via an explicit override: \\'b5\\'b8 ("µ¸") → "àá"."""
    from viparse.normalize.normalizer import VietnameseNormalizer

    rtf = r"{\rtf1\ansi\ansicpg1252 \'b5\'b8\par}"
    raw = RtfEngine().extract(_write_rtf(tmp_path / "legacy.rtf", rtf), LoadOptions())
    nd = VietnameseNormalizer().normalize(raw, LoadOptions(encoding="tcvn3"))
    assert nd.text == "àá"
    assert nd.encoding_detected == "tcvn3"


def test_supports_only_rtf() -> None:
    engine = RtfEngine()
    assert engine.supports(CONTENT_TYPE_RTF)
    assert not engine.supports("application/pdf")


def test_registry_selects_rtf_engine() -> None:
    reg = EngineRegistry()
    reg.register(RtfEngine())
    assert isinstance(reg.select(CONTENT_TYPE_RTF), RtfEngine)


def test_missing_dependency_raises_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without striprtf, extraction fails with actionable install guidance."""
    monkeypatch.setitem(sys.modules, "striprtf.striprtf", None)
    with pytest.raises(MissingDependency, match=r"viparse\[rtf\]"):
        RtfEngine().extract("missing.rtf", LoadOptions())
