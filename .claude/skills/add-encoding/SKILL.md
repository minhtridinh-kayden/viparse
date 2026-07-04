---
name: add-encoding
description: Scaffold a legacy Vietnamese encoding table (e.g. TCVN3, VNI, VISCII) plus its golden test, so the normalizer can convert that encoding to Unicode NFC. Use when adding or correcting support for a legacy font/encoding.
---

# Add a legacy encoding

Legacy Vietnamese documents store text in font-specific encodings (TCVN3 `.VnTime`, VNI
`VNI-Times`, VISCII, …). The normalization layer maps those bytes/codepoints to correct Unicode
and enforces **NFC**. This is the product's moat, so correctness is verified by **golden tests**.

Follow these steps.

## 1. Gather an authoritative mapping

- Find a reputable source for the encoding→Unicode mapping (published charset tables, the font's
  documented layout). Record the source in a comment.
- Note how the encoding is detected: font name signal from the engine, byte-range heuristics, or an
  explicit caller hint.

## 2. Add the table

Create `src/viparse/normalize/tables/<encoding>.py` (or the project's table location) as a plain,
reviewable mapping. Keep it data, not logic — the shared conversion routine consumes any table.

- Map every codepoint the encoding uses, including composed diacritic forms.
- The conversion output must be normalized to **NFC** by the shared normalizer, not per-table.

## 3. Wire detection

Register the encoding so the normalizer selects it from the engine's raw signals (e.g. font name).
Do not guess from the file extension.

## 4. Add a golden test

- Add an input fixture in the legacy encoding and an expected Unicode **NFC** output fixture under
  `tests/` (synthetic text — no sensitive documents).
- Assert the converted output equals the golden output **and** that it is NFC
  (`unicodedata.is_normalized("NFC", out)`).
- Include diacritic-heavy words (e.g. "Việt", "Nguyễn", "Đường") to catch composition bugs.

## 5. Verify

Run `scripts/dev.sh`. Open one PR titled `VIP-<id> Add <encoding> encoding`.

## Checklist

- [ ] Mapping sourced from an authoritative reference (cited in a comment)
- [ ] Table is data-only; conversion reuses the shared routine
- [ ] Output enforced to Unicode NFC
- [ ] Detection wired from engine signals, not the extension
- [ ] Golden test with diacritic-heavy input asserts exact NFC output
- [ ] `scripts/dev.sh` passes
