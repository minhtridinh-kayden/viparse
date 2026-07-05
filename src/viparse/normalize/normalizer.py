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
"""

from __future__ import annotations

import unicodedata

from viparse.model import NormalizedDoc, RawExtraction
from viparse.normalize.cleanup import clean_text
from viparse.normalize.detector import detect_encoding
from viparse.normalize.encodings import get_charmap
from viparse.normalize.tables import convert
from viparse.options import LoadOptions

_OVERRIDE_CONFIDENCE = 1.0
_LOW_CONFIDENCE = 0.75  # below this, surface a warning (SPEC-3 T3.6.2)


class VietnameseNormalizer:
    """Detects a legacy encoding, converts it to Unicode, and enforces NFC."""

    def normalize(self, raw: RawExtraction, options: LoadOptions) -> NormalizedDoc:
        # `.get(...) or []` guards both a missing key and an explicit None value.
        fonts = raw.signals.get("fonts") or []
        warnings: list[str] = list(raw.warnings)  # carry the extract stage's warnings forward

        if options.encoding:
            encoding: str | None = options.encoding
            confidence = _OVERRIDE_CONFIDENCE
        else:
            detection = detect_encoding(fonts)
            encoding = detection.encoding
            confidence = detection.confidence
            if detection.method == "font-signal-mixed":
                warnings.append(
                    f"multiple legacy encodings detected; converting all as {encoding!r}"
                )

        text = raw.text
        converted = False
        if encoding is not None:
            charmap = get_charmap(encoding)
            if charmap is None:
                warnings.append(
                    f"no conversion table for encoding {encoding!r}; text left unconverted"
                )
            else:
                # convert() already applies the normalization form, so no second pass.
                text = convert(text, charmap, options.normalize_form)
                converted = True

        # Enforce the requested form (default NFC) when conversion did not already.
        if not converted:
            text = unicodedata.normalize(options.normalize_form, text)
        # Cleanup can strip format characters that were blocking composition, so it
        # re-normalizes to the requested form as its final step.
        text = clean_text(text, options.normalize_form)
        if confidence < _LOW_CONFIDENCE:
            warnings.append(f"low encoding-detection confidence ({confidence:.2f})")

        return NormalizedDoc(
            source=raw.source,
            content_type=raw.content_type,
            text=text,
            engine=raw.engine,
            encoding_detected=encoding,
            encoding_confidence=confidence,
            warnings=warnings,
        )
