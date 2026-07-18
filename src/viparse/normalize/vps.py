"""VPS (Vietnamese Professional System) → Unicode conversion table.

Like VISCII, VPS is an 8-bit Vietnamese encoding: it keeps the printable ASCII
characters, repurposes **14 C0 control bytes** (0x02–0x06, 0x10–0x15, 0x19, 0x1C,
0x1D) for uppercase precomposed letters, and fills much of 0x80–0xFF with the
remaining Vietnamese letters. When VPS bytes are read as Latin-1, each byte ``0xNN``
surfaces as ``chr(0xNN)``; this table maps every byte VPS assigns *differently* from
Latin-1 back to the correct Vietnamese letter (Unicode, then NFC). Bytes VPS shares
with Latin-1 (Á Â É Ê, à á â ã, è é ê, ì í, ò ó ô õ, ù ú) are omitted and pass through.

Provenance: the byte → Unicode mapping is cross-verified across four independent
sources — the Vietnamese Unicode project chart at
``http://vietunicode.sourceforge.net/charset/`` (``vps.gif``), the ICU/Encode::VN
``x-viet-vps.ucm``, the R package ``jniedballa/vietnameseConverter`` (itself adapted
from vietunicode), and ``vuthaihoc/py-unicode-convert``. Every one of the 112 bytes
below is corroborated by at least two of those lineages; the one known upstream typo
(``vietnameseConverter`` v2 rendering 0xF1 as U+00D0 Ð) is overruled in favour of the
value the other three agree on, U+0110 (Đ).

.. note::
   Like VISCII, this table keys on the **Latin-1** surface form (byte ``0xNN`` →
   ``chr(0xNN)``). The caveat is sharper for VPS: it uses 0x80–0x9F heavily, exactly
   where Latin-1 and CP1252 diverge and where CP1252 leaves 0x81/0x8D/0x8F/0x90/0x9D
   undefined. A future engine that decodes *raw* legacy bytes must therefore decode
   VPS content as Latin-1 (or key conversion on the raw bytes); decoding as CP1252
   would surface those bytes as different glyphs (or replacement characters) this
   table cannot match, silently passing the letter through unconverted.

.. note::
   VPS converts only via an explicit ``encoding="vps"`` override — it is **excluded**
   from content-frequency auto-detection (see ``AUTO_DETECT_CHARMAPS``). It shares
   VISCII's Latin-1 surface bytes but maps them to different letters, so auto-detecting
   it would risk mis-converting genuine VISCII text; and because it encodes uppercase
   letters as C0 control bytes that cleanup strips before detection, auto-detection of
   VPS is unreliable anyway.
"""

from __future__ import annotations

from viparse.normalize.tables import Charmap, build_charmap

ENCODING_NAME = "vps"

