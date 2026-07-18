"""Character-level regression tests over the legacy encoding tables (SPEC-6 E6.2 / T6.2.1).

Every conversion-table mapping is exercised entry-by-entry so a regression in any single
character fails loudly. (The NFD↔NFC repertoire round-trip lives in
``test_normalizer.py::test_nfc_nfd_roundtrip_for_all_accented_vowels``, which owns the single
source of truth for the Vietnamese letter set.)
"""

from __future__ import annotations

import unicodedata

import pytest

from viparse.normalize.detector import detect_encoding_by_content
from viparse.normalize.encodings import CHARMAPS
from viparse.normalize.tables import convert
from viparse.normalize.viscii import _BYTE_TO_CODEPOINT
from viparse.normalize.vps import _BYTE_TO_CODEPOINT as _VPS_BYTE_TO_CODEPOINT

_TCVN3 = CHARMAPS["tcvn3"]
_VNI = CHARMAPS["vni"]
_VISCII = CHARMAPS["viscii"]
_VPS = CHARMAPS["vps"]


# --- T6.2.1: every table entry converts to the correct NFC character -----------------


@pytest.mark.parametrize(("byte", "codepoint"), _BYTE_TO_CODEPOINT)
def test_viscii_entry_converts(byte: int, codepoint: int) -> None:
    assert convert(chr(byte), _VISCII) == unicodedata.normalize("NFC", chr(codepoint))


@pytest.mark.parametrize(("byte", "codepoint"), _VPS_BYTE_TO_CODEPOINT)
def test_vps_entry_converts(byte: int, codepoint: int) -> None:
    assert convert(chr(byte), _VPS) == unicodedata.normalize("NFC", chr(codepoint))


@pytest.mark.parametrize(("source", "target"), _TCVN3.pairs)
def test_tcvn3_entry_converts(source: str, target: str) -> None:
    assert convert(source, _TCVN3) == unicodedata.normalize("NFC", target)


@pytest.mark.parametrize(("source", "target"), _VNI.pairs)
def test_vni_entry_converts(source: str, target: str) -> None:
    assert convert(source, _VNI) == unicodedata.normalize("NFC", target)


@pytest.mark.parametrize("name", ["tcvn3", "vni", "viscii", "vps"])
def test_all_table_targets_are_nfc(name: str) -> None:
    assert all(unicodedata.is_normalized("NFC", target) for _, target in CHARMAPS[name].pairs)


# --- T6.2.3: content detection is a no-op on short / non-legacy strings ---------------


@pytest.mark.parametrize("text", ["", "a", "Hi", "ok then"])
def test_short_non_legacy_text_is_left_unconverted(text: str) -> None:
    assert detect_encoding_by_content(text, CHARMAPS).encoding is None
