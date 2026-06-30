# SPEC-6 — Testing, Fixtures & Quality Gates

| | |
|---|---|
| **Status** | Draft |
| **Depends on** | cross-cutting (every spec contributes tests) |
| **Blocks** | release |
| **Milestone** | runs in parallel across M1–M4 |

## 1. Goal

The test suite and the **golden corpus** are the project's biggest asset for retaining users and
guarding against regression. Goal: every Vietnamese behavior (legacy fonts, NFC, OCR) has a golden
test, and coverage is gated.

## 2. Scope

**In scope**: fixtures, unit/integration/snapshot tests, accuracy benchmark, coverage gate.
**Out of scope**: perf benchmark (S7), security scan (S8) — though they share CI infrastructure.

## 3. Epics & Tasks

### E6.1 — Golden corpus
- **T6.1.1** Collect/synthesize real files: DOCX/PDF in TCVN3, VNI, VISCII fonts.
- **T6.1.2** Scanned Vietnamese PDFs (for OCR).
- **T6.1.3** Legacy binary `.doc`/`.xls`.
- **T6.1.4** **Anonymize** sensitive data; record fixture source/license.
- **T6.1.5** Each fixture ships an NFC "expected text" for comparison.

### E6.2 — Unit tests
- **T6.2.1** Test each encoding table (TCVN3/VNI/VISCII) character by character.
- **T6.2.2** Diacritic edge cases: vowel clusters, stacked marks, rare characters (ỹ, ợ, ặ...).
- **T6.2.3** Test the detector on short/mixed-encoding strings.

### E6.3 — Integration tests
- **T6.3.1** End-to-end per format: file → `load()` → Document.
- **T6.3.2** Partial-failure (partially corrupt file) returns the correct extracted parts.

### E6.4 — Snapshot/golden output
- **T6.4.1** Snapshot markdown/json output for canonical fixtures.
- **T6.4.2** Controlled snapshot-update workflow (review the diff).

### E6.5 — Accuracy benchmark & coverage gate
- **T6.5.1** Normalization accuracy metric (CER / character match) vs expected.
- **T6.5.2** Coverage gate in CI (core ≥ 80%, tighten per milestone).
- **T6.5.3** Per-encoding accuracy report to catch regressions.

## 4. Acceptance Criteria
- [ ] Golden corpus has at least one fixture per encoding + per MVP format.
- [ ] Every fixture has an NFC expected text for automated comparison.
- [ ] CI blocks merge when coverage drops below threshold or accuracy regresses.
- [ ] Snapshot tests catch unintended output changes.

## 5. Design decisions
- Fixtures are small, anonymized, clearly licensed — avoids legal/sensitivity risk.
- Measure accuracy by character metric (CER) rather than pass/fail to reveal trends.
- Coverage gate rises gradually — doesn't slow the early phase.

## 6. Risks
- Lack of diverse real files. *Mitigation:* a generator that synthesizes legacy fonts + a call for
  fixture contributions.
- Snapshots rot if updated carelessly. *Mitigation:* require snapshot-diff review in the PR.
