# viparse — Spec Map

> **viparse** — a Vietnamese-first document loader for RAG. One command turns any Vietnamese
> document (including legacy TCVN3/VNI/VISCII fonts, scanned PDFs, old `.doc`/`.xls`) into clean
> Unicode **NFC** Markdown/JSON, ready to push into a vector DB.

## What this document is

This is the **overview** tier. Each SPEC is a large, self-contained area with clear boundaries so
they don't overlap. A SPEC breaks into **Epics**, an Epic breaks into **Tasks**. Conventions:

- **1 Task = 1 branch = 1 MR** (short title, **no description**).
- Every Task has explicit **Acceptance Criteria**; review before commit & push.
- Every Task maps 1-to-1 to **one Linear issue** and **one GitHub PR**.

## Positioning (one-liner)

Other loaders *parse the file* but often emit **garbled diacritics** (legacy fonts) or **wrong
NFC**. `viparse` handles exactly that Vietnamese layer — this is the project's **moat** (SPEC 3).

**Backbone principle:** never hand-write a parser. Wrap well-maintained engines behind **thin
adapters**; if an engine gets a CVE or is abandoned, swap the adapter without touching the rest.

## SPEC list

| ID | Name | Role | Depends on |
|----|------|------|------------|
| [SPEC-0](SPEC-0-foundation-ops.md) | Foundation & Project Ops | Ops infra + Claude optimization | — |
| [SPEC-1](SPEC-1-core-architecture.md) | Core Architecture & Domain Model | Skeleton, contracts between layers | S0 |
| [SPEC-2](SPEC-2-extraction-engines.md) | Extraction Engines | Adapters wrapping parse engines | S1 |
| [SPEC-3](SPEC-3-vietnamese-normalization.md) | Vietnamese Normalization ★MOAT★ | Encoding convert + NFC | S1 |
| [SPEC-4](SPEC-4-rag-output.md) | RAG Output & Structuring | Markdown/JSON + chunk + metadata | S2, S3 |
| [SPEC-5](SPEC-5-api-cli-packaging.md) | Public API, CLI & Packaging | Dev surface + extras | S1–S4 |
| [SPEC-6](SPEC-6-testing-quality.md) | Testing, Fixtures & Quality | Golden corpus + regression guard | cross-cutting |
| [SPEC-7](SPEC-7-performance-scale.md) | Performance & Scale | Lazy/batch/cache for large corpora | S1–S5 |
| [SPEC-8](SPEC-8-security-supplychain.md) | Security & Supply-chain | CVE defense, untrusted input | S0, S5 |

## Dependency graph

```
SPEC 0 (ops) ──► SPEC 1 (core) ──► SPEC 2 (engines) ─┐
                       │                              ├─► SPEC 4 ─► SPEC 5
                       └──────────► SPEC 3 (moat) ────┘
SPEC 6 (testing) runs in parallel throughout
SPEC 7 & 8: hardening after the vertical slice is green
```

## MVP vertical slice (v0.1)

A thin cut across specs to get something runnable early and prove the moat before expanding:

```
DOCX → extract → (TCVN3/VNI → Unicode + NFC) → markdown   via viparse.load()
```

## Status

| Phase | Focus specs |
|-------|-------------|
| **M0 — Foundation** | S0 |
| **M1 — MVP slice** | S1, S3 (TCVN3/VNI), S2 (DOCX), S4 (markdown), S5 (load + CLI) |
| **M2 — More formats** | S2 (digital PDF, XLSX), S3 (VISCII, detector) |
| **M3 — Heavy formats** | S2 (OCR, .doc/.xls) |
| **M4 — Hardening** | S6, S7, S8 |
