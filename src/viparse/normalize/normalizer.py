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

**Per-segment detection (SPEC-3 T3.2.4).** Detection runs at the finest granularity the
engine tagged: a **run** when a block carries per-run signals (``block["runs"]``),
otherwise the whole **block** (``block["fonts"]``). When those segments disagree — a
genuinely *mixed-encoding* document, e.g. a legacy ``.VnTime`` run next to a Unicode one,
whether in separate paragraphs or within the *same* paragraph — each segment is detected
and converted with *its own* encoding, so a Unicode run is never mangled by a neighbour's
legacy charmap. When every segment agrees (the common single-encoding case) the
whole-document path runs unchanged, keeping output byte-for-byte identical. A block is only
split run-by-run when its runs actually disagree; even then, consecutive same-encoding runs
are coalesced before conversion, so a legacy multi-character form (base + mark) split across
run boundaries is never severed.

A run's **own** font is trusted: a run tagged with a non-legacy font is taken as already
Unicode and left untouched (never force-converted — this is what preserves the ``®``-style
case), while a run with *no* font inherits the document verdict. The trade-off is deliberate
and moat-aligned — never corrupt good text — so a run explicitly mislabelled with a Unicode
font but holding legacy bytes is left unconverted rather than risk mangling a real Unicode run.
"""

from __future__ import annotations

import unicodedata
from collections import Counter
from dataclasses import dataclass
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


def _convert(text: str, charmap: Charmap | None, form: NormalizeForm) -> str:
    """Encoding-convert to Unicode (or just enforce ``form``) — *without* cleanup.

    Kept separate from :func:`_normalize_text` so per-run pieces can be converted and
    concatenated before a single whole-line ``clean_text`` runs; cleaning each run in
    isolation would collapse whitespace differently across run boundaries.
    """
    if charmap is not None:
        return convert(text, charmap, form)
    return unicodedata.normalize(form, text)


def _normalize_text(text: str, charmap: Charmap | None, form: NormalizeForm) -> str:
    """Convert legacy bytes to Unicode (when a charmap applies), enforce ``form``, clean up."""
    return clean_text(_convert(text, charmap, form), form)


def _typed_para_or_heading(block: dict[str, Any], text: str) -> Block:
    """Build a :class:`Heading` or :class:`Paragraph` from a block dict + normalized text.

    Shared by the whole-block and per-run conversion paths so their heading/paragraph
    construction (level parsing, dispatch) can never drift apart.
    """
    if block.get("type") == "heading":
        level = block.get("level")
        return Heading(level=int(level) if level else 1, text=text)
    return Paragraph(text=text)


def _normalize_block(block: dict[str, Any], charmap: Charmap | None, form: NormalizeForm) -> Block:
    """Normalize one raw engine block into its typed, Unicode-NFC counterpart.

    Field access is defensive (``.get`` with defaults) so a slightly off-contract
    block from a third-party engine degrades to a best-effort block instead of
    raising a bare ``KeyError``/``TypeError`` — which would bypass the pipeline's
    ViparseError-only lenient-mode handling and crash the run.
    """
    if block.get("type") == "table":
        rows = block.get("rows") or []
        cells = [[_normalize_text(cell, charmap, form) for cell in row] for row in rows]
        return Table(rows=cells)
    return _typed_para_or_heading(block, _normalize_text(block.get("text", ""), charmap, form))


# A detection segment: (encoding, confidence, font_based). ``font_based`` marks a verdict
# that came from a real font signal (vs. one inherited from the document-level verdict), so
# only genuine signals feed the aggregated confidence.
_Segment = tuple[str | None, float, bool]


@dataclass
class _BlockPlan:
    """How one raw block will be normalized, plus its detection segments for metadata.

    ``run_encodings`` is set when the block has usable per-run signals (then it drives a
    per-run conversion if the runs disagree); otherwise ``block_encoding`` drives a
    whole-block conversion. ``segments`` is one entry per run (or one for the whole block).
    """

    block: dict[str, Any]
    run_encodings: list[str | None] | None
    block_encoding: str | None
    segments: list[_Segment]
    font_signal_mixed: bool

    @property
    def internally_mixed(self) -> bool:
        """True when the block's own runs resolve to more than one encoding."""
        return self.run_encodings is not None and len(set(self.run_encodings)) > 1

    @property
    def encodings(self) -> list[str | None]:
        """Every encoding this block will convert with (per run, or the single block one)."""
        return self.run_encodings if self.run_encodings is not None else [self.block_encoding]


def _usable_runs(block: dict[str, Any]) -> list[dict[str, Any]] | None:
    """The block's runs iff they faithfully reconstruct its text, else ``None``.

    A mismatch (e.g. text pulled from hyperlinks/fields the run list omits) means per-run
    conversion could drop or reorder characters, so the caller falls back to block level.
    """
    runs: list[dict[str, Any]] | None = block.get("runs")
    if not runs:
        return None
    if "".join(r.get("text", "") for r in runs) != block.get("text", ""):
        return None
    return runs


