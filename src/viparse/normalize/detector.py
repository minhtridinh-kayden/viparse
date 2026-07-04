"""Legacy-encoding detector.

Chooses which conversion table (if any) applies to extracted text. The MVP relies
on the **font-name signal** the extraction engine attaches (SPEC-3 T3.2.2): a
``.Vn*`` font implies TCVN3, a ``VNI*`` font implies VNI. Frequency- and
dictionary-based detection (T3.2.1 / T3.2.3) and per-block detection (T3.2.4) are
future refinements for sources that carry no font information.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from viparse.normalize.tcvn3 import ENCODING_NAME as TCVN3_NAME
from viparse.normalize.vni import ENCODING_NAME as VNI_NAME

# Confidence for each detection outcome.
_FONT_CONFIDENCE = 0.95  # a single legacy font family is a strong, direct signal
_MIXED_CONFIDENCE = 0.6  # two different legacy encodings present — per-file conversion is lossy
_UNICODE_CONFIDENCE = 0.9  # fonts present but none legacy → almost certainly Unicode
_ASSUMED_CONFIDENCE = 0.5  # no usable font information → Unicode assumed, not confirmed

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
