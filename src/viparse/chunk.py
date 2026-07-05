"""RAG chunking: split a normalized document into retrieval-sized pieces (SPEC-4 E4.2).

Chunking works on the **block structure** (headings / paragraphs / table rows), not the
flat text, so it can:

- keep every chunk within a single section — any section change (a heading, or an empty
  heading that merely resets the section) starts a new chunk, so a chunk's ``section``
  metadata is unambiguous (it never straddles a section boundary);
- **never split a table row** — each row is an atomic unit, and a large table is split at
  row boundaries;
- carry per-chunk metadata (``section`` and inherited ``page`` / ``sheet``) plus the
  chunk's ordinal :attr:`~viparse.model.Chunk.index` for downstream provenance.

Token counts are **approximate and tiktoken-free** (whitespace-delimited words), which is
enough to bound chunk size without pinning to any one model's tokenizer. A single block
larger than the target is emitted whole (sub-splitting long paragraphs is a future
refinement); table rows are always kept intact regardless of size.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from viparse.model import Block, Chunk, Heading, NormalizedDoc, Table, blocks_of


@dataclass(frozen=True, slots=True)
class ChunkOptions:
    """Chunking knobs: target size and overlap, both in approximate tokens (words)."""

    max_tokens: int = 512
    overlap_tokens: int = 64


def estimate_tokens(text: str) -> int:
    """Approximate token count for ``text`` (tiktoken-free: whitespace-delimited words)."""
    return len(text.split())


@dataclass(frozen=True, slots=True)
class _Unit:
    """An atomic chunkable piece — a heading, a paragraph, or a single table row."""

    text: str
    section: str
    is_heading: bool


def chunk_document(document: NormalizedDoc, options: ChunkOptions) -> list[Chunk]:
    """Split ``document`` into overlapping, single-section :class:`~viparse.model.Chunk`s."""
    units = list(_iter_units(blocks_of(document)))
    if not units:
        return []

    chunks: list[Chunk] = []
    start = 0
    count = len(units)
    while True:  # always terminates via the `end >= count` break below (count >= 1 here)
        end = start
        tokens = 0
        while end < count:
            if end > start and _crosses_section(units, start, end):
                break  # a new section starts here — never split one across chunks
            unit_tokens = estimate_tokens(units[end].text)
            if end > start and tokens + unit_tokens > options.max_tokens:
                break  # this unit would overflow — leave it for the next chunk
            tokens += unit_tokens
            end += 1
        chunks.append(_make_chunk(units[start:end], len(chunks), document))
        if end >= count:
            break
        # Overlap stays within a section: a section boundary starts the next chunk fresh.
        if _crosses_section(units, start, end):
            start = end
        else:
            start = _next_start(units, start, end, options)
    return chunks


def _crosses_section(units: list[_Unit], start: int, end: int) -> bool:
    """Whether ``units[end]`` opens a new section relative to the chunk started at ``start``.

    True at an explicit heading unit *and* when the section label merely changes (an
    empty-text heading resets the section without emitting a unit of its own), so a chunk
    can never straddle a section boundary regardless of how it was introduced.
    """
    return units[end].is_heading or units[end].section != units[start].section


def _iter_units(blocks: list[Block]) -> Iterator[_Unit]:
    """Flatten blocks into atomic units, tracking the section each unit belongs to."""
    section = ""
    for block in blocks:
        if isinstance(block, Heading):
            section = block.text
            if block.text:
                yield _Unit(text=block.text, section=section, is_heading=True)
        elif isinstance(block, Table):
            for row in block.rows:
                if any(cell.strip() for cell in row):  # skip a row whose every cell is blank
                    yield _Unit(text="\t".join(row), section=section, is_heading=False)
        elif block.text:  # Paragraph
            yield _Unit(text=block.text, section=section, is_heading=False)


def _make_chunk(group: list[_Unit], index: int, document: NormalizedDoc) -> Chunk:
    metadata: dict[str, object] = {
        "section": group[0].section,  # every unit in the group shares one section
        "page": document.page,
        "sheet": document.sheet,
    }
    return Chunk(text="\n".join(unit.text for unit in group), metadata=metadata, index=index)


def _next_start(units: list[_Unit], start: int, end: int, options: ChunkOptions) -> int:
    """Where the next chunk begins: back up from ``end`` to repeat ~``overlap_tokens``.

    Never returns ``<= start``, so the scan always makes progress (an overlap larger than
    the chunk simply repeats everything but the first unit). ``units[start:end]`` share one
    section, so this overlap never crosses a heading boundary.
    """
    cursor = end
    tokens = 0
    while cursor > start + 1 and tokens < options.overlap_tokens:
        cursor -= 1
        tokens += estimate_tokens(units[cursor].text)
    return cursor