def _plan_block(block: dict[str, Any], doc: EncodingDetection) -> _BlockPlan:
    """Detect a block at run granularity when it has usable runs, else at block level."""
    runs = _usable_runs(block)
    if runs is not None:
        # A run carries at most one font, so its detection is never ``font-signal-mixed``.
        run_dets = [detect_encoding([r["font"]]) if r.get("font") else None for r in runs]
        run_encs = [d.encoding if d is not None else doc.encoding for d in run_dets]
        segments = [
            (enc, d.confidence if d is not None else doc.confidence, d is not None)
            for enc, d in zip(run_encs, run_dets, strict=True)
        ]
        return _BlockPlan(block, run_encs, None, segments, font_signal_mixed=False)
    det = detect_encoding(block["fonts"] or []) if "fonts" in block else None
    enc = det.encoding if det is not None else doc.encoding
    confidence = det.confidence if det is not None else doc.confidence
    mixed = det is not None and det.method == "font-signal-mixed"
    segment: _Segment = (enc, confidence, det is not None)
    return _BlockPlan(block, None, enc, [segment], font_signal_mixed=mixed)


def _coalesce_runs(
    runs: list[dict[str, Any]], run_encodings: list[str | None]
) -> list[tuple[str | None, str]]:
    """Merge consecutive runs that share an encoding into ``(encoding, text)`` pieces.

    Coalescing before conversion is essential: a legacy multi-character form (VNI/TCVN3
    encode a toned vowel as *base + mark*) that a formatting change split across two
    same-encoding runs must be converted as one piece, or the sequence is severed and
    left as raw bytes. Only a genuine encoding *change* between runs starts a new piece.
    """
    pieces: list[tuple[str | None, str]] = []
    for run, enc in zip(runs, run_encodings, strict=True):
        text = run.get("text", "")
        if pieces and pieces[-1][0] == enc:
            pieces[-1] = (enc, pieces[-1][1] + text)
        else:
            pieces.append((enc, text))
    return pieces


def _normalize_runs(
    block: dict[str, Any],
    run_encodings: list[str | None],
    charmaps: dict[str | None, Charmap | None],
    form: NormalizeForm,
) -> Block:
    """Convert each same-encoding run span of a paragraph/heading, then clean the whole."""
    converted = "".join(
        _convert(text, charmaps[enc], form)
        for enc, text in _coalesce_runs(block["runs"], run_encodings)
    )
    return _typed_para_or_heading(block, clean_text(converted, form))


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
        """Convert each segment by its own font signal, or ``None`` if not a mixed document.

        A run (or a run-less block) carrying a font is detected on its own; a segment
        without inherits the document-level verdict. When every segment resolves to the
        same encoding the document is not mixed and this returns ``None`` so the caller's
        whole-document path (identical output for single-encoding files) runs instead.
        """
        if not any(("fonts" in b or "runs" in b) for b in raw_blocks):
            return None

        plans = [_plan_block(b, doc_detection) for b in raw_blocks]
        segments = [seg for plan in plans for seg in plan.segments]
        if len({enc for enc, _, _ in segments}) <= 1:
            return None  # every segment agrees → not mixed; whole-document path handles it

        needed = {enc for plan in plans for enc in plan.encodings}
        charmaps = {enc: self._charmap(enc, warnings) for enc in needed}
        blocks = [
            _normalize_runs(plan.block, plan.run_encodings, charmaps, form)
            if plan.internally_mixed and plan.run_encodings is not None
            else _normalize_block(plan.block, charmaps[plan.encodings[0]], form)
            for plan in plans
        ]

        # Flag lossy conversion whenever more than one legacy encoding is in play — across
        # segments, or within a single run-less block whose own detection is font-mixed.
        legacy = [enc for enc, _, _ in segments if enc is not None]
        if len(set(legacy)) > 1 or any(plan.font_signal_mixed for plan in plans):
            warnings.append("multiple legacy encodings across blocks; converted per block")

        # The document's dominant encoding is decided by BLOCK, not by run count — a
        # paragraph a formatting change fragmented into many runs must not out-vote a
        # single-run paragraph (that would flip the metadata versus the per-block path).
        # Each block contributes its own dominant legacy encoding, if it has one.
        block_legacy = [
            _dominant_encoding(encs)
            for plan in plans
            if (encs := [enc for enc, _, _ in plan.segments if enc is not None])
        ]
        encoding = _dominant_encoding(block_legacy)

        # Confidence is the font-signal confidence of the segments that resolve to the
        # dominant encoding on their own; when it reaches segments only by inheriting the
        # document verdict (none carries it via its own font), fall back to that
        # document-level confidence so the min() below never runs over an empty set.
        own_confidences = [
            conf for enc, conf, font_based in segments if font_based and enc == encoding
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
