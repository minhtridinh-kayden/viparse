# SPEC-3 — Vietnamese Normalization Layer ★ MOAT ★

| | |
|---|---|
| **Status** | Draft |
| **Depends on** | S1 |
| **Blocks** | S4 |
| **Milestone** | M1 (TCVN3/VNI + NFC) → M2 (VISCII, good detector) → M4 (diacritic restore) |

## 1. Goal

The part that makes `viparse` **different**: detect legacy encodings (TCVN3/VNI/VISCII), convert
them to Unicode, normalize to **NFC**, and clean up Vietnamese text. This is where we invest the
most testing effort.

## 2. Why this matters
- Old Office documents in Vietnam often use TCVN3 fonts (`.VnTime`, `.VnArial`), VNI (`VNI-Times`),
  or VISCII. When extracted, the bytes map onto the legacy font → garbled characters instead of
  proper diacritics.
- RAG/search without consistent NFC → **silently wrong dedup and search** (e.g. "ế" as one
  codepoint vs `e` + combining marks).

## 3. Scope

**In scope**: static conversion tables, encoding detector, NFC normalizer, text cleanup,
confidence score.
**Out of scope**: extraction (S2), chunk/render (S4). Diacritic restoration is **v2 (optional)**.

## 4. Epics & Tasks

### E3.1 — Static conversion tables
- **T3.1.1** TCVN3 → Unicode table (static data + golden character tests).
- **T3.1.2** VNI → Unicode table.
- **T3.1.3** VISCII → Unicode table.
- **T3.1.4** Shared table framework + `add-encoding` skill to add new tables consistently.

### E3.2 — Encoding detector
- **T3.2.1** Heuristic over byte/character frequency characteristic of each encoding.
- **T3.2.2** Font-name signal from S2 (`.VnTime`→TCVN3, `VNI-`→VNI) when available.
- **T3.2.3** Score via a Vietnamese dictionary (ratio of valid tokens after trial conversion).
- **T3.2.4** **Per-block detection**: old files may mix multiple encodings in one document.

### E3.3 — NFC normalizer
- **T3.3.1** NFC normalization (on by default), configurable (NFC/NFD/none).
- **T3.3.2** Test NFC/NFD pairs across all Vietnamese accented vowels.

### E3.4 — Text cleanup
- **T3.4.1** Strip junk/control characters; normalize whitespace and line breaks.
- **T3.4.2** Normalize punctuation, de-hyphenate line-broken words when safe.
- **T3.4.3** Preserve block structure (don't break headings/tables marked by S2).

### E3.5 — Diacritic restoration  *(v2, optional)*
- **T3.5.1** Restore diacritics for accent-stripped text via a small model (optional dependency).
- **T3.5.2** Run only when the detector flags "likely accent-stripped" + the user enables it.

### E3.6 — Confidence & telemetry
- **T3.6.1** Return `encoding_detected` + `encoding_confidence` in metadata.
- **T3.6.2** Warn on low confidence so downstream/RAG can handle it.

## 5. Acceptance Criteria
- [ ] Sample TCVN3 and VNI strings convert 100% correctly across the test character set.
- [ ] Detector correctly distinguishes TCVN3/VNI/VISCII/Unicode on the golden corpus (target ≥ 95%).
- [ ] Output is **always NFC** by default; NFC/NFD pair tests pass for all accented vowels.
- [ ] A mixed-encoding file → per-block detection separates the segments correctly.
- [ ] Metadata contains `encoding_detected` + `encoding_confidence`.

## 6. Design decisions
- **Per-block** rather than per-file: safer for mixed-encoding documents.
- Conversion tables are **static data** (built once) → stable, easy to test, runtime-independent.
- NFC is **on by default** — a hard requirement for RAG.
- Diacritic restoration kept optional so no heavy model is pulled into core.

## 7. Risks
- Detector confusion on short/low-diacritic text. *Mitigation:* use font signal + manual override.
- Encoding variants (TCVN3 has many fonts). *Mitigation:* broad golden tests, easy add-table skill.
