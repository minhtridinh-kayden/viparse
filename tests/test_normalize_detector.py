"""Tests for the font-signal encoding detector."""

from __future__ import annotations

import pytest

from viparse.normalize.detector import detect_encoding


@pytest.mark.parametrize(
    "font",
    [".VnTime", ".VnArial", ".VnTimeH", ".vntime", ".VNTIME", "ABCDEF+.VnTime"],
)
def test_dot_vn_fonts_detect_tcvn3(font: str) -> None:
    result = detect_encoding([font])
    assert result.encoding == "tcvn3"
    assert result.method == "font-signal"
    assert result.font == font
    assert result.confidence == pytest.approx(0.95)


@pytest.mark.parametrize("font", ["VNI-Times", "VNI-Helve", "vni-times", "XYZKLM+VNI-Times"])
def test_vni_fonts_detect_vni(font: str) -> None:
    result = detect_encoding([font])
    assert result.encoding == "vni"
    assert result.method == "font-signal"


def test_legacy_font_wins_over_plain_fonts() -> None:
    result = detect_encoding(["Arial", "Times New Roman", ".VnTime"])
    assert result.encoding == "tcvn3"
    assert result.font == ".VnTime"


def test_mixed_legacy_encodings_are_flagged() -> None:
    result = detect_encoding([".VnTime", "VNI-Times"])
    assert result.encoding == "tcvn3"  # first-detected
    assert result.method == "font-signal-mixed"
    assert result.confidence == pytest.approx(0.6)


def test_none_fonts_are_ignored() -> None:
    assert detect_encoding([None, ".VnTime"]).encoding == "tcvn3"
    assert detect_encoding([None, "Arial"]).method == "no-legacy-font"
    assert detect_encoding([None, None]).method == "assumed-unicode"


def test_plain_fonts_are_unicode() -> None:
    result = detect_encoding(["Arial", "Calibri"])
    assert result.encoding is None
    assert result.method == "no-legacy-font"
    assert result.confidence == pytest.approx(0.9)


def test_no_fonts_assumes_unicode() -> None:
    result = detect_encoding([])
    assert result.encoding is None
    assert result.method == "assumed-unicode"
    assert result.confidence == pytest.approx(0.5)


def test_legacy_confidence_beats_assumption() -> None:
    legacy = detect_encoding([".VnTime"]).confidence
    unicode_present = detect_encoding(["Arial"]).confidence
    assumed = detect_encoding([]).confidence
    assert legacy > unicode_present > assumed
