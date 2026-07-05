"""Tests for the public load / load_batch API (extract → normalize → render, end to end)."""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path

import pytest

from viparse import load, load_batch
from viparse.model import Document

docx = pytest.importorskip("docx")  # python-docx; skipped without the office extra


def _write_docx(path: Path, text: str, font: str | None = None) -> Path:
    document = docx.Document()
    run = document.add_paragraph().add_run(text)
    if font is not None:
        run.font.name = font
    document.save(str(path))
    return path


def test_load_returns_single_document_list_in_nfc(tmp_path: Path) -> None:
    path = _write_docx(tmp_path / "a.docx", "Tiếng Việt")
    result = load(path)
    assert isinstance(result, list) and len(result) == 1
    doc = result[0]
    assert isinstance(doc, Document)
    assert doc.text == "Tiếng Việt"  # markdown default: a lone paragraph is plain text
    assert unicodedata.is_normalized("NFC", doc.text)
    assert doc.metadata.engine == "docx"


def test_load_output_json(tmp_path: Path) -> None:
    path = _write_docx(tmp_path / "a.docx", "Xin chào")
    (doc,) = load(path, output="json")
    payload = json.loads(doc.text)
    assert payload["schema_version"] == "1.0"
    assert payload["blocks"] == [{"type": "paragraph", "text": "Xin chào"}]


def test_load_encoding_override_converts_legacy(tmp_path: Path) -> None:
    # TCVN3 surface bytes rendered with a legacy font; forcing the encoding converts them.
    path = _write_docx(tmp_path / "legacy.docx", "µ¸¶·¹", font=".VnTime")
    (doc,) = load(path, output="text", encoding="tcvn3")
    assert doc.text == "àáảãạ"
    assert doc.metadata.encoding_detected == "tcvn3"


def test_load_respects_normalize_form(tmp_path: Path) -> None:
    path = _write_docx(tmp_path / "a.docx", "Việt")
    (doc,) = load(path, output="text", normalize="NFD")
    assert doc.text == unicodedata.normalize("NFD", "Việt")
    assert not unicodedata.is_normalized("NFC", doc.text)


def test_load_batch_is_lazy_and_yields_per_source(tmp_path: Path) -> None:
    a = _write_docx(tmp_path / "a.docx", "Một")
    b = _write_docx(tmp_path / "b.docx", "Hai")
    batch = load_batch([a, b], output="text")
    assert iter(batch) is batch  # a generator, not a materialized list
    results = list(batch)
    assert [r[0].text for r in results] == ["Một", "Hai"]


def test_load_rejects_oversized_input(tmp_path: Path) -> None:
    from viparse.errors import UnsafeInput

    path = _write_docx(tmp_path / "a.docx", "Xin chào")
    with pytest.raises(UnsafeInput):
        load(path, max_bytes=10)


def test_load_cache_hit_skips_parsing(tmp_path: Path) -> None:
    from viparse import MemoryCache
    from viparse.cache import cache_key
    from viparse.model import Document, DocumentMetadata
    from viparse.options import LoadOptions

    path = _write_docx(tmp_path / "a.docx", "real content")
    cache = MemoryCache()
    sentinel = Document(text="FROM CACHE", metadata=DocumentMetadata(source="x", content_type="y"))
    cache.set(cache_key(path, LoadOptions()), sentinel)  # LoadOptions() matches load() defaults
    (doc,) = load(path, cache=cache)
    assert doc.text == "FROM CACHE"  # returned the cache, never parsed "real content"


def test_load_populates_cache_on_miss(tmp_path: Path) -> None:
    from viparse import MemoryCache
    from viparse.cache import cache_key
    from viparse.options import LoadOptions

    path = _write_docx(tmp_path / "a.docx", "Tài liệu")
    cache = MemoryCache()
    (doc,) = load(path, cache=cache)
    assert doc.text == "Tài liệu"
    assert cache.get(cache_key(path, LoadOptions())) is doc
