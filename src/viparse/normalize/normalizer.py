"""The concrete Vietnamese Normalizer: detect → convert → NFC.

``VietnameseNormalizer`` implements the :class:`~viparse.protocols.Normalizer`
Protocol and is the moat's entry point in the pipeline. For each extraction it:

1. determines the source encoding — an explicit ``options.encoding`` override wins,
   otherwise the font-signal :func:`~viparse.normalize.detector.detect_encoding`;
2. converts legacy text to Unicode via the matching
   :class:`~viparse.normalize.tables.Charmap` (a no-op when the text is Unicode);
3. enforces the requested normalization form (**NFC** by default);
4. records ``encoding_detected`` / ``encoding_confidence`` and warns on low
   confidence or mixed encodings (SPEC-3 E3.6).

The same conversion is applied per structural block (``signals["blocks"]``) so the
renderer receives normalized headings/paragraphs/tables, with the flat ``text``
derived from them; when the engine supplies no blocks, the flat text is normalized
directly and ``blocks`` stays empty.
"""

from __future__ import annotations

import unicodedata
from typing import Any

from viparse.model import Block, Heading, NormalizedDoc, Paragraph, RawExtraction, Table
from viparse.normalize.cleanup import clean_text
from viparse.normalize.detector import detect_encoding, detect_encoding_by_content
from viparse.normalize.encodings import CHARMAPS, get_charmap
from viparse.normalize.tables import Charmap, convert
from viparse.options import LoadOptions, NormalizeForm

_OVERRIDE_CONFIDENCE = 1.0
_LOW_CONFIDENCE = 0.75  # below this, surface a warning (SPEC-3 T3.6.2)
_AUTO_ENCODING = "auto"  # opt-in sentinel for content-based detection (SPEC-3 E3.2)


def _normalize_text(text: str, charmap: Charmap | None, form: NormalizeForm) -> str:
    """Convert legacy bytes to Unicode (when a charmap applies), enforce ``form``, clean up."""
    if charmap is not None:
        text = convert(text, charmap, form)
    else:
        text = unicodedata.normalize(form, text)
    return clean_text(text, form)


def _normalize_block(block: dict[str, Any], charmap: Charmap | None, form: NormalizeForm) -> Block:
    """Normalize one raw engine block into its typed, Unicode-NFC counterpart.

    Field access is defensive (``.get`` with defaults) so a slightly off-contract
    block from a third-party engine degrades to a best-effort block instead of
    raising a bare ``KeyError``/``TypeError`` — which would bypass the pipeline's
    ViparseError-only lenient-mode handling and crash the run.
    """
    kind = block.get("type")
    if kind == "heading":
        level = block.get("level")
        text = _normalize_text(block.get("text", ""), charmap, form)
        return Heading(level=int(level) if level else 1, text=text)
    if kind == "table":
        rows = block.get("rows") or []
        cells = [[_normalize_text(cell, charmap, form) for cell in row] for row in rows]
        return Table(rows=cells)
    return Paragraph(text=_normalize_text(block.get("text", ""), charmap, form))


class VietnameseNormalizer:
    """Detects a legacy encoding, converts it to Unicode, and enforces NFC."""

    def normalize(self, raw: RawExtraction, options: LoadOptions) -> NormalizedDoc:
        # `.get(...) or []` guards both a missing key and an explicit None value.
        fonts = raw.signals.get("fonts") or []
        warnings: list[str] = list(raw.warnings)  # carry the extract stage's warnings forwa

        override = options.encoding
        if override and override != _AUTO_ENCODING:
            encoding: str | None = override
            confidence = _OVERRIDE_CONFIDENCE
        else:
            detection = detect_encoding(fonts)
            if override == _AUTO_ENCODING and detection.method == "assumed-unicode":
                # Opt-in content detection (SPEC-3 E3.2): only when the caller passed
                # encoding="auto" AND there is no font signal. It is NOT the default,
                # because character-frequency scoring can misclassify non-Vietnamese text
                # (e.g. Spanish "señor") as legacy and corrupt it — the moat's cardinal
                # sin. The caller opting in asserts the source is legacy Vietnamese. The
                # text is cleaned first so control-character noise cannot dilute the score.
                detection = detect_encoding_by_content(
                    clean_text(raw.text, options.normalize_form), CHARMAPS
                )
            encoding = detection.encoding
            confidence = detection.confidence
            if detection.method == "font-signal-mixed":
                warnings.append(
                    f"multiple legacy encodings detected; converting all as {encoding!r}"
                )

        charmap: Charmap | None = None
        if encoding is not None:
            charmap = get_charmap(encoding)
            if charmap is None:
                warnings.append(
                    f"no conversion table for encoding {encoding!r}; text left unconverted"
                )

        # The flat text stays the engine's own flat representation (raw.text), just
        # encoding-converted and NFC-cleaned — the normalizer never second-guesses the
        # engine's flattening. Structural blocks (headings/tables) are normalized in
        # parallel so the renderer can preserve them; both use the same per-field path.
        text = _normalize_text(raw.text, charmap, options.normalize_form)
        raw_blocks = raw.signals.get("blocks")
        blocks: list[Block] = (
            [_normalize_block(b, charmap, options.normalize_form) for b in raw_blocks]
            if raw_blocks
            else []
        )

        if confidence < _LOW_CONFIDENCE:
            warnings.append(f"low encoding-detection confidence ({confidence:.2f})")

        return NormalizedDoc(
            source=raw.source,
            content_type=raw.content_type,
            text=text,
            engine=raw.engine,
            page=raw.page,  # carry the engine's location provenance through to metadata
            sheet=raw.sheet,
            encoding_detected=encoding,
            encoding_confidence=confidence,
            warnings=warnings,
            blocks=blocks,
        )
