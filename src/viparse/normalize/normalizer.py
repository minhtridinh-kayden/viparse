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

**Per-block detection (SPEC-3 T3.2.4).** When the engine attaches a per-block font
signal (``block["fonts"]``) and those blocks disagree — a genuinely *mixed-encoding*
document, e.g. a legacy ``.VnTime`` paragraph next to a Unicode one — each block is
detected and converted with *its own* encoding, so a Unicode run is never mangled by
a neighbour's legacy charmap. When the blocks agree (the common single-encoding case)
the whole-document path runs unchanged, keeping output byte-for-byte identical. Within
a single block the granularity is still whole-block; per-run splitting is a further
refinement.
"""

from __future__ import annotations

import unicodedata
from collections import Counter
from typing import Any

from viparse.model import Block, Heading, NormalizedDoc, Paragraph, RawExtraction, Table
from viparse.normalize.cleanup import clean_text
from viparse.normalize.detector import (
    EncodingDetection,
    detect_encoding,
    detect_encoding_by_content,
)
from viparse.normalize.encodings import AUTO_DETECT_CHARMAPS, get_charmap
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


def _block_text(block: Block) -> list[str]:
    """The flat line(s) a typed block contributes, mirroring ``_shared.blocks_to_text``."""
    if isinstance(block, Table):
        return ["\t".join(row) for row in block.rows]
    return [block.text]  # Heading | Paragraph


def _flatten(blocks: list[Block]) -> str:
    """Rebuild flat text from already-normalized blocks (used only on the mixed path)."""
    return "\n".join(line for block in blocks for line in _block_text(block))


def _dominant_encoding(legacy_encodings: list[str]) -> str:
    """The most common encoding; document order breaks ties. Input must be non-empty."""
    counts = Counter(legacy_encodings)
    best = max(counts.values())
    return next(enc for enc in legacy_encodings if counts[enc] == best)


class VietnameseNormalizer:
    """Detects a legacy encoding, converts it to Unicode, and enforces NFC."""

    def normalize(self, raw: RawExtraction, options: LoadOptions) -> NormalizedDoc:
        # `.get(...) or []` guards both a missing key and an explicit None value.
        fonts = raw.signals.get("fonts") or []
        raw_blocks = raw.signals.get("blocks") or []
        warnings: list[str] = list(raw.warnings)  # carry the extract stage's warnings forward
        form = options.normalize_form

        override = options.encoding
        encoding: str | None
        if override and override != _AUTO_ENCODING:
            encoding = override
            confidence = _OVERRIDE_CONFIDENCE
        elif raw.signals.get("native_unicode"):
            # The engine already produced Unicode (e.g. OCR): there is no legacy encoding
            # to detect, so skip detection and its low-confidence warning entirely.
            encoding = None
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
                    clean_text(raw.text, form), AUTO_DETECT_CHARMAPS
                )

            # Per-block path: only when the engine tagged blocks with their own fonts and
            # those blocks resolve to different encodings (a real mixed-encoding document).
            per_block = self._normalize_mixed_blocks(raw_blocks, detection, form, warnings)
            if per_block is not None:
                blocks, text, encoding, confidence = per_block
                self._warn_low_confidence(confidence, warnings)
                return self._build(raw, text, encoding, confidence, warnings, blocks)

            encoding = detection.encoding
            confidence = detection.confidence
            if detection.method == "font-signal-mixed":
                warnings.append(
                    f"multiple legacy encodings detected; converting all as {encoding!r}"
                )

        charmap = self._charmap(encoding, warnings)

        # The flat text stays the engine's own flat representation (raw.text), just
        # encoding-converted and NFC-cleaned — the normalizer never second-guesses the
        # engine's flattening. Structural blocks (headings/tables) are normalized in
        # parallel so the renderer can preserve them; both use the same per-field path.
        text = _normalize_text(raw.text, charmap, form)
        blocks = [_normalize_block(b, charmap, form) for b in raw_blocks] if raw_blocks else []

        self._warn_low_confidence(confidence, warnings)
        return self._build(raw, text, encoding, confidence, warnings, blocks)

    def _normalize_mixed_blocks(
        self,
        raw_blocks: list[dict[str, Any]],
        doc_detection: EncodingDetection,
        form: NormalizeForm,
        warnings: list[str],
    ) -> tuple[list[Block], str, str | None, float] | None:
        """Convert each block by its own font signal, or ``None`` if not a mixed document.

        A block carrying ``fonts`` is detected on its own; a block without inherits the
        document-level verdict. When every block resolves to the same encoding the
        document is not mixed and this returns ``None`` so the caller's whole-document
        path (identical output for single-encoding files) runs instead.
        """
        if not any("fonts" in b for b in raw_blocks):
            return None

        # Detect each font-bearing block once and reuse the verdict for both its encoding
        # and its confidence; a block without fonts inherits the document-level verdict.
        detections = [
            detect_encoding(b["fonts"] or []) if "fonts" in b else None for b in raw_blocks
        ]
        block_encodings = [
            d.encoding if d is not None else doc_detection.encoding for d in detections
        ]
        if len(set(block_encodings)) <= 1:
            return None  # blocks agree → not mixed; let the whole-document path handle it

        charmaps = {enc: self._charmap(enc, warnings) for enc in set(block_encodings)}
        blocks = [
            _normalize_block(b, charmaps[enc], form)
            for b, enc in zip(raw_blocks, block_encodings, strict=True)
        ]

        # Flag lossy conversion whenever more than one legacy encoding is in play —
        # across blocks, or within a single block whose own detection is font-signal-mixed.
        legacy_encodings = [enc for enc in block_encodings if enc is not None]
        if len(set(legacy_encodings)) > 1 or any(
            d is not None and d.method == "font-signal-mixed" for d in detections
        ):
            warnings.append("multiple legacy encodings across blocks; converted per block")

        # A mixed document always has at least one legacy block, so a dominant encoding
        # exists. Its confidence is the font-signal confidence of the blocks that resolve
        # to it on their own; when it reaches blocks only by inheriting the document
        # verdict (no block carries it via its own fonts), fall back to that document-level
        # confidence so the min() below never runs over an empty set.
        encoding = _dominant_encoding(legacy_encodings)
        own_confidences = [
            d.confidence
            for d, enc in zip(detections, block_encodings, strict=True)
            if d is not None and enc == encoding
        ]
        confidence = min(own_confidences) if own_confidences else doc_detection.confidence

        # Re-clean the flattened text as a whole so cross-line rules (blank-run capping,
        # leading/trailing newline stripping) match the single-encoding path's clean_text.
        return blocks, clean_text(_flatten(blocks), form), encoding, confidence

    @staticmethod
    def _charmap(encoding: str | None, warnings: list[str]) -> Charmap | None:
        """Resolve a charmap for ``encoding``, warning once if no table is registered."""
        if encoding is None:
            return None
        charmap = get_charmap(encoding)
        if charmap is None:
            # Reached only via an explicit override for an encoding with no table; the
            # per-block path never lands here (font detection yields registered tables).
            warnings.append(f"no conversion table for encoding {encoding!r}; text left unconverted")
        return charmap

    @staticmethod
    def _warn_low_confidence(confidence: float, warnings: list[str]) -> None:
        if confidence < _LOW_CONFIDENCE:
            warnings.append(f"low encoding-detection confidence ({confidence:.2f})")

    @staticmethod
    def _build(
        raw: RawExtraction,
        text: str,
        encoding: str | None,
        confidence: float,
        warnings: list[str],
        blocks: list[Block],
    ) -> NormalizedDoc:
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
