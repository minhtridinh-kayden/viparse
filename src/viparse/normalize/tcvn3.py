"""TCVN3 (ABC / ``.Vn`` fonts) → Unicode conversion table.

TCVN3 is the encoding behind the classic ``.VnTime`` / ``.VnArial`` fonts. Each
Vietnamese glyph occupies a single byte in the upper range; when such a document
is extracted, those bytes surface as the matching Latin-1/CP1252 characters
(e.g. ``0xB5`` → ``µ``). This table maps each of those surface characters back to
the correct Vietnamese letter.

.. warning::
   **Provenance / validation.** The *legacy source* characters below follow the
   standard TCVN3 font layout but were transcribed without an authoritative
   charset file (unavailable in this environment). The Unicode *targets* are
   exact. Before relying on this in production, validate the source column
   against an authoritative TCVN3 reference (see the ``add-encoding`` skill,
   step 1). The conversion framework and NFC guarantee are independently tested.

Only entries whose source byte is well-established are included; the table grows
as entries are validated. Missing characters simply pass through unchanged.
"""

from __future__ import annotations

from viparse.normalize.tables import Charmap, build_charmap

ENCODING_NAME = "tcvn3"

# TCVN3 surface character → Unicode Vietnamese letter (NFC). Uppercase forms use
# separate lead bytes in TCVN3 and are deferred until validated against a source.
_ENTRIES = [
    ("µ", "à"),  # a + grave
    ("¸", "á"),  # a + acute
    ("¶", "ả"),  # a + hook
    ("·", "ã"),  # a + tilde
    ("¹", "ạ"),  # a + dot below
    ("¨", "ă"),  # a + breve
    ("»", "ằ"),  # ă + grave
    ("¾", "ắ"),  # ă + acute
    ("¼", "ẳ"),  # ă + hook
    ("½", "ẵ"),  # ă + tilde
    ("Æ", "ặ"),  # ă + dot below
    ("®", "đ"),  # d with stroke
]

TCVN3: Charmap = build_charmap(ENCODING_NAME, _ENTRIES)
