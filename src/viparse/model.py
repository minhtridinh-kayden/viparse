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


@dataclass(frozen=True, slots=True)
class DocumentMetadata:
    """Provenance and detection metadata attached to a :class:`Document`.

    ``encoding_detected``/``encoding_confidence`` record the outcome of the
    Vietnamese normalization layer; ``engine`` names the adapter that extracted
    the text. ``extra`` holds engine- or format-specific fields without
    widening this schema.
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
    optional retrieval-oriented split produced by the renderer. Field names
    mirror LangChain/LlamaIndex document shapes so conversion is trivial.
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
    project these onto :class:`DocumentMetadata`.
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
