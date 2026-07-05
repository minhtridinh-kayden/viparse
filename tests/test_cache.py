"""Tests for content-hash caching."""

from __future__ import annotations

from pathlib import Path

from viparse.cache import Cache, DiskCache, MemoryCache, cache_key
from viparse.model import Document, DocumentMetadata
from viparse.options import LoadOptions


def _doc(text: str = "x") -> Document:
    return Document(text=text, metadata=DocumentMetadata(source="s", content_type="t"))


def _file(path: Path, data: bytes) -> Path:
    path.write_bytes(data)
    return path


def test_memory_cache_roundtrip() -> None:
    cache = MemoryCache()
    assert isinstance(cache, Cache)
    assert cache.get("k") is None
    document = _doc()
    cache.set("k", document)
    assert cache.get("k") is document


def test_disk_cache_roundtrip(tmp_path: Path) -> None:
    cache = DiskCache(tmp_path / "cache")
    assert isinstance(cache, Cache)
    assert cache.get("k") is None
    cache.set("k", _doc("hello"))
    restored = cache.get("k")
    assert restored is not None
    assert restored.text == "hello"


def test_disk_cache_corrupt_entry_is_a_miss(tmp_path: Path) -> None:
    cache = DiskCache(tmp_path / "cache")
    cache.set("k", _doc())
    cache._path("k").write_bytes(b"not a valid pickle")  # corrupt the stored entry
    assert cache.get("k") is None


def test_disk_cache_key_cannot_escape_the_directory(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache = DiskCache(cache_dir)
    cache.set("../../evil", _doc("x"))  # a hostile key must not traverse out
    restored = cache.get("../../evil")
    assert restored is not None and restored.text == "x"  # still round-trips within the dir
    assert not (tmp_path.parent / "evil.pickle").exists()  # nothing escaped
    assert list(cache_dir.glob("*.pickle"))  # written inside the cache dir


def test_cache_key_depends_on_content(tmp_path: Path) -> None:
    a = _file(tmp_path / "a.bin", b"one")
    b = _file(tmp_path / "b.bin", b"two")
    options = LoadOptions()
    assert cache_key(a, options) == cache_key(a, options)  # stable
    assert cache_key(a, options) != cache_key(b, options)  # content differs


def test_cache_key_depends_on_source_path(tmp_path: Path) -> None:
    # Byte-identical files at different paths must not share an entry (correct provenance).
    a = _file(tmp_path / "a.bin", b"identical")
    b = _file(tmp_path / "b.bin", b"identical")
    assert cache_key(a, LoadOptions()) != cache_key(b, LoadOptions())


def test_cache_key_depends_on_output_options(tmp_path: Path) -> None:
    path = _file(tmp_path / "a.bin", b"same")
    assert cache_key(path, LoadOptions(fmt="markdown")) != cache_key(path, LoadOptions(fmt="json"))
    assert cache_key(path, LoadOptions()) != cache_key(path, LoadOptions(encoding="tcvn3"))
    # None (auto-detect) and the literal string "None" must never collide.
    assert cache_key(path, LoadOptions(encoding=None)) != cache_key(
        path, LoadOptions(encoding="None")
    )


def test_cache_key_ignores_non_output_options(tmp_path: Path) -> None:
    # max_bytes and strict do not change the parsed output, so they must not change the key.
    path = _file(tmp_path / "a.bin", b"same")
    assert cache_key(path, LoadOptions(max_bytes=10)) == cache_key(path, LoadOptions(max_bytes=99))
    assert cache_key(path, LoadOptions(strict=True)) == cache_key(path, LoadOptions(strict=False))
