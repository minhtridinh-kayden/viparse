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
    # Vietware is a real Vietnamese encoding that viparse does not yet have a table for.
    raw = _raw("plain", ["Arial"])
    nd = VietnameseNormalizer().normalize(raw, LoadOptions(encoding="vietware"))
    assert nd.encoding_detected == "vietware"
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


# --- Per-block detection for mixed-encoding documents (SPEC-3 T3.2.4) ---


def test_mixed_document_converts_each_block_by_its_own_encoding() -> None:
    # A legacy TCVN3 paragraph next to a Unicode paragraph whose text legitimately
    # contains "®" (also a TCVN3 surface byte for đ). Whole-document conversion would
    # corrupt "viparse®" → "viparseđ"; per-block detection must leave it alone.
    blocks = [
        {"type": "paragraph", "text": "µ¸", "fonts": [".VnTime"]},  # TCVN3 -> "àá"
        {"type": "paragraph", "text": "viparse® 2026", "fonts": ["Arial"]},  # Unicode, keep
    ]
    raw = _raw_blocks(blocks, [".VnTime", "Arial"], text="µ¸\nviparse® 2026")
    nd = VietnameseNormalizer().normalize(raw, LoadOptions())
    assert nd.blocks == [Paragraph(text="àá"), Paragraph(text="viparse® 2026")]
    assert nd.text == "àá\nviparse® 2026"  # flat text rebuilt from the per-block conversions
    assert nd.encoding_detected == "tcvn3"
    assert nd.encoding_confidence == pytest.approx(0.95)


def test_mixed_document_rebuilds_flat_text_including_a_table() -> None:
    # A legacy table beside a Unicode paragraph: the rebuilt flat text keeps the table's
    # tab-joined rows and leaves the Unicode block (with its "®") untouched.
    blocks = [
        {"type": "table", "rows": [["µ¸", "¶·"]], "fonts": [".VnTime"]},  # TCVN3
        {"type": "paragraph", "text": "viparse® 2026", "fonts": ["Arial"]},  # Unicode
    ]
    raw = _raw_blocks(blocks, [".VnTime", "Arial"])
    nd = VietnameseNormalizer().normalize(raw, LoadOptions())
    assert nd.blocks == [Table(rows=[["àá", "ảã"]]), Paragraph(text="viparse® 2026")]
    assert nd.text == "àá\tảã\nviparse® 2026"
    assert nd.encoding_detected == "tcvn3"


def test_mixed_two_legacy_encodings_convert_independently() -> None:
    blocks = [
        {"type": "paragraph", "text": "µ¸", "fonts": [".VnTime"]},  # TCVN3 -> "àá"
        {"type": "paragraph", "text": "aù", "fonts": ["VNI-Times"]},  # VNI -> "á"
    ]
    raw = _raw_blocks(blocks, [".VnTime", "VNI-Times"])
    nd = VietnameseNormalizer().normalize(raw, LoadOptions())
    assert nd.blocks == [Paragraph(text="àá"), Paragraph(text="á")]
    assert any("multiple legacy encodings across blocks" in w for w in nd.warnings)


def test_uniform_blocks_are_not_treated_as_mixed() -> None:
    # Every block resolves to the same encoding → the whole-document path runs, so the
    # flat text stays the engine's own flattening (not rebuilt from the blocks).
    blocks = [
        {"type": "paragraph", "text": "µ¸", "fonts": [".VnTime"]},
        {"type": "paragraph", "text": "¶·", "fonts": [".VnTime"]},
    ]
    raw = _raw_blocks(blocks, [".VnTime"], text="ENGINE-FLAT")
    nd = VietnameseNormalizer().normalize(raw, LoadOptions())
    assert nd.blocks == [Paragraph(text="àá"), Paragraph(text="ảã")]
    assert nd.text == "ENGINE-FLAT"  # whole-document path keeps the engine's flat text
    assert not any("per block" in w for w in nd.warnings)


def test_legacy_block_beside_fontless_block_inherits_document_verdict() -> None:
    # A block with no font signal inherits the document-level encoding; when the only
    # font signal is legacy, the document is uniform (not mixed) and converts as one.
    blocks = [
        {"type": "paragraph", "text": "µ¸", "fonts": [".VnTime"]},
        {"type": "paragraph", "text": "¶·"},  # no per-block fonts
    ]
    raw = _raw_blocks(blocks, [".VnTime"], text="µ¸\n¶·")
    nd = VietnameseNormalizer().normalize(raw, LoadOptions())
    assert nd.blocks == [Paragraph(text="àá"), Paragraph(text="ảã")]
    assert nd.encoding_detected == "tcvn3"


def test_encoding_override_still_applies_to_every_block() -> None:
    # An explicit override is a whole-document decision and must ignore per-block fonts.
    blocks = [
        {"type": "paragraph", "text": "aù", "fonts": ["Arial"]},
        {"type": "paragraph", "text": "aï", "fonts": ["Times New Roman"]},
    ]
    raw = _raw_blocks(blocks, ["Arial", "Times New Roman"])
    nd = VietnameseNormalizer().normalize(raw, LoadOptions(encoding="vni"))
    assert nd.encoding_detected == "vni"
    assert nd.blocks == [Paragraph(text="á"), Paragraph(text="ạ")]


