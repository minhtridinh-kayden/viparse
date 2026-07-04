"""Tests for the legacy-encoding conversion framework and the TCVN3/VNI tables."""

from __future__ import annotations

import unicodedata

import pytest

from viparse.normalize.encodings import CHARMAPS, _register, get_charmap
from viparse.normalize.tables import build_charmap, convert
from viparse.normalize.tcvn3 import TCVN3
from viparse.normalize.vni import VNI

# --- Framework: build_charmap --------------------------------------------


def test_build_charmap_sorts_longest_first() -> None:
    cm = build_charmap("t", [("a", "1"), ("abc", "3"), ("ab", "2")])
    assert [seq for seq, _ in cm.pairs] == ["abc", "ab", "a"]


def test_build_charmap_rejects_empty_source() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        build_charmap("t", [("", "1")])


def test_build_charmap_rejects_empty_replacement() -> None:
    with pytest.raises(ValueError, match="replacement.*must not be empty"):
        build_charmap("t", [("µ", "")])


def test_build_charmap_rejects_duplicate_source() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        build_charmap("t", [("a", "1"), ("a", "2")])


# --- Framework: convert --------------------------------------------------


def test_convert_prefers_longest_match() -> None:
    cm = build_charmap("t", [("ab", "Z"), ("a", "y"), ("x", "W")])
    assert convert("abax", cm) == "ZyW"


def test_convert_passes_through_unmapped_characters() -> None:
    cm = build_charmap("t", [("µ", "à")])
    assert convert("Tea µ time", cm) == "Tea à time"


def test_convert_is_single_pass_no_reintroduction() -> None:
    """A replacement's output is never re-matched as another rule's input."""
    cm = build_charmap("t", [("a", "b"), ("b", "c")])
    assert convert("a", cm) == "b"  # not "c"


def test_convert_output_is_nfc() -> None:
    decomposed = "e" + "́"  # e + combining acute
    cm = build_charmap("t", [("X", decomposed)])
    result = convert("X", cm)
    assert result == "é"
    assert unicodedata.is_normalized("NFC", result)


def test_convert_respects_normalize_form() -> None:
    cm = build_charmap("t", [("X", "é")])
    result = convert("X", cm, normalize_form="NFD")
    assert result == "e" + "́"


# --- Tables: TCVN3 / VNI golden characters -------------------------------


def test_tcvn3_converts_a_group() -> None:
    assert convert("µ¸¶·¹", TCVN3) == "àáảãạ"


def test_tcvn3_converts_dj() -> None:
    assert convert("®", TCVN3) == "đ"


def test_tcvn3_output_is_nfc() -> None:
    out = convert("µ¸¶·¹", TCVN3)
    assert unicodedata.is_normalized("NFC", out)


def test_vni_converts_composite_sequences() -> None:
    assert convert("a½aùaûaõaï", VNI) == "àáảãạ"


def test_vni_converts_dj() -> None:
    assert convert("ñ", VNI) == "đ"


def test_ascii_text_is_unchanged_by_tables() -> None:
    assert convert("Ha Noi 2026", TCVN3) == "Ha Noi 2026"


# --- Registry ------------------------------------------------------------


def test_registry_lookup() -> None:
    assert get_charmap("tcvn3") is TCVN3
    assert get_charmap("vni") is VNI
    assert get_charmap("unknown") is None


def test_registry_contains_expected_encodings() -> None:
    assert set(CHARMAPS) == {"tcvn3", "vni"}


def test_register_rejects_duplicate_names() -> None:
    a = build_charmap("dup", [("x", "y")])
    b = build_charmap("dup", [("p", "q")])
    with pytest.raises(ValueError, match="duplicate encoding name"):
        _register(a, b)
