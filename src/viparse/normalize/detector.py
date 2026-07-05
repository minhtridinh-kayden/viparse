"""Legacy-encoding detector.

Chooses which conversion table (if any) applies to extracted text. The primary,
highest-confidence signal is the **font name** the extraction engine attaches
(SPEC-3 T3.2.2): a ``.Vn*`` font implies TCVN3, a ``VNI*`` font implies VNI.

:func:`detect_encoding_by_content` adds a **content-frequency** heuristic (T3.2.1 /
T3.2.3) — trial-convert and score against a Vietnamese character model — for sources
with no font signal. It is deliberately **not** run by default: a character model
cannot reliably tell legacy Vietnamese from other diacritic-heavy Latin text (Spanish
``ñ``, German ``ß``), so applying it automatically would risk corrupting good text —
the moat's cardinal sin. The normalizer invokes it only when the caller opts in with
``encoding="auto"``, thereby asserting the source is legacy Vietnamese.

Per-block detection for mixed-encoding documents (T3.2.4) remains a future refinement;
detection runs on the whole text, which is also more reliable than scoring a short
block in isolation.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from viparse.normalize.frequency import vietnamese_score
from viparse.normalize.tables import Charmap, convert
from viparse.normalize.tcvn3 import ENCODING_NAME as TCVN3_NAME
from viparse.normalize.vni import ENCODING_NAME as VNI_NAME

# Confidence for each detection outcome.
_FONT_CONFIDENCE = 0.95  # a single legacy font family is a strong, direct signal
_MIXED_CONFIDENCE = 0.6  # two different legacy encodings present — per-file conversion is lossy
_UNICODE_CONFIDENCE = 0.9  # fonts present but none legacy → almost certainly Unicode
_ASSUMED_CONFIDENCE = 0.5  # no usable font information → Unicode assumed, not confirmed

# Content detection thresholds. A legacy decode is accepted only when it both beats
# leaving the text unconverted by _CONTENT_MARGIN *and* clearly separates from the
# next-best table by _CONTENT_SEPARATION — otherwise the input is ambiguous (several
# tables yield plausible Vietnamese) and guessing would risk corrupting good text.
_CONTENT_MARGIN = 0.15
_CONTENT_SEPARATION = 0.05
_CONTENT_BASE_CONFIDENCE = 0.5
_CONTENT_MAX_CONFIDENCE = 0.85  # content evidence never reaches font-signal certainty

# PDF embeds subsetted fonts under a 6-uppercase-letter tag, e.g. "ABCDEF+.VnTime".
_SUBSET_TAG = re.compile(r"^[A-Z]{6}\+")


@dataclass(frozen=True, slots=True)
class EncodingDetection:
    """The detector's verdict for a piece of text.

    ``encoding`` is the charmap name to convert with, or ``None`` when the text is
    taken to be already Unicode. ``confidence`` is in ``[0, 1]``; ``method`` records
    how the verdict was reached; ``font`` is the font that triggered a legacy match.
    """

    encoding: str | None
    confidence: float
    method: str
    font: str | None = None


def _encoding_for_font(font: str) -> str | None:
    """Map a font name to a legacy encoding, or ``None`` if it is not a legacy font."""
    name = _SUBSET_TAG.sub("", font).upper()
    if name.startswith(".VN"):  # .VnTime, .VnArial, .VnTimeH, .vntime, …
        return TCVN3_NAME
    if name.startswith("VNI"):  # VNI-Times, VNI-Helve, vni-times, …
        return VNI_NAME
    return None


def detect_encoding(fonts: Iterable[str | None]) -> EncodingDetection:
    """Detect the legacy encoding of extracted text from its font-name signals.

    A single legacy font family wins with high confidence (mixed documents commonly
    interleave one legacy font with plain Latin runs). When *two different* legacy
    encodings appear, per-file conversion cannot be right for both, so the first is
    chosen but flagged with low confidence (real per-block handling is T3.2.4). With
    usable fonts present but none legacy, the text is Unicode with high confidence;
    with no usable font information, Unicode is assumed.
    """
    detected: dict[str, str] = {}  # encoding -> first font that implied it
    usable = False
    for font in fonts:
        if not font:
            continue
        usable = True
        encoding = _encoding_for_font(font)
        if encoding is not None and encoding not in detected:
            detected[encoding] = font

    if len(detected) == 1:
        encoding, font = next(iter(detected.items()))
        return EncodingDetection(encoding, _FONT_CONFIDENCE, "font-signal", font)
    if len(detected) > 1:
        encoding, font = next(iter(detected.items()))
        return EncodingDetection(encoding, _MIXED_CONFIDENCE, "font-signal-mixed", font)
    if usable:
        return EncodingDetection(None, _UNICODE_CONFIDENCE, "no-legacy-font")
    return EncodingDetection(None, _ASSUMED_CONFIDENCE, "assumed-unicode")


def detect_encoding_by_content(text: str, candidates: Mapping[str, Charmap]) -> EncodingDetection:
    """Detect a legacy encoding from the text itself, for sources with no font signal.

    Each candidate charmap is trial-applied and its output scored against the Vietnamese
    character model; the charmap whose conversion most improves the score over leaving
    the text unconverted wins, provided the gain clears :data:`_CONTENT_MARGIN` (else the
    text is taken to be already Unicode). This breaks ties between tables that both yield
    some Vietnamese letters and catches sparsely-legacy text. Confidence scales with the
    margin but never reaches font-signal certainty (SPEC-3 T3.2.1 / T3.2.3).
    """
    base = vietnamese_score(text)
    ranked = sorted(
        (
            (vietnamese_score(convert(text, charmap)) - base, name)
            for name, charmap in candidates.items()
        ),
        reverse=True,
    )
    best_gain, best_name = ranked[0]
    runner_up_gain = ranked[1][0] if len(ranked) > 1 else 0.0
    if best_gain < _CONTENT_MARGIN or best_gain - runner_up_gain < _CONTENT_SEPARATION:
        # Not clearly one legacy encoding — leave the text as Unicode rather than risk
        # a wrong conversion (the moat's "never corrupt good text" rule).
        return EncodingDetection(None, _ASSUMED_CONFIDENCE, "assumed-unicode")
    confidence = min(_CONTENT_MAX_CONFIDENCE, _CONTENT_BASE_CONFIDENCE + best_gain)
    return EncodingDetection(best_name, confidence, "content-frequency")