def test_mixed_dominant_encoding_only_on_inherited_blocks_does_not_crash() -> None:
    # The dominant encoding (tcvn3) reaches the document only by inheritance: the one
    # font-bearing block is VNI, while two fontless blocks inherit the document verdict
    # (a real shape when a legacy run sits in an empty paragraph that yields no block).
    # Confidence must fall back to the document-level detection, not reduce over an empty
    # set — which would raise ValueError and abort the load.
    blocks = [
        {"type": "paragraph", "text": "aù", "fonts": ["VNI-Times"]},  # VNI -> "á"
        {"type": "paragraph", "text": "µ¸"},  # no fonts -> inherits tcvn3
        {"type": "paragraph", "text": "¶·"},  # no fonts -> inherits tcvn3
    ]
    raw = _raw_blocks(blocks, [".VnTime", "VNI-Times"], text="aù\nµ¸\n¶·")
    nd = VietnameseNormalizer().normalize(raw, LoadOptions())
    assert nd.blocks == [Paragraph(text="á"), Paragraph(text="àá"), Paragraph(text="ảã")]
    assert nd.encoding_detected == "tcvn3"
    assert nd.encoding_confidence == pytest.approx(0.6)  # inherited from the doc verdict


def test_mixed_flat_text_is_cleaned_like_the_single_encoding_path() -> None:
    # A trailing block that normalizes to an empty line must not leave a dangling blank
    # line in the flat text: the mixed path re-cleans the joined text the same way the
    # single-encoding path cleans raw.text (trailing-newline strip, blank-run cap).
    blocks = [
        {"type": "paragraph", "text": "µ¸", "fonts": [".VnTime"]},  # TCVN3 -> "àá"
        {"type": "paragraph", "text": "viparse® 2026", "fonts": ["Arial"]},  # Unicode
        {"type": "paragraph", "text": "   ", "fonts": ["Arial"]},  # collapses to empty
    ]
    raw = _raw_blocks(blocks, [".VnTime", "Arial"])
    nd = VietnameseNormalizer().normalize(raw, LoadOptions())
    assert nd.text == "àá\nviparse® 2026"  # trailing blank line stripped, not "…2026\n"


# --- Per-run detection within a single block (SPEC-3 T3.2.4, VIP-72) ---


def test_mixed_runs_within_a_paragraph_convert_by_their_own_encoding() -> None:
    # One paragraph mixing a legacy TCVN3 run with a Unicode run whose text contains "®"
    # (also a TCVN3 surface byte for đ). Whole-block conversion would corrupt "viparse®";
    # per-run detection converts only the legacy run.
    blocks = [
        {
            "type": "paragraph",
            "text": "µ¸ viparse® 2026",
            "runs": [
                {"text": "µ¸", "font": ".VnTime"},  # TCVN3 -> "àá"
                {"text": " viparse® 2026", "font": "Arial"},  # Unicode, keep the "®"
            ],
        }
    ]
    raw = _raw_blocks(blocks, [".VnTime", "Arial"], text="µ¸ viparse® 2026")
    nd = VietnameseNormalizer().normalize(raw, LoadOptions())
    assert nd.blocks == [Paragraph(text="àá viparse® 2026")]
    assert nd.text == "àá viparse® 2026"
    assert nd.encoding_detected == "tcvn3"
    assert nd.encoding_confidence == pytest.approx(0.95)


def test_mixed_runs_within_a_heading_convert_per_run() -> None:
    blocks = [
        {
            "type": "heading",
            "level": 2,
            "text": "µ ONE",
            "runs": [
                {"text": "µ", "font": ".VnTime"},  # TCVN3 -> "à"
                {"text": " ONE", "font": "Arial"},  # Unicode
            ],
        }
    ]
    raw = _raw_blocks(blocks, [".VnTime", "Arial"], text="µ ONE")
    nd = VietnameseNormalizer().normalize(raw, LoadOptions())
    assert nd.blocks == [Heading(level=2, text="à ONE")]


def test_uniform_runs_block_is_converted_whole_not_split_at_run_boundary() -> None:
    # A legacy multi-character form ("aù" = VNI for "á") split across two same-encoding
    # runs must convert as a whole — splitting it per run would sever the base+mark pair.
    # A neighbouring Unicode block makes the document mixed so the per-segment path runs.
    blocks = [
        {
            "type": "paragraph",
            "text": "aù",
            "runs": [
                {"text": "a", "font": "VNI-Times"},
                {"text": "ù", "font": "VNI-Times"},
            ],
        },
        {"type": "paragraph", "text": "® x", "runs": [{"text": "® x", "font": "Arial"}]},
    ]
    raw = _raw_blocks(blocks, ["VNI-Times", "Arial"], text="aù\n® x")
    nd = VietnameseNormalizer().normalize(raw, LoadOptions())
    assert nd.blocks == [Paragraph(text="á"), Paragraph(text="® x")]  # not "aù"
    assert nd.encoding_detected == "vni"


