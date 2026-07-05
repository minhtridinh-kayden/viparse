"""Content-hash caching so unchanged files are not re-parsed (SPEC-7 E7.3).

A cache is keyed by the file's content hash *plus* the options that affect the output
(format, encoding, OCR, normalization) and the :data:`~viparse.model.SCHEMA_VERSION`, so
a changed file, different options, or a new pipeline version all miss the cache and never
serve a stale result. Caching is opt-in — pass a :class:`Cache` to :func:`viparse.load`.

Two stores ship: :class:`MemoryCache` (per-process) and :class:`DiskCache` (persists
across runs). Both satisfy the small :class:`Cache` Protocol, so callers can supply their
own (Redis, S3, …).

.. note::
   The key is computed by hashing the file *before* the pipeline re-reads it to parse, so
   rewriting a file in place *during* a load is a TOCTOU race that can cache the new bytes
   under the old hash. Don't mutate files in place while loading them; write a new file
   (atomic rename) instead.
"""

from __future__ import annotations

import hashlib
import os
import pickle
import tempfile
from pathlib import Path
from typing import Protocol, runtime_checkable

from viparse.model import SCHEMA_VERSION, Document
from viparse.options import LoadOptions
from viparse.protocols import Source

_HASH_CHUNK = 1024 * 1024  # hash the file in 1 MiB chunks (bounded memory)


@runtime_checkable
class Cache(Protocol):
    """A content-addressed store of parsed :class:`Document` results."""

    def get(self, key: str) -> Document | None:
        """Return the cached document for ``key``, or ``None`` on a miss."""
        ...

    def set(self, key: str, document: Document) -> None:
        """Store ``document`` under ``key``."""
        ...


class MemoryCache:
    """A simple in-process cache backed by a dict."""

    def __init__(self) -> None:
        self._store: dict[str, Document] = {}

    def get(self, key: str) -> Document | None:
        return self._store.get(key)

    def set(self, key: str, document: Document) -> None:
        self._store[key] = document


class DiskCache:
    """A cache that persists pickled documents under a directory, one file per key."""

    def __init__(self, directory: Source) -> None:
        self._dir = Path(directory)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        # Hash the key into the filename so an arbitrary key can never traverse out of the
        # cache directory, and any string is a valid (fixed-length, filesystem-safe) name.
        name = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self._dir / f"{name}.pickle"

    def get(self, key: str) -> Document | None:
        try:
            with self._path(key).open("rb") as fh:
                # Trusted input: the cache directory holds only this library's own writes.
                document: Document = pickle.load(fh)
        except FileNotFoundError:
            return None  # a plain miss
        except Exception:  # noqa: BLE001 — any corrupt/unreadable entry is treated as a miss
            return None
        return document

    def set(self, key: str, document: Document) -> None:
        # Write to a temp file in the same directory, then atomically rename into place, so
        # a crash or a concurrent writer never leaves a half-written entry to be read back.
        fd, tmp = tempfile.mkstemp(dir=self._dir, suffix=".tmp")
        with os.fdopen(fd, "wb") as fh:
            pickle.dump(document, fh)
        os.replace(tmp, self._path(key))


def cache_key(source: Source, options: LoadOptions) -> str:
    """A stable key from the file's content hash, its path, and the output-affecting options.

    The path is part of the key so a hit only ever returns the document parsed from *that*
    source (its ``metadata.source`` stays correct — two byte-identical files never share an
    entry). The options are fingerprinted with :func:`repr` of a tuple so ``None`` and the
    string ``"None"`` (and any field containing a delimiter) can never collide. ``max_bytes``
    and ``strict`` are omitted because they do not change the parsed output; ``chunk`` is
    included because it changes the document (its ``chunks``), and its frozen ``repr`` is stable.
    """
    digest = hashlib.sha256()
    with Path(source).open("rb") as fh:
        for block in iter(lambda: fh.read(_HASH_CHUNK), b""):
            digest.update(block)
    fingerprint = repr(
        (
            str(source),
            SCHEMA_VERSION,
            options.fmt,
            options.encoding,
            options.ocr,
            options.normalize_form,
            options.chunk,
        )
    )
    digest.update(fingerprint.encode("utf-8"))
    return digest.hexdigest()
