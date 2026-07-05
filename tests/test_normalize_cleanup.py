"""Tests for the Vietnamese text cleanup step."""

from __future__ import annotations

import unicodedata

from viparse.normalize.cleanup import clean_text


def test_normalizes_line_endings() -> None:
    assert clean_text("a\r\nb\rc") == "a\nb\nc"


def test_strips_control_characters() -> None:
    assert clean_text("a\x00b\x07c") == "abc"


def test_strips_zero_width_and_format_characters() -> None:
    # zero-width space, soft hyphen, and BOM are invisible format characters.
    dirty = "a​b­c﻿d"
    assert clean_text(dirty) == "abcd"


def test_collapses_horizontal_whitespace() -> None:
    assert clean_text("a    b  c") == "a b c"


def test_normalizes_non_breaking_space() -> None:
    assert clean_text("a b") == "a b"


def test_strips_leading_and_trailing_spaces_per_line() -> None:
    assert clean_text("  hello  \n  world  ") == "hello\nworld"


def test_preserves_tabs_as_cell_separators() -> None:
    assert clean_text("A\tB\tC") == "A\tB\tC"


def test_preserves_block_newlines() -> None:
    assert clean_text("Heading\nParagraph\nRow1\tRow2") == "Heading\nParagraph\nRow1\tRow2"


def test_caps_blank_line_runs() -> None:
    assert clean_text("a\n\n\n\nb") == "a\n\nb"


def test_trims_leading_and_trailing_blank_lines() -> None:
    assert clean_text("\n\n  content  \n\n") == "content"


def test_leaves_vietnamese_text_intact() -> None:
    assert clean_text("Tiếng Việt") == "Tiếng Việt"


def test_output_is_nfc_even_when_stripping_unblocks_composition() -> None:
    # A zero-width space between a base letter and a combining acute accent blocks
    # composition; stripping it must not leave the text denormalized.
    dirty = "a​́"
    result = clean_text(dirty)
    assert result == "á"
    assert unicodedata.is_normalized("NFC", result)


def test_respects_requested_normalize_form() -> None:
    result = clean_text("Việt", normalize_form="NFD")
    assert result == unicodedata.normalize("NFD", "Việt")
    assert not unicodedata.is_normalized("NFC", result)


def test_form_feed_becomes_a_block_boundary() -> None:
    # Form feed marks a page break; it must separate content, not glue it together.
    assert clean_text("end of page one.\x0cStart of page two.") == (
        "end of page one.\nStart of page two."
    )


def test_vertical_tab_becomes_a_block_boundary() -> None:
    assert clean_text("a\x0bb") == "a\nb"