def test_runs_not_reconstructing_text_fall_back_to_block_level() -> None:
    # If a block's runs don't concatenate back to its text (e.g. hyperlink/field text the
    # run list omits), the normalizer distrusts the runs and converts the block whole from
    # its block-level font signal instead.
    blocks = [
        {
            "type": "paragraph",
            "text": "µ¸",  # TCVN3 -> "àá"
            "fonts": [".VnTime"],
            "runs": [{"text": "MISMATCH", "font": ".VnTime"}],  # != "µ¸"
        },
        {"type": "paragraph", "text": "viparse", "fonts": ["Arial"]},  # Unicode → mixed doc
    ]
    raw = _raw_blocks(blocks, [".VnTime", "Arial"], text="µ¸\nviparse")
    nd = VietnameseNormalizer().normalize(raw, LoadOptions())
    assert nd.blocks == [Paragraph(text="àá"), Paragraph(text="viparse")]


def test_uniform_runs_document_is_not_treated_as_mixed() -> None:
    # Every run agrees on one encoding → the whole-document path runs (flat text stays the
    # engine's own flattening), exactly as for a document with no per-run signal.
    blocks = [
        {"type": "paragraph", "text": "µ¸", "runs": [{"text": "µ¸", "font": ".VnTime"}]},
        {"type": "paragraph", "text": "¶·", "runs": [{"text": "¶·", "font": ".VnTime"}]},
    ]
    raw = _raw_blocks(blocks, [".VnTime"], text="ENGINE-FLAT")
    nd = VietnameseNormalizer().normalize(raw, LoadOptions())
    assert nd.blocks == [Paragraph(text="àá"), Paragraph(text="ảã")]
    assert nd.text == "ENGINE-FLAT"  # whole-document path keeps the engine's flat text


def test_same_encoding_digraph_split_across_runs_survives_in_a_mixed_block() -> None:
    # Inside an internally-mixed block, a legacy base+mark form ("aù" = VNI "á") split
    # across two same-encoding runs must still convert as one: consecutive same-encoding
    # runs are coalesced before conversion, so the sequence is never severed at a boundary.
    blocks = [
        {
            "type": "paragraph",
            "text": "aù® x",
            "runs": [
                {"text": "a", "font": "VNI-Times"},  # base, run 1
                {"text": "ù", "font": "VNI-Times"},  # mark, run 2 (same encoding)
                {"text": "® x", "font": "Arial"},  # Unicode run → block is mixed
            ],
        }
    ]
    raw = _raw_blocks(blocks, ["VNI-Times", "Arial"], text="aù® x")
    nd = VietnameseNormalizer().normalize(raw, LoadOptions())
    assert nd.blocks == [Paragraph(text="á® x")]  # "aù"→"á" recomposed, "®" preserved


def test_dominant_encoding_is_weighted_by_block_not_by_run_count() -> None:
    # A VNI paragraph (one run) and a TCVN3 paragraph a formatting change fragmented into
    # three runs. The dominant encoding is decided per block (1 vs 1, tie broken by
    # document order → vni), never by run count (which would wrongly pick tcvn3 3-to-1).
    blocks = [
        {"type": "paragraph", "text": "aù", "runs": [{"text": "aù", "font": "VNI-Times"}]},
        {
            "type": "paragraph",
            "text": "µ¸¶",
            "runs": [
                {"text": "µ", "font": ".VnTime"},
                {"text": "¸", "font": ".VnTime"},
                {"text": "¶", "font": ".VnTime"},
            ],
        },
    ]
    raw = _raw_blocks(blocks, ["VNI-Times", ".VnTime"], text="aù\nµ¸¶")
    nd = VietnameseNormalizer().normalize(raw, LoadOptions())
    assert nd.blocks == [Paragraph(text="á"), Paragraph(text="àáả")]
    assert nd.encoding_detected == "vni"  # block-weighted, not run-count (which is tcvn3)


# Both cases: the moat must recompose upper- and lower-case Vietnamese letters alike.
_VIETNAMESE_REPERTOIRE = sorted(
    set(_VIETNAMESE_ACCENTED) | {ch.upper() for ch in _VIETNAMESE_ACCENTED}
)


@pytest.mark.parametrize("char", _VIETNAMESE_REPERTOIRE)
def test_nfc_nfd_roundtrip_for_all_accented_vowels(char: str) -> None:
    """Feeding the NFD form of each Vietnamese vowel yields the NFC precomposed form."""
    nfd = unicodedata.normalize("NFD", char)
    nd = VietnameseNormalizer().normalize(_raw(nfd, ["Arial"]), LoadOptions())
    assert nd.text == char
    assert unicodedata.is_normalized("NFC", nd.text)
