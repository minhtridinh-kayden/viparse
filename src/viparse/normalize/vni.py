"""VNI (VNI-Windows / ``VNI-Times`` fonts) → Unicode conversion table.

VNI is a **composite** encoding: a toned Vietnamese vowel is stored as a base
Latin letter followed by one or two mark characters from the upper byte range.
When extracted, those surface as a base letter plus the matching Latin-1/CP1252
characters, so the conversion sequences here are multi-character (e.g. ``a`` +
mark → ``á``). The framework matches longest sequences first, so ``aù`` is
converted before a bare ``a`` is ever considered.

.. warning::
   **Provenance / validation.** The *legacy mark* characters below follow the
   standard VNI-Windows layout but were transcribed without an authoritative
   charset file (unavailable in this environment). The Unicode *targets* are
   exact. Validate the source column against an authoritative VNI reference (see
   the ``add-encoding`` skill, step 1) before production use.

Only well-established sequences are included for now; the table grows as entries
are validated. Unmatched characters pass through unchanged.
"""

from __future__ import annotations

from viparse.normalize.tables import Charmap, build_charmap

ENCODING_NAME = "vni"

# VNI surface sequence (base letter + mark) → Unicode Vietnamese letter (NFC).
_ENTRIES = [
    ("a½", "à"),  # a + grave
    ("aù", "á"),  # a + acute
    ("aû", "ả"),  # a + hook
    ("aõ", "ã"),  # a + tilde
    ("aï", "ạ"),  # a + dot below
    ("ñ", "đ"),  # d with stroke
]

VNI: Charmap = build_charmap(ENCODING_NAME, _ENTRIES)
