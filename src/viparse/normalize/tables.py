"""Shared framework for legacy Vietnamese encoding → Unicode conversion.

A legacy encoding (TCVN3, VNI, VISCII) is described by a :class:`Charmap`: an
ordered set of *(legacy sequence → Unicode replacement)* pairs. When a document
is authored in a legacy font, extraction yields the **font's** code points as
ordinary Unicode characters — e.g. the TCVN3 byte ``0xB5`` surfaces as U+00B5
``µ``. Converting means replacing each legacy sequence with the correct
Vietnamese character, then normalizing to NFC.

Matching is greedy and longest-first, so a multi-character legacy form (VNI
encodes a toned vowel as *base + mark*) is matched before any shorter sequence
that is its prefix. Conversion is a single left-to-right scan, so a replacement's
output can never be re-matched as another sequence's input.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from functools import cache

from viparse.options import NormalizeForm


@dataclass(frozen=True)
class Charmap:
    """An immutable legacy-encoding → Unicode conversion table.

    ``pairs`` are ``(legacy_sequence, unicode_replacement)`` tuples, pre-sorted
    longest sequence first. Build one with :func:`build_charmap` rather than
    constructing it directly, so the ordering and validation invariants hold.
    """

    name: str
    pairs: tuple[tuple[str, str], ...]


def build_charmap(name: str, entries: Iterable[tuple[str, str]]) -> Charmap:
    """Build a :class:`Charmap` from ``(legacy_sequence, unicode)`` pairs.

    A list of pairs (rather than a dict literal) lets this function catch a
    duplicated legacy sequence — a dict would silently collapse it. Raises
    ``ValueError`` on an empty source, an empty replacement (which would delete
    the character), or a duplicate legacy sequence (an ambiguous table).
    """
    seen: set[str] = set()
    pairs: list[tuple[str, str]] = []
    for legacy_seq, replacement in entries:
        if not legacy_seq:
            raise ValueError(f"{name}: legacy sequence must not be empty")
        if not replacement:
            raise ValueError(f"{name}: replacement for {legacy_seq!r} must not be empty")
        if legacy_seq in seen:
            raise ValueError(f"{name}: duplicate legacy sequence {legacy_seq!r}")
        seen.add(legacy_seq)
        pairs.append((legacy_seq, replacement))
    pairs.sort(key=lambda pair: len(pair[0]), reverse=True)
    return Charmap(name=name, pairs=tuple(pairs))


@cache
def _first_char_index(charmap: Charmap) -> dict[str, tuple[tuple[str, str], ...]]:
    """Group a charmap's pairs by their first character (cached per charmap)."""
    grouped: dict[str, list[tuple[str, str]]] = {}
    for legacy_seq, replacement in charmap.pairs:
        grouped.setdefault(legacy_seq[0], []).append((legacy_seq, replacement))
    return {first: tuple(items) for first, items in grouped.items()}


def convert(text: str, charmap: Charmap, normalize_form: NormalizeForm = "NFC") -> str:
    """Convert legacy-encoded ``text`` to Unicode using ``charmap``, then normalize.

    A single left-to-right scan replaces each matched legacy sequence (longest
    first) with its Unicode form; unmatched characters pass through unchanged.
    """
    index = _first_char_index(charmap)
    out: list[str] = []
    position = 0
    length = len(text)
    while position < length:
        char = text[position]
        for legacy_seq, replacement in index.get(char, ()):
            if text.startswith(legacy_seq, position):
                out.append(replacement)
                position += len(legacy_seq)
                break
        else:
            out.append(char)
            position += 1
    return unicodedata.normalize(normalize_form, "".join(out))
