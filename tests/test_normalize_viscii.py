"""Golden tests for the VISCII → Unicode conversion table."""

from __future__ import annotations

import unicodedata

from viparse.normalize.encodings import get_charmap
from viparse.normalize.tables import convert
from viparse.normalize.viscii import _BYTE_TO_CODEPOINT, VISCII


def _viscii(*byte_values: int) -> str:
    """The Latin-1 surface form of a VISCII byte sequence (how it surfaces on extract)."""
    return bytes(byte_values).decode("latin-1")


def test_viscii_is_registered() -> None:
    assert get_charmap("viscii") is VISCII
    assert VISCII.name == "viscii"


def test_low_control_bytes_convert() -> None:
    # The six repurposed C0 control bytes.
    assert convert(_viscii(0x02), VISCII) == "Ẳ"
    assert convert(_viscii(0x05), VISCII) == "Ẵ"
    assert convert(_viscii(0x1E), VISCII) == "Ỵ"


def test_d_with_stroke_converts() -> None:
    assert convert(_viscii(0xD0), VISCII) == "Đ"
    assert convert(_viscii(0xF0), VISCII) == "đ"


def test_a_breve_and_o_horn_convert() -> None:
    assert convert(_viscii(0xC5), VISCII) == "Ă"
    assert convert(_viscii(0xE5), VISCII) == "ă"
    assert convert(_viscii(0xB4), VISCII) == "Ơ"
    assert convert(_viscii(0xBD), VISCII) == "ơ"


def test_converts_a_full_word() -> None:
    # "Tiếng Việt": ế = 0xAA, ệ = 0xAE; ASCII letters pass through.
    source = _viscii(0x54, 0x69, 0xAA, 0x6E, 0x67, 0x20, 0x56, 0x69, 0xAE, 0x74)
    assert convert(source, VISCII) == "Tiếng Việt"


def test_shared_latin1_letters_pass_through() -> None:
    # Bytes VISCII shares with Latin-1 (à, é, ô) are not remapped.
    assert convert(_viscii(0xE0, 0xE9, 0xF4), VISCII) == "àéô"


def test_output_is_nfc() -> None:
    source = "".join(_viscii(byte) for byte, _ in _BYTE_TO_CODEPOINT)
    converted = convert(source, VISCII)
    assert unicodedata.is_normalized("NFC", converted)


def test_table_is_complete_and_unambiguous() -> None:
    # Six control replacements + 0x80..0xFF (minus the shared Latin-1 letters).
    assert len(_BYTE_TO_CODEPOINT) == 103
    sources = [byte for byte, _ in _BYTE_TO_CODEPOINT]
    assert len(set(sources)) == len(sources)  # no duplicate byte
    # Every target is a single Unicode scalar (a precomposed Vietnamese letter).
    assert all(len(chr(cp)) == 1 for _, cp in _BYTE_TO_CODEPOINT)
