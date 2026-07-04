---
name: add-engine
description: Scaffold a new viparse extraction Engine — a thin adapter around a well-maintained parse library, plus its test and registry entry. Use when adding support for a new file format or swapping the library behind an existing format.
---

# Add an extraction engine

An **Engine** is a thin adapter that wraps a well-maintained parse library and returns a
`RawExtraction` (raw text + font/encoding signals). Engines carry **no Vietnamese logic** — that
lives in the normalization layer. Heavy engines are lazy-imported behind an extra.

Follow these steps.

## 1. Confirm the library choice

- Pick a **well-maintained** library for the format (recent releases, no open CVEs, active repo).
  Never hand-write the parser.
- Decide whether it is heavy (native deps, OCR, LibreOffice). If so, it goes behind an extra
  (`viparse[<extra>]`) and must be **lazy-imported** inside the engine, never at module top level.

## 2. Scaffold the adapter

Create `src/viparse/extract/<format>.py` with an engine class/callable that:

- Declares which formats (magic-byte signatures) it handles.
- Lazy-imports its heavy dependency inside the method, raising a clear error that names the extra
  to install if the import fails.
- Extracts text and attaches raw signals (e.g. run font names, embedded encoding hints) needed by
  the normalizer — but performs **no** encoding conversion or NFC itself.
- Returns a `RawExtraction`.

## 3. Register it

Add the engine to the format→engine registry used by the `route` layer so magic-byte detection can
select it. Keep detection based on real bytes, not the filename extension.

## 4. Add a test

- Add a small, synthetic fixture under `tests/` (no sensitive or copyrighted documents).
- Test that the engine is selected for the format and returns the expected raw text and signals.
- If the dependency is heavy/optional, skip the test cleanly when the extra is not installed.

## 5. Verify

Run `scripts/dev.sh` (lint + type-check + test). Then open one PR titled `VIP-<id> Add <format> engine`.

## Checklist

- [ ] Wraps a maintained library — no hand-written parser
- [ ] Heavy dependency lazy-imported behind an extra
- [ ] No Vietnamese/encoding logic in the engine
- [ ] Registered for magic-byte routing
- [ ] Synthetic fixture + test, optional-dependency skip handled
- [ ] `scripts/dev.sh` passes
