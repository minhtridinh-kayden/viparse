# SPEC-2 — Extraction Engines (Adapters)

| | |
|---|---|
| **Status** | Draft |
| **Depends on** | S1 |
| **Blocks** | S4 |
| **Milestone** | M1 (DOCX) → M2 (digital PDF, XLSX) → M3 (OCR, .doc/.xls) |

## 1. Goal

Provide **thin adapters** wrapping the best parse engine for each format. Each adapter is
independent, swappable, and **lazy-imports** heavy dependencies via extras so `core` stays light.

## 2. Scope

**In scope**: digital PDF, DOCX, XLSX/XLS, scanned PDF (OCR), legacy binary `.doc`/`.xls`,
capability registry.
**Out of scope**: Vietnamese normalization (S3), render/chunk (S4). Adapters only return
`RawExtraction` (raw text + font/encoding signals when the engine exposes them).

## 3. Adapter principles
- Adapters contain **no** Vietnamese logic; they only extract + attach signals (font name, flags).
- Heavy dependencies sit behind `try/import` + extras (`viparse[ocr]`, `viparse[office]`).
- Each adapter: `supports()`, `extract()`, declares priority, and is tested with a small fixture.

## 4. Epics & Tasks

### E2.1 — Digital PDF
- **T2.1.1** `pypdfium2`/`pdfplumber` adapter: extract text per page.
- **T2.1.2** Extract **font name** per text run (signal for the S3 detector, e.g. `.VnTime`→TCVN3).
- **T2.1.3** Extract tables (pdfplumber tables) → intermediate structure preserving rows/cols.

### E2.2 — DOCX  *(MVP)*
- **T2.2.1** `python-docx` adapter: paragraphs + runs (keep run font name).
- **T2.2.2** Extract DOCX tables → intermediate structure.
- **T2.2.3** Preserve block order (heading/paragraph/table) so S4 renders correctly.

### E2.3 — XLSX/XLS
- **T2.3.1** `openpyxl`/`calamine` adapter: read sheets, cells, merged cells.
- **T2.3.2** Map sheet → metadata; cells → intermediate table structure.
- **T2.3.3** Handle formulas (use computed value if present; otherwise record formula + warning).

### E2.4 — Scanned PDF → OCR  *(extra `viparse[ocr]`)*
- **T2.4.1** Tesseract `vie` adapter (pytesseract/ocrmypdf) with sensible DPI/preprocessing.
- **T2.4.2** Image preprocessing pipeline (deskew, threshold) to improve diacritic accuracy.
- **T2.4.3** Return per-block confidence; flag weak OCR so S3 can react.

### E2.5 — Legacy binary `.doc`/`.xls`  *(extra `viparse[office]`)*
- **T2.5.1** LibreOffice-headless adapter (convert to temp docx/xlsx) or `antiword`.
- **T2.5.2** Manage LibreOffice process lifecycle (timeout, temp-file cleanup).
- **T2.5.3** Detect missing LibreOffice → clear error + install guidance.

### E2.6 — Engine registry & capability
- **T2.6.1** Register engines by content_type + priority.
- **T2.6.2** Fallback chain (e.g. digital PDF fails → try OCR if enabled).
- **T2.6.3** Report available engines (`viparse doctor`) based on installed extras.

## 5. Acceptance Criteria
- [ ] Each adapter has a small fixture + a test that extracts correct text & basic table structure.
- [ ] Without extras, `core` still imports; calling an engine with a missing dep → clear error,
  no import-time crash.
- [ ] DOCX adapter (MVP) returns `RawExtraction` with the font name for each run.
- [ ] Registry selects the correct engine by content_type and priority.

## 6. Design decisions
- **Lazy-import** mandatory for heavy deps; `core` depends only on stdlib + schema.
- Adapters return **raw** font/encoding signals and let S3 decide — clean separation of concerns.
- Prefer well-maintained engines; avoid abandoned libs (prevents repeating the CVE pain).

## 7. Risks
- LibreOffice/Tesseract are heavy system dependencies. *Mitigation:* separate extras + `doctor`.
- Some engines don't expose font names. *Mitigation:* S3 detector has a font-free heuristic branch.
