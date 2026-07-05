"""Shared mapping from a viparse :class:`Document` to framework-agnostic records.

Both the LangChain and LlamaIndex adapters project a document the same way — the only
difference is the concrete type they wrap each ``(text, metadata)`` record in — so that
projection lives here once.
"""

from __future__ import annotations

import copy
from typing import Any

from viparse.model import Document, DocumentMetadata


def _metadata_dict(metadata: DocumentMetadata) -> dict[str, Any]:
    """Flatten :class:`DocumentMetadata` into a plain dict for a framework's metadata field."""
    record: dict[str, Any] = {
        "source": metadata.source,
        "content_type": metadata.content_type,
        "page": metadata.page,
        "sheet": metadata.sheet,
        "lang": metadata.lang,
        "encoding_detected": metadata.encoding_detected,
        "encoding_confidence": metadata.encoding_confidence,
        "engine": metadata.engine,
    }
    if metadata.warnings:
        record["warnings"] = list(metadata.warnings)
    record.update(metadata.extra)  # engine/format-specific escape-hatch fields
    return record


def document_records(document: Document) -> list[tuple[str, dict[str, Any]]]:
    """The ``(text, metadata)`` records to emit for ``document``.

    One record per :class:`~viparse.model.Chunk` when the document has been chunked (each
    carrying the document provenance plus the chunk's own ``section`` / ``page`` / ``sheet``
    and its ordinal ``chunk_index``), otherwise a single record for the whole document.

    Each record's metadata is deep-copied so nested mutables (the ``warnings`` list, any
    ``extra`` values) are independent — a caller mutating one document's metadata in place
    never bleeds into the source document or a sibling chunk.
    """
    base = _metadata_dict(document.metadata)
    if not document.chunks:
        return [(document.text, copy.deepcopy(base))]
    return [
        (chunk.text, copy.deepcopy({**base, **chunk.metadata, "chunk_index": chunk.index}))
        for chunk in document.chunks
    ]
