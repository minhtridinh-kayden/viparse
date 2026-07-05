"""Core domain model for viparse.

Plain stdlib dataclasses so that ``core`` stays dependency-free. These types are
the stable contracts that flow between the pipeline layers:

    extract → RawExtraction → normalize → NormalizedDoc → structure → Document

``RawExtraction`` and ``NormalizedDoc`` are internal intermediates; ``Document``
(with its ``Chunk`` list and ``DocumentMetadata``) is the public result of
``viparse.load()``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

SCHEMA_VERSION = "1.0"
"""Version of viparse's stable output contract — the :class:`DocumentMetadata` fields
and the ``json`` renderer's block/metadata payload (SPEC-4 E4.3).

Downstream consumers pin this to depend on the shape stably; it is bumped only on a
breaking change. The chunk-level metadata fields (``section``, ``page``, ``sheet``,
plus the ``Chunk.index`` position) arrive with chunking (SPEC-4 E4.2) as an additive,
non-breaking change.
"""


@dataclass(frozen=True, slots=True)
class Heading:
    """A heading block with a 1-based ``level`` (``Heading 2`` → ``level=2``)."""

    level: int
    text: str


@dataclass(frozen=True, slots=True)
class Paragraph:
    """A body paragraph of normalized (Unicode NFC) text."""

    text: str


@dataclass(frozen=True, slots=True)
class Table:
    """A table as ``rows`` of cell strings (row-major, may be ragged)."""

    # Excluded from __hash__ (a list is unhashable) so the frozen type stays hashable.
    rows: list[list[str]] = field(hash=False)


# The structural blocks a renderer consumes, in document order. Kept deliberately
# small (heading/paragraph/table) — the moat is normalization, not layout fidelity.
Block = Heading | Paragraph | Table


@dataclass(frozen=True, slots=True)
class DocumentMetadata:
    """Provenance and detection metadata attached to a :class:`Document`.

    This is the document-level half of viparse's standardized, versioned metadata
    schema (SPEC-4 E4.3, versioned by :data:`SCHEMA_VERSION`):

    - ``source`` / ``content_type`` — where the document came from and its detected type;
    - ``page`` / ``sheet`` — location within a paginated or multi-sheet source;
    - ``lang`` — detected language;
    - ``encoding_detected`` / ``encoding_confidence`` — the Vietnamese normalization
      layer's outcome (the moat);
    - ``engine`` — the adapter that extracted the text;
    - ``warnings`` — non-fatal issues (e.g. a page that failed under lenient mode);
    - ``extra`` — an escape hatch for engine/format-specific fields that must not
      widen the stable schema.

    The chunk-level metadata fields (``section``, ``page``, ``sheet``) live on each
    :class:`Chunk`'s ``metadata`` and are populated by the chunker (SPEC-4 E4.2); a
    chunk's position is its ``Chunk.index``.
    """

    source: str
    content_type: str
    page: int | None = None
    sheet: str | None = None
    lang: str | None = None
    encoding_detected: str | None = None
    encoding_confidence: float | None = None
    engine: str | None = None
    # Mutable containers are excluded from the generated __hash__ (they are
    # unhashable) so these frozen types stay honestly hashable — usable as set
    # members / dict keys for dedup and caching — while __eq__ still compares them.
    warnings: list[str] = field(default_factory=list, hash=False)
    extra: dict[str, Any] = field(default_factory=dict, hash=False)


@dataclass(frozen=True, slots=True)
class Chunk:
    """A retrieval-sized piece of a :class:`Document`.

    Shaped for LangChain/LlamaIndex interop: ``text`` maps to their
    ``page_content`` and ``metadata`` is a free-form dict. ``index`` is the
    chunk's position within its parent document (0-based).
    """

    # Field order matches SPEC-1 T1.1.2: Chunk(text, metadata, index).
    text: str
    metadata: dict[str, Any] = field(hash=False)
    index: int


@dataclass(frozen=True, slots=True)
class Document:
    """The parsed result for one source document.

    ``text`` is the full normalized (Unicode NFC) text; ``chunks`` is an
    optional retrieval-oriented split, populated only when chunking is requested.
    Field names mirror LangChain/LlamaIndex document shapes so conversion is trivial.
    """

    text: str
    metadata: DocumentMetadata
    chunks: list[Chunk] = field(default_factory=list, hash=False)


@dataclass(frozen=True, slots=True)
class RawExtraction:
    """Raw output of an :class:`Engine`, before Vietnamese normalization.

    Carries the extracted ``text`` plus the raw ``signals`` the normalizer needs
    to detect a legacy encoding (e.g. run font names like ``.VnTime``, embedded
    charset hints). No encoding conversion or NFC is applied here — that is the
    normalizer's job.
    """

    source: str
    content_type: str
    text: str
    engine: str | None = None
    page: int | None = None
    sheet: str | None = None
    signals: dict[str, Any] = field(default_factory=dict, hash=False)
    warnings: list[str] = field(default_factory=list, hash=False)


@dataclass(frozen=True, slots=True)
class NormalizedDoc:
    """Output of a :class:`Normalizer`: text converted to Unicode **NFC**.

    Records what the normalization layer decided (``encoding_detected`` and its
    ``encoding_confidence`` in ``[0, 1]``, detected ``lang``) so the renderer can
    project these onto :class:`DocumentMetadata`. ``text`` is the normalized flat
    text; ``blocks`` is the same content as ordered structural blocks (empty when
    the engine supplied no block structure), which the renderer uses to emit
    markdown/JSON that preserves headings and tables.
    """

    source: str
    content_type: str
    text: str
    engine: str | None = None
    page: int | None = None
    sheet: str | None = None
    lang: str | None = None
    encoding_detected: str | None = None
    encoding_confidence: float | None = None
    warnings: list[str] = field(default_factory=list, hash=False)
    blocks: list[Block] = field(default_factory=list, hash=False)


def blocks_of(doc: NormalizedDoc) -> list[Block]:
    """The document's structural blocks, synthesizing one paragraph from flat text.

    A block-less document (an engine that only emits text) still yields one paragraph so
    downstream consumers (renderer, chunker) never see an empty structure when there is
    text. This is the single source of that fallback rule — both the renderer and the
    chunker derive their block view from here so they can never disagree.
    """
    if doc.blocks:
        return doc.blocks
    return [Paragraph(text=doc.text)] if doc.text else []