# (VPS byte, Unicode code point) for every byte VPS maps differently from Latin-1:
# the 14 repurposed C0 controls, then the differing bytes across 0x80–0xFF. Kept as
# integers so the cross-verified data cannot be silently mistyped as look-alike glyphs.
_BYTE_TO_CODEPOINT: list[tuple[int, int]] = [
    # 14 repurposed C0 control bytes → uppercase precomposed letters.
    (0x02, 0x1EA0),
    (0x03, 0x1EAC),
    (0x04, 0x1EB6),
    (0x05, 0x1EB8),
    (0x06, 0x1EC6),
    (0x10, 0x1ECA),
    (0x11, 0x1ECC),
    (0x12, 0x1ED8),
    (0x13, 0x1EE2),
    (0x14, 0x1EE4),
    (0x15, 0x1EF0),
    (0x19, 0x1EF4),
    (0x1C, 0x1EAA),
    (0x1D, 0x1EEE),
    # 0x80–0xFF: every byte VPS assigns differently from Latin-1.
    (0x80, 0x00C0),
    (0x81, 0x1EA2),
    (0x82, 0x00C3),
    (0x83, 0x1EA4),
    (0x84, 0x1EA6),
    (0x85, 0x1EA8),
    (0x86, 0x1ECD),
    (0x87, 0x1ED7),
    (0x88, 0x0102),
    (0x89, 0x1EBF),
    (0x8A, 0x1EC1),
    (0x8B, 0x1EC3),
    (0x8C, 0x1EC7),
    (0x8D, 0x1EAE),
    (0x8E, 0x1EB0),
    (0x8F, 0x1EB2),
    (0x90, 0x1EBE),
    (0x93, 0x1EC0),
    (0x94, 0x1EC2),
    (0x95, 0x1EC4),
    (0x96, 0x1ED0),
    (0x97, 0x1ED2),
    (0x98, 0x1ED4),
    (0x99, 0x1ED6),
    (0x9A, 0x00FD),
    (0x9B, 0x1EF7),
    (0x9C, 0x1EF5),
    (0x9D, 0x1EDA),
    (0x9E, 0x1EDC),
    (0x9F, 0x1EDE),
    (0xA1, 0x1EAF),
    (0xA2, 0x1EB1),
    (0xA3, 0x1EB3),
    (0xA4, 0x1EB5),
    (0xA5, 0x1EB7),
    (0xA6, 0x1EE0),
    (0xA7, 0x1EDB),
    (0xA8, 0x00D9),
    (0xA9, 0x1EDD),
    (0xAA, 0x1EDF),
    (0xAB, 0x1EE1),
    (0xAC, 0x0168),
    (0xAD, 0x1EE8),
    (0xAE, 0x1EE3),
    (0xAF, 0x1EEA),
    (0xB0, 0x1ED5),
    (0xB1, 0x1EEC),
    (0xB2, 0x1EF2),
    (0xB3, 0x1EF8),
    (0xB4, 0x00CD),
    (0xB5, 0x00CC),
    (0xB6, 0x1ED9),
    (0xB7, 0x1EC8),
    (0xB8, 0x0128),
    (0xB9, 0x00D3),
    (0xBA, 0x1EED),
    (0xBB, 0x1EEF),
    (0xBC, 0x00D2),
    (0xBD, 0x1ECE),
    (0xBE, 0x00D5),
    (0xBF, 0x1EF1),
    (0xC0, 0x1EA7),
    (0xC3, 0x1EA5),
    (0xC4, 0x1EA9),
    (0xC5, 0x1EAB),
    (0xC6, 0x1EAD),
    (0xC7, 0x0111),
    (0xC8, 0x1EBB),
    (0xCB, 0x1EB9),
    (0xCC, 0x1EC9),
    (0xCD, 0x1EC5),
    (0xCE, 0x1ECB),
    (0xCF, 0x1EF9),
    (0xD0, 0x01AF),
    (0xD1, 0x1EE6),
    (0xD2, 0x1ED3),
    (0xD3, 0x1ED1),
    (0xD5, 0x1ECF),
    (0xD6, 0x01A1),
    (0xD7, 0x00C8),
    (0xD8, 0x1EEB),
    (0xD9, 0x1EE9),
    (0xDB, 0x0169),
    (0xDC, 0x01B0),
    (0xDE, 0x1EBA),
    (0xE4, 0x1EA3),
    (0xE5, 0x1EA1),
    (0xE6, 0x0103),
    (0xEB, 0x1EBD),
    (0xEF, 0x0129),
    (0xF0, 0x1EB4),
    (0xF1, 0x0110),
    (0xF7, 0x01A0),
    (0xF8, 0x1EE5),
    (0xFB, 0x1EE7),
    (0xFD, 0x1EF6),
    (0xFE, 0x1EBC),
    (0xFF, 0x1EF3),
]

_ENTRIES = [(chr(byte), chr(codepoint)) for byte, codepoint in _BYTE_TO_CODEPOINT]

VPS: Charmap = build_charmap(ENCODING_NAME, _ENTRIES)
