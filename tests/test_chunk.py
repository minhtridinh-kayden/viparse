"""Tests for RAG chunking (SPEC-4 E4.2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from viparse import load
from viparse.cache import cache_key
from viparse.chunk import ChunkOptions, chunk_document, estimate_tokens
from viparse.model import Heading, NormalizedDoc, Paragraph, Table
from viparse.options import LoadOptions


def _doc(*, text: str = "", blocks: list[object] | None = None, **kw: object) -> NormalizedDoc:
    return NormalizedDoc(
        source="a.docx",
        content_type="application/vnd.docx",
        text=text,
        blocks=blocks or [],  # type: ignore[arg-type]
        **kw,  # type: ignore[arg-type]
    )


def test_estimate_tokens_counts_whitespace_words() -> None:
    assert estimate_tokens("một hai  ba\nbốn") == 4
    assert estimate_tokens("") == 0


def test_empty_document_yields_no_chunks() -> None:
    assert chunk_document(_doc(), ChunkOptions()) == []


def test_flat_text_document_falls_back_to_one_paragraph() -> None:
    chunks = chunk_document(_doc(text="hello world"), ChunkOptions())
    assert len(chunks) == 1
    assert chunks[0].text == "hello world"
    assert chunks[0].index == 0


def test_heading_leads_its_section_chunk() -> None:
    doc = _doc(
        text="Intro\naa bb\ncc dd",
        blocks=[Heading(level=1, text="Intro"), Paragraph("aa bb"), Paragraph("cc dd")],
    )
    chunks = chunk_document(doc, ChunkOptions(max_tokens=100))
    assert len(chunks) == 1
    assert chunks[0].text == "Intro\naa bb\ncc dd"
    assert chunks[0].metadata["section"] == "Intro"


def test_heading_boundary_never_mislabels_a_chunk() -> None:
    # The review's repro: a generous budget must NOT merge two sections into one chunk
    # tagged with the first section — each heading starts its own single-section chunk.
    doc = _doc(
        blocks=[
            Heading(level=1, text="Overview"),
            Paragraph("short intro"),
            Heading(level=1, text="Pricing"),
            Paragraph("$99 per month"),
        ]
    )
    chunks = chunk_document(doc, ChunkOptions(max_tokens=100))
    assert [c.metadata["section"] for c in chunks] == ["Overview", "Pricing"]
    assert "$99 per month" in chunks[1].text and "$99 per month" not in chunks[0].text


def test_empty_heading_mid_document_still_breaks_the_section() -> None:
    # An empty heading emits no unit but resets the section; content after it must NOT be
    # mislabeled with the previous section, even under a generous budget.
    doc = _doc(
        blocks=[
            Heading(level=1, text="Overview"),
            Paragraph("aa"),
            Heading(level=1, text=""),  # a blank divider heading resets the section to ""
            Paragraph("bb"),
        ]
    )
    chunks = chunk_document(doc, ChunkOptions(max_tokens=100))
    assert [c.metadata["section"] for c in chunks] == ["Overview", ""]
    assert "bb" in chunks[1].text and "bb" not in chunks[0].text


def test_repeated_same_named_headings_each_start_a_chunk() -> None:
    # Two distinct headings with the same text are separate boundaries (the section label
    # matching must not merge them).
    doc = _doc(
        blocks=[
            Heading(level=1, text="Notes"),
            Paragraph("x"),
            Heading(level=1, text="Notes"),
            Paragraph("y"),
        ]
    )
    chunks = chunk_document(doc, ChunkOptions(max_tokens=100))
    assert [c.text for c in chunks] == ["Notes\nx", "Notes\ny"]


def test_table_row_is_never_split_even_when_over_budget() -> None:
    # A single row of three words with a one-token budget must still emit intact.
    chunks = chunk_document(_doc(blocks=[Table(rows=[["x y z"]])]), ChunkOptions(max_tokens=1))
    assert len(chunks) == 1
    assert chunks[0].text == "x y z"


def test_large_table_splits_at_row_boundaries() -> None:
    rows = [["a", "b"], ["c", "d"], ["e", "f"]]
    chunks = chunk_document(_doc(blocks=[Table(rows=rows)]), ChunkOptions(max_tokens=2))
    # Each row is 2 words == the budget, so every chunk is exactly one whole row.
    assert [c.text for c in chunks] == ["a\tb", "c\td", "e\tf"]


def test_overlap_repeats_trailing_units() -> None:
    doc = _doc(blocks=[Paragraph("a"), Paragraph("b"), Paragraph("c"), Paragraph("d")])
    chunks = chunk_document(doc, ChunkOptions(max_tokens=2, overlap_tokens=1))
    assert [c.text for c in chunks] == ["a\nb", "b\nc", "c\nd"]
    # Indices are contiguous and 0-based.
    assert [c.index for c in chunks] == [0, 1, 2]


def test_no_overlap_still_makes_progress_on_single_unit_chunks() -> None:
    # Each unit alone exceeds the budget, so every chunk is one unit — and the scan must
    # still terminate (the progress guard), covering all units exactly once.
    doc = _doc(blocks=[Paragraph("a a a"), Paragraph("b b b"), Paragraph("c c c")])
    chunks = chunk_document(doc, ChunkOptions(max_tokens=1, overlap_tokens=1))
    assert [c.text for c in chunks] == ["a a a", "b b b", "c c c"]


def test_metadata_inherits_page_and_sheet() -> None:
    doc = _doc(blocks=[Paragraph("cell")], page=7, sheet="Data")
    (chunk,) = chunk_document(doc, ChunkOptions())
    assert chunk.metadata["page"] == 7
    assert chunk.metadata["sheet"] == "Data"


def test_empty_units_are_skipped() -> None:
    # Empty paragraphs contribute no units.
    doc = _doc(blocks=[Paragraph(""), Paragraph("real"), Paragraph("")])
    (chunk,) = chunk_document(doc, ChunkOptions())
    assert chunk.text == "real"


def test_empty_heading_and_all_blank_table_rows_contribute_no_units() -> None:
    # An empty heading still (re)sets the section but emits no unit; an all-blank table
    # row is dropped regardless of its column count (no phantom tab-only unit leaks in).
    doc = _doc(
        blocks=[
            Heading(level=1, text=""),
            Paragraph("body"),
            Table(rows=[["kept"], ["", ""], [" "]]),  # multi-cell + whitespace-only blanks
        ],
    )
    (chunk,) = chunk_document(doc, ChunkOptions())
    assert chunk.text == "body\nkept"
    assert chunk.metadata["section"] == ""


# --- Integration through the public API ------------------------------------------------


def _docx_fixture(path: Path) -> Path:
    docx = pytest.importorskip("docx")
    document = docx.Document()
    document.add_heading("Tiêu đề", level=1)
    for i in range(20):
        document.add_paragraph(f"Đoạn văn số {i} với vài từ tiếng Việt.")
    document.save(str(path))
    return path


def test_load_without_chunk_leaves_document_unchunked(tmp_path: Path) -> None:
    (document,) = load(_docx_fixture(tmp_path / "a.docx"))
    assert document.chunks == []


def test_load_with_chunk_populates_chunks(tmp_path: Path) -> None:
    (document,) = load(
        _docx_fixture(tmp_path / "a.docx"), chunk=ChunkOptions(max_tokens=8, overlap_tokens=2)
    )
    assert len(document.chunks) > 1  # 20 paragraphs at 8 tokens each → several chunks
    assert [c.index for c in document.chunks] == list(range(len(document.chunks)))
    assert all(c.metadata["section"] == "Tiêu đề" for c in document.chunks)


def test_cache_key_distinguishes_chunked_from_unchunked(tmp_path: Path) -> None:
    path = _docx_fixture(tmp_path / "a.docx")
    plain = cache_key(path, LoadOptions())
    chunked = cache_key(path, LoadOptions(chunk=ChunkOptions()))
    assert plain != chunked
