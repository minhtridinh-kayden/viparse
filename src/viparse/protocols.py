"""Layer interfaces for the viparse pipeline, as PEP 544 Protocols.

Each pipeline layer is defined *structurally*: a third-party implementation only
has to match the shape, with no base class to inherit (SPEC-1 §6). The data
contracts they exchange are the domain types in :mod:`viparse.model`:

    Engine.extract → RawExtraction → Normalizer.normalize → NormalizedDoc
        → Renderer.render → Document

The Protocols are ``runtime_checkable`` so the router/registry and tests can
``isinstance``-check implementations structurally.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

from viparse.model import Document, NormalizedDoc, RawExtraction

Source = str | Path
"""A document source: a filesystem path as ``str`` or :class:`~pathlib.Path`."""

OutputFormat = Literal["text", "markdown", "json"]
"""Supported renderer output formats."""

DEFAULT_PRIORITY = 100
"""Neutral baseline priority for an engine that has no strong preference."""


@runtime_checkable
class Engine(Protocol):
    """Extracts raw text and encoding/font signals from a source document.

    Engines are thin adapters over a well-maintained parse library. They carry
    **no** Vietnamese logic — they only extract text and attach the raw signals
    (font names, embedded charset hints) that the normalizer needs.
    """

    #: Selection priority when several engines support a content type; higher
    #: wins, with :data:`DEFAULT_PRIORITY` as the neutral baseline. This is a
    #: value attribute, not a method — set it as a class or instance attribute
    #: (a method here would pass the structural check but break priority sorting).
    priority: int

    def supports(self, content_type: str) -> bool:
        """Return ``True`` if this engine can extract the given content type."""
        ...

    def extract(self, source: Source) -> RawExtraction:
        """Extract raw text and signals from ``source`` into a RawExtraction."""
        ...


@runtime_checkable
class Normalizer(Protocol):
    """Converts a :class:`RawExtraction` to Unicode **NFC** text.

    This is where the Vietnamese layer lives: detect a legacy encoding
    (TCVN3/VNI/VISCII) from the raw signals, convert to Unicode, and enforce NFC.
    """

    def normalize(self, raw: RawExtraction) -> NormalizedDoc:
        """Normalize raw extracted text to a Unicode-NFC :class:`NormalizedDoc`."""
        ...


@runtime_checkable
class Renderer(Protocol):
    """Renders a :class:`NormalizedDoc` into the final :class:`Document`."""

    def render(self, doc: NormalizedDoc, fmt: OutputFormat = "markdown") -> Document:
        """Assemble the final Document, projecting the normalizer's detection
        results onto :class:`DocumentMetadata` and serializing the text per
        ``fmt``: ``"text"`` emits plain text, ``"markdown"`` preserves structure
        (headings, tables, lists), ``"json"`` a structured payload. Any chunking
        is applied here.
        """
        ...
