"""Tests for the output renderers (text / markdown / json)."""

from __future__ import annotations

import json
import unicodedata

from viparse.model import Heading, NormalizedDoc, Paragraph, Table
from viparse.structure.renderer import SCHEMA_VERSION, DocumentRenderer


def _doc(**kwargs: object) -> NormalizedDoc:
    base: dict[str, object] = {
        "source": "a.docx",
        "content_type": "application/vnd.docx",
        "text": "",
    }
    base.update(kwargs)
    # kwargs are widened to `object` for a flexible factory; the callers below always
    # pass correctly-typed values, so mypy cannot verify the **splat here.
    return NormalizedDoc(**base)  # type: ignore[arg-type]


def test_text_renderer_returns_flat_text() -> None:
    doc = _doc(text="Xin chào\nthế giới", blocks=[Paragraph("Xin chào"), Paragraph("thế giới")])
    result = DocumentRenderer().render(doc, "text")
    assert result.text == "Xin chào\nthế giới"


def test_markdown_renders_headings_at_their_level() -> None:
    doc = _doc(blocks=[Heading(1, "Title"), Heading(3, "Sub")])
    assert DocumentRenderer().render(doc, "markdown").text == "# Title\n\n### Sub"


def test_markdown_clamps_heading_level_between_one_and_six() -> None:
    doc = _doc(blocks=[Heading(0, "Too small"), Heading(9, "Too big")])
    assert DocumentRenderer().render(doc, "markdown").text == "# Too small\n\n###### Too big"


def test_markdown_renders_gfm_table() -> None:
    doc = _doc(blocks=[Table([["Name", "Age"], ["An", "30"]])])
    expected = "| Name | Age |\n| --- | --- |\n| An | 30 |"
    assert DocumentRenderer().render(doc, "markdown").text == expected


def test_markdown_pads_ragged_table_rows() -> None:
    doc = _doc(blocks=[Table([["A", "B", "C"], ["1"]])])
    expected = "| A | B | C |\n| --- | --- | --- |\n| 1 |  |  |"
    assert DocumentRenderer().render(doc, "markdown").text == expected


def test_markdown_escapes_pipes_and_newlines_in_cells() -> None:
    doc = _doc(blocks=[Table([["a|b", "c\nd"]])])
    expected = "| a\\|b | c<br>d |\n| --- | --- |"
    assert DocumentRenderer().render(doc, "markdown").text == expected


def test_markdown_skips_empty_table() -> None:
    doc = _doc(blocks=[Paragraph("before"), Table([]), Paragraph("after")])
    assert DocumentRenderer().render(doc, "markdown").text == "before\n\nafter"


def test_markdown_falls_back_to_text_as_single_paragraph() -> None:
    doc = _doc(text="just text", blocks=[])
    assert DocumentRenderer().render(doc, "markdown").text == "just text"


def test_markdown_of_empty_document_is_empty() -> None:
    assert DocumentRenderer().render(_doc(text="", blocks=[]), "markdown").text == ""


def test_schema_version_is_a_single_exported_contract() -> None:
    import viparse
    from viparse.model import SCHEMA_VERSION as model_version

    # One source of truth, re-exported publicly and stamped into the JSON payload.
    assert viparse.SCHEMA_VERSION == model_version == SCHEMA_VERSION
    payload = json.loads(
        DocumentRenderer().render(_doc(text="x", blocks=[Paragraph("x")]), "json").text
    )
    assert payload["schema_version"] == viparse.SCHEMA_VERSION


def test_json_has_versioned_schema_and_blocks() -> None:
    doc = _doc(
        text="Title",
        engine="docx",
        encoding_detected="tcvn3",
        encoding_confidence=0.95,
        blocks=[Heading(1, "Title"), Paragraph("Body"), Table([["a", "b"]])],
    )
    payload = json.loads(DocumentRenderer().render(doc, "json").text)
    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["source"] == "a.docx"
    assert payload["engine"] == "docx"
    assert payload["encoding_detected"] == "tcvn3"
    assert payload["encoding_confidence"] == 0.95
    assert payload["blocks"] == [
        {"type": "heading", "level": 1, "text": "Title"},
        {"type": "paragraph", "text": "Body"},
        {"type": "table", "rows": [["a", "b"]]},
    ]


def test_json_clamps_heading_level_like_markdown() -> None:
    # JSON and markdown must agree on heading depth (both clamped to [1, 6]).
    doc = _doc(blocks=[Heading(9, "Deep")])
    payload = json.loads(DocumentRenderer().render(doc, "json").text)
    assert payload["blocks"] == [{"type": "heading", "level": 6, "text": "Deep"}]


def test_json_keeps_vietnamese_literal_and_nfc() -> None:
    doc = _doc(text="Tiếng Việt", blocks=[Paragraph("Tiếng Việt")])
    body = DocumentRenderer().render(doc, "json").text
    assert "Tiếng Việt" in body  # not \u-escaped
    assert unicodedata.is_normalized("NFC", body)


def test_json_falls_back_to_single_paragraph_block() -> None:
    doc = _doc(text="loose text", blocks=[])
    payload = json.loads(DocumentRenderer().render(doc, "json").text)
    assert payload["blocks"] == [{"type": "paragraph", "text": "loose text"}]


def test_json_of_empty_document_has_no_blocks() -> None:
    payload = json.loads(DocumentRenderer().render(_doc(text="", blocks=[]), "json").text)
    assert payload["blocks"] == []


def test_render_projects_detection_metadata() -> None:
    doc = _doc(
        engine="docx",
        lang="vi",
        encoding_detected="vni",
        encoding_confidence=1.0,
        warnings=["heads up"],
    )
    meta = DocumentRenderer().render(doc, "text").metadata
    assert meta.source == "a.docx"
    assert meta.engine == "docx"
    assert meta.lang == "vi"
    assert meta.encoding_detected == "vni"
    assert meta.encoding_confidence == 1.0
    assert meta.warnings == ["heads up"]


def test_default_format_is_markdown() -> None:
    doc = _doc(blocks=[Heading(2, "H")])
    assert DocumentRenderer().render(doc).text == "## H"
