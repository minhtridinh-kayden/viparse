"""Tests for the concrete Vietnamese normalizer (detect → convert → NFC)."""

from __future__ import annotations

import unicodedata
from typing import Any

import pytest

from viparse.model import Heading, Paragraph, RawExtraction, Table
from viparse.normalize.normalizer import VietnameseNormalizer
from viparse.normalize.viscii import _BYTE_TO_CODEPOINT as _VISCII_BYTES
from viparse.options import LoadOptions

# Every precomposed Vietnamese accented vowel (lowercase) plus đ, for NFC/NFD tests.
_VIETNAMESE_ACCENTED = "àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ"


def _raw(text: str, fonts: list[Any] | None = None) -> RawExtraction:
    return RawExtraction(
        source="a.docx",
        content_type="application/vnd.docx",
        text=text,
        engine="docx",
        signals={"fonts": fonts if fonts is not None else []},
    )


def test_converts_tcvn3_from_font_signal() -> None:
    nd = VietnameseNormalizer().normalize(_raw("µ¸¶·¹", [".VnTime"]), LoadOptions())
    assert nd.text == "àáảãạ"
    assert nd.encoding_detected == "tcvn3"
    assert nd.encoding_confidence == pytest.approx(0.95)
    assert unicodedata.is_normalized("NFC", nd.text)


def test_converts_vni_via_encoding_override() -> None:
    nd = VietnameseNormalizer().normalize(_raw("aùaïñ"), LoadOptions(encoding="vni"))
    assert nd.text == "áạđ"
    assert nd.encoding_detected == "vni"
    assert nd.encoding_confidence == pytest.approx(1.0)


def test_converts_viscii_via_encoding_override() -> None:
    source = bytes([0x56, 0x69, 0xAE, 0x74]).decode("latin-1")  # "Việt" in VISCII bytes
    nd = VietnameseNormalizer().normalize(_raw(source), LoadOptions(encoding="viscii"))
    assert nd.text == "Việt"
    assert nd.encoding_detected == "viscii"
    assert nd.encoding_confidence == pytest.approx(1.0)


def test_unicode_text_is_only_nfc_normalized() -> None:
    decomposed = "Vie" + "̣" + "t"  # Việt with a combining dot below
    nd = VietnameseNormalizer().normalize(_raw(decomposed, ["Arial"]), LoadOptions())
    assert nd.encoding_detected is None
    assert unicodedata.is_normalized("NFC", nd.text)
    assert nd.text == unicodedata.normalize("NFC", decomposed)


def test_normalize_form_nfd_is_respected() -> None:
    nd = VietnameseNormalizer().normalize(
        _raw("Việt", ["Arial"]), LoadOptions(normalize_form="NFD")
    )
    assert nd.text == unicodedata.normalize("NFD", "Việt")
    assert not unicodedata.is_normalized("NFC", nd.text)


def test_unknown_encoding_override_warns_and_leaves_text() -> None:
    # VPS is a real Vietnamese encoding that viparse does not yet have a table for.
    nd = VietnameseNormalizer().normalize(_raw("plain", ["Arial"]), LoadOptions(encoding="vps"))
    assert nd.encoding_detected == "vps"
    assert any("no conversion table" in w for w in nd.warnings)
    assert nd.text == "plain"


def _viscii_surface(text: str) -> str:
    cp_to_byte = {cp: byte for byte, cp in _VISCII_BYTES}
    return bytes(cp_to_byte.get(ord(ch), ord(ch)) for ch in text).decode("latin-1")


def test_auto_encoding_content_detects_without_a_font_signal() -> None:
    # encoding="auto" opts in: "Việt Nam độc lập" in VISCII bytes, no font signal.
    text = "Việt Nam độc lập"
    nd = VietnameseNormalizer().normalize(
        _raw(_viscii_surface(text), []), LoadOptions(encoding="auto")
    )
    assert nd.encoding_detected == "viscii"
    assert nd.text == text


def test_default_mode_never_content_detects() -> None:
    # Without encoding="auto", the same fontless legacy surface is LEFT ALONE — the moat
    # never risks a wrong conversion on a document the caller has not asserted is legacy.
    surface = _viscii_surface("Việt Nam độc lập")
    nd = VietnameseNormalizer().normalize(_raw(surface, []), LoadOptions())
    assert nd.encoding_detected is None
    assert nd.text == surface


def test_auto_encoding_still_prefers_a_font_signal() -> None:
    # In auto mode a real (non-legacy) font signal wins; content detection is not consulted.
    surface = _viscii_surface("Việt Nam")
    nd = VietnameseNormalizer().normalize(_raw(surface, ["Arial"]), LoadOptions(encoding="auto"))
    assert nd.encoding_detected is None


def test_native_unicode_signal_skips_detection_and_warning() -> None:
    # An engine (e.g. OCR) that already produced Unicode marks it, so the normalizer
    # neither detects an encoding nor emits a spurious low-confidence warning.
    raw = RawExtraction(
        source="scan.pdf",
        content_type="application/pdf",
        text="Tiếng Việt",
        signals={"fonts": [], "native_unicode": True},
    )
    nd = VietnameseNormalizer().normalize(raw, LoadOptions())
    assert nd.encoding_detected is None
    assert nd.text == "Tiếng Việt"
    assert nd.warnings == []


