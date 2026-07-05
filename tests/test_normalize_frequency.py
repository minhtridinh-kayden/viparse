"""Tests for the content-frequency encoding model and detector."""

from __future__ import annotations

import unicodedata

from viparse.normalize.detector import detect_encoding_by_content
from viparse.normalize.encodings import CHARMAPS
from viparse.normalize.frequency import vietnamese_score
from viparse.normalize.viscii import _BYTE_TO_CODEPOINT


def _encode(text: str, name: str) -> str:
    """Reverse a charmap: turn Unicode Vietnamese back into its legacy surface form."""
    reverse = {target: source for source, target in CHARMAPS[name].pairs}
    return "".join(reverse.get(ch, ch) for ch in unicodedata.normalize("NFC", text))


def _encode_viscii(text: str) -> str:
    cp_to_byte = {cp: byte for byte, cp in _BYTE_TO_CODEPOINT}
    codes = [cp_to_byte.get(ord(ch), ord(ch)) for ch in unicodedata.normalize("NFC", text)]
    return bytes(codes).decode("latin-1")


def test_score_prefers_vietnamese_over_foreign_glyphs() -> None:
    assert vietnamese_score("người Việt Nam") > vietnamese_score("þÿ§±¤×")


def test_score_of_empty_text_is_the_floor() -> None:
    assert vietnamese_score("") < 0.0


def test_detects_tcvn3_by_content() -> None:
    detection = detect_encoding_by_content(_encode("đá và cà đăng", "tcvn3"), CHARMAPS)
    assert detection.encoding == "tcvn3"
    assert detection.method == "content-frequency"


def test_detects_vni_by_content() -> None:
    assert detect_encoding_by_content(_encode("áạđ áạ đ", "vni"), CHARMAPS).encoding == "vni"


def test_detects_viscii_by_content() -> None:
    surface = _encode_viscii("Việt Nam độc lập tự do hạnh phúc")
    assert detect_encoding_by_content(surface, CHARMAPS).encoding == "viscii"


def test_single_candidate_is_accepted_when_it_clears_the_margin() -> None:
    surface = _encode("đá và cà đăng", "tcvn3")
    only_tcvn3 = {"tcvn3": CHARMAPS["tcvn3"]}
    assert detect_encoding_by_content(surface, only_tcvn3).encoding == "tcvn3"


def test_ambiguous_text_is_left_unconverted() -> None:
    # "Vi®t Nam": the single legacy byte maps to plausible Vietnamese under BOTH tcvn3
    # ("Viđt") and viscii ("Việt"), so no table clearly wins → leave it as Unicode.
    surface = bytes([0x56, 0x69, 0xAE, 0x74, 0x20, 0x4E, 0x61, 0x6D]).decode("latin-1")
    detection = detect_encoding_by_content(surface, CHARMAPS)
    assert detection.encoding is None
    assert detection.method == "assumed-unicode"


def test_unicode_vietnamese_needs_no_conversion() -> None:
    assert detect_encoding_by_content("Tiếng Việt Nam", CHARMAPS).encoding is None


def test_ascii_needs_no_conversion() -> None:
    detection = detect_encoding_by_content("Hello world", CHARMAPS)
    assert detection.encoding is None
    assert detection.method == "assumed-unicode"


def test_content_confidence_stays_below_font_certainty() -> None:
    detection = detect_encoding_by_content(_encode("đá và cà đăng", "tcvn3"), CHARMAPS)
    assert 0.5 < detection.confidence <= 0.85
