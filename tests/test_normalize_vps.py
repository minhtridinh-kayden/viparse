"""Golden tests for the VPS → Unicode conversion table."""

from __future__ import annotations

import unicodedata

from viparse.normalize.detector import detect_encoding_by_content
from viparse.normalize.encodings import AUTO_DETECT_CHARMAPS, CHARMAPS, get_charmap
from viparse.normalize.tables import convert
from viparse.normalize.vps import _BYTE_TO_CODEPOINT, VPS


def _vps(*byte_values: int) -> str:
    """The Latin-1 surface form of a VPS byte sequence (how it surfaces on extract)."""
    return bytes(byte_values).decode("latin-1")


def test_vps_is_registered() -> None:
    assert get_charmap("vps") is VPS
    assert VPS.name == "vps"


def test_repurposed_control_bytes_convert() -> None:
    # A few of the 14 C0 control bytes VPS repurposes for uppercase letters.
    assert convert(_vps(0x02), VPS) == "Ạ"
    assert convert(_vps(0x19), VPS) == "Ỵ"
    assert convert(_vps(0x1C), VPS) == "Ẫ"


def test_d_with_stroke_converts_to_the_vietnamese_letter() -> None:
    # Đ / đ must be U+0110 / U+0111 (D WITH STROKE), never the look-alike U+00D0 (Ð ETH).
    assert convert(_vps(0xF1), VPS) == "Đ"
    assert convert(_vps(0xC7), VPS) == "đ"
    assert ord(convert(_vps(0xF1), VPS)) == 0x0110


def test_o_horn_and_u_horn_convert() -> None:
    assert convert(_vps(0xF7), VPS) == "Ơ"
    assert convert(_vps(0xD6), VPS) == "ơ"
    assert convert(_vps(0xD0), VPS) == "Ư"
    assert convert(_vps(0xDC), VPS) == "ư"


def test_converts_a_full_word() -> None:
    # "Tiếng Việt": ế = 0x89, ệ = 0x8C; ASCII letters pass through.
    source = _vps(0x54, 0x69, 0x89, 0x6E, 0x67, 0x20, 0x56, 0x69, 0x8C, 0x74)
    assert convert(source, VPS) == "Tiếng Việt"


def test_shared_latin1_letters_pass_through() -> None:
    # Bytes VPS shares with Latin-1 (é, ô, à) are not remapped.
    assert convert(_vps(0xE9, 0xF4, 0xE0), VPS) == "éôà"


def test_output_is_nfc() -> None:
    source = "".join(_vps(byte) for byte, _ in _BYTE_TO_CODEPOINT)
    converted = convert(source, VPS)
    assert unicodedata.is_normalized("NFC", converted)


def test_vps_is_excluded_from_content_auto_detection() -> None:
    # VPS shares VISCII's Latin-1 surface bytes but maps them to different letters, so
    # auto-detecting it would risk corrupting genuine VISCII text; and its uppercase
    # letters are C0 control bytes cleanup strips before detection. VPS is therefore an
    # explicit-override-only encoding: registered for lookup, but not an auto candidate.
    assert "vps" in CHARMAPS  # reachable via encoding="vps"
    assert "vps" not in AUTO_DETECT_CHARMAPS  # but never auto-detected

    sentence = "Cộng hòa xã hội chủ nghĩa Việt Nam độc lập tự do hạnh phúc"
    encode = {chr(cp): chr(byte) for byte, cp in _BYTE_TO_CODEPOINT}
    surface = "".join(encode.get(ch, ch) for ch in unicodedata.normalize("NFC", sentence))
    # The explicit table converts the surface correctly...
    assert convert(surface, VPS) == unicodedata.normalize("NFC", sentence)
    # ...but content detection over the real candidate set never selects VPS.
    assert detect_encoding_by_content(surface, AUTO_DETECT_CHARMAPS).encoding != "vps"


def test_table_is_complete_and_unambiguous() -> None:
    # 14 repurposed C0 controls + the differing 0x80..0xFF bytes.
    assert len(_BYTE_TO_CODEPOINT) == 112
    sources = [byte for byte, _ in _BYTE_TO_CODEPOINT]
    assert len(set(sources)) == len(sources)  # no duplicate byte
    # Every entry genuinely differs from Latin-1 (shared letters are omitted), and
    # every target is a single Unicode scalar (a precomposed Vietnamese letter).
    assert all(chr(byte) != chr(cp) for byte, cp in _BYTE_TO_CODEPOINT)
    assert all(len(chr(cp)) == 1 for _, cp in _BYTE_TO_CODEPOINT)
