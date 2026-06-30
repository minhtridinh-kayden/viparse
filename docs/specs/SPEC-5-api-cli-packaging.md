# SPEC-5 — Public API, CLI & Packaging

| | |
|---|---|
| **Status** | Draft |
| **Depends on** | S1–S4 |
| **Blocks** | S8 (release) |
| **Milestone** | M1 (load + basic CLI) → M2 (extras, config) |

## 1. Goal

The surface developers touch: the `load()`/`load_batch()` API, the `viparse` CLI, packaging with
**extras** to isolate heavy dependencies, and a clear configuration layer.

## 2. Scope

**In scope**: public API, CLI, `pyproject.toml` + extras, config layering, `doctor`.
**Out of scope**: parse/normalize logic (S2/S3), advanced batch parallelism (S7).

## 3. Epics & Tasks

### E5.1 — Public API
- **T5.1.1** `viparse.load(source, *, output, encoding, ocr, normalize) -> list[Document]`.
- **T5.1.2** `viparse.load_batch(sources, ...) -> Iterator[list[Document]]` (extension point for S7).
- **T5.1.3** Stable API + docstrings + full type hints; tidy `__all__`.

### E5.2 — CLI
- **T5.2.1** `viparse <file> -o md|text|json` (stdout or `--out` file).
- **T5.2.2** Glob multiple files + directories (`viparse ./docs/**/*.pdf`).
- **T5.2.3** Flags `--ocr`, `--encoding`, `--normalize`, `--chunk`.
- **T5.2.4** `viparse doctor`: list available engines based on installed extras.

### E5.3 — Packaging & extras
- **T5.3.1** `pyproject.toml` (PEP 621), build backend, metadata.
- **T5.3.2** Extras: `core` (light default), `[ocr]`, `[office]`, `[all]`.
- **T5.3.3** CLI entry point (`viparse = viparse.cli:main`).
- **T5.3.4** Clean wheel/sdist build in CI.

### E5.4 — Config layering
- **T5.4.1** Precedence: function args > environment variables > config file (`viparse.toml`).
- **T5.4.2** `Settings` object validates configuration; clear errors on misconfiguration.

## 4. Acceptance Criteria
- [ ] `pip install viparse` (core) does not pull Tesseract/LibreOffice.
- [ ] `viparse.load("a.docx")` returns a correctly typed `list[Document]`, already NFC.
- [ ] CLI renders md/text/json; `viparse doctor` reports the correct available engines.
- [ ] Config layering works: override via args > env > file.

## 5. Design decisions
- Minimal API: a single `load()` covers 90% of needs; keyword-only params for safe extension.
- Extras isolate heavy deps — directly counters the "heavy install + many CVEs" pain.
- The CLI is thin and calls the API directly (no duplicated logic).

## 6. Risks
- API extension breaks compatibility. *Mitigation:* keyword-only + SemVer + scheduled deprecation.