def test_mixed_encoding_warns() -> None:
    nd = VietnameseNormalizer().normalize(_raw("µ", [".VnTime", "VNI-Times"]), LoadOptions())
    assert any("multiple legacy encodings" in w for w in nd.warnings)


def test_low_confidence_warns() -> None:
    nd = VietnameseNormalizer().normalize(_raw("text", []), LoadOptions())  # assumed-unicode 0.5
    assert any("low encoding-detection confidence" in w for w in nd.warnings)


def test_high_confidence_has_no_warning() -> None:
    nd = VietnameseNormalizer().normalize(_raw("text", ["Arial"]), LoadOptions())  # 0.9
    assert nd.warnings == []


def test_none_or_missing_fonts_signal_does_not_crash() -> None:
    none_fonts = RawExtraction(source="a", content_type="t", text="x", signals={"fonts": None})
    no_key = RawExtraction(source="a", content_type="t", text="x", signals={})
    for raw in (none_fonts, no_key):
        nd = VietnameseNormalizer().normalize(raw, LoadOptions())
        assert nd.encoding_detected is None
        assert nd.text == "x"


def test_normalizer_applies_cleanup() -> None:
    nd = VietnameseNormalizer().normalize(_raw("  a    b  \n\n\n c ", ["Arial"]), LoadOptions())
    assert nd.text == "a b\n\nc"


def test_carries_location_provenance_forward() -> None:
    raw = RawExtraction(
        source="a.xlsx",
        content_type="t",
        text="x",
        signals={"fonts": ["Arial"]},
        page=3,
        sheet="Data",
    )
    nd = VietnameseNormalizer().normalize(raw, LoadOptions())
    assert nd.page == 3
    assert nd.sheet == "Data"


def test_extract_stage_warnings_are_carried_forward() -> None:
    raw = RawExtraction(
        source="a",
        content_type="t",
        text="ok",
        signals={"fonts": ["Arial"]},
        warnings=["page 2 failed to extract"],
    )
    nd = VietnameseNormalizer().normalize(raw, LoadOptions())
    assert "page 2 failed to extract" in nd.warnings


def _raw_blocks(blocks: list[Any], fonts: list[Any], text: str = "") -> RawExtraction:
    return RawExtraction(
        source="a.docx",
        content_type="application/vnd.docx",
        text=text,
        engine="docx",
        signals={"fonts": fonts, "blocks": blocks},
    )


def test_normalizes_structural_blocks() -> None:
    blocks = [
        {"type": "heading", "level": 2, "text": "  Tiêu đề  "},
        {"type": "paragraph", "text": "Nội   dung"},
        {"type": "table", "rows": [["A", "B"], ["1", "2"]]},
    ]
    nd = VietnameseNormalizer().normalize(_raw_blocks(blocks, ["Arial"]), LoadOptions())
    assert nd.blocks == [
        Heading(level=2, text="Tiêu đề"),
        Paragraph(text="Nội dung"),
        Table(rows=[["A", "B"], ["1", "2"]]),
    ]


def test_flat_text_stays_the_engine_flat_text_normalized() -> None:
    # The engine authors raw.text; the normalizer only encoding-converts + cleans it,
    # never re-derives it from the blocks.
    raw = _raw_blocks([{"type": "paragraph", "text": "x"}], ["Arial"], text="Nội   dung  ")
    nd = VietnameseNormalizer().normalize(raw, LoadOptions())
    assert nd.text == "Nội dung"


def test_block_conversion_applies_legacy_encoding_per_field() -> None:
    blocks = [
        {"type": "heading", "level": 1, "text": "µ¸"},
        {"type": "table", "rows": [["¶·¹"]]},
    ]
    nd = VietnameseNormalizer().normalize(_raw_blocks(blocks, [".VnTime"]), LoadOptions())
    assert nd.encoding_detected == "tcvn3"
    assert nd.blocks == [Heading(level=1, text="àá"), Table(rows=[["ảãạ"]])]


def test_malformed_blocks_degrade_without_crashing() -> None:
    # A third-party engine emitting off-contract blocks must not raise KeyError/TypeError.
    blocks = [
        {"type": "heading", "text": "no level"},  # missing level → defaults to 1
        {"type": "paragraph"},  # missing text → empty
        {"type": "table"},  # missing rows → empty table
        {"text": "no type"},  # missing type → treated as a paragraph
    ]
    nd = VietnameseNormalizer().normalize(_raw_blocks(blocks, ["Arial"]), LoadOptions())
    assert nd.blocks == [
        Heading(level=1, text="no level"),
        Paragraph(text=""),
        Table(rows=[]),
        Paragraph(text="no type"),
    ]


def test_no_blocks_leaves_blocks_empty() -> None:
    nd = VietnameseNormalizer().normalize(_raw("plain", ["Arial"]), LoadOptions())
    assert nd.blocks == []


@pytest.mark.parametrize("char", list(_VIETNAMESE_ACCENTED))
def test_nfc_nfd_roundtrip_for_all_accented_vowels(char: str) -> None:
    """Feeding the NFD form of each Vietnamese vowel yields the NFC precomposed form."""
    nfd = unicodedata.normalize("NFD", char)
    nd = VietnameseNormalizer().normalize(_raw(nfd, ["Arial"]), LoadOptions())
    assert nd.text == char
    assert unicodedata.is_normalized("NFC", nd.text)
