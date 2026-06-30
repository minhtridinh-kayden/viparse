# SPEC-1 — Core Architecture & Domain Model

| | |
|---|---|
| **Status** | Draft |
| **Depends on** | S0 |
| **Blocks** | S2, S3, S4, S5 |
| **Milestone** | M1 |

## 1. Goal

Define the skeleton and the **contracts between layers** (interfaces), the domain model, and the
orchestrator that runs the pipeline `route → extract → vn-normalize → structure`. This is the most
touched part, so it must be tightly designed and its internal API stabilized early so other specs
can plug in concurrently.

## 2. Scope

**In scope**
- `Document` / `Chunk` model + metadata schema.
- `Engine` (extract) and `Normalizer` (normalize) interfaces as Protocols/ABCs.
- Format detection via magic bytes + registry router.
- Orchestrator + error/partial-failure policy + observability hooks.

**Out of scope**
- Concrete engine implementations (S2), Vietnamese normalization algorithms (S3),
  renderer/chunker (S4).

## 3. Architecture model

```
viparse.load("file") → list[Document]
   route(detect format) → extract(Engine) → normalize(Normalizer) → structure(Renderer)
```

Each layer communicates through intermediate types (`RawExtraction` → `NormalizedDoc` →
`Document`) for decoupling and independent testing.

## 4. Epics & Tasks

### E1.1 — Domain model
- **T1.1.1** `Document(text, metadata, chunks)`; compatible with LangChain/LlamaIndex shapes.
- **T1.1.2** `Chunk(text, metadata, index)`.
- **T1.1.3** `DocumentMetadata` schema: `source, content_type, page, sheet, lang,
  encoding_detected, encoding_confidence, engine, extra`.
- **T1.1.4** Intermediate types: `RawExtraction` (raw text + encoding/font signals), `NormalizedDoc`.

### E1.2 — Interfaces
- **T1.2.1** `Engine` Protocol: `supports(content_type) -> bool`, `extract(source) -> RawExtraction`.
- **T1.2.2** `Normalizer` Protocol: `normalize(RawExtraction) -> NormalizedDoc`.
- **T1.2.3** `Renderer` Protocol: `render(NormalizedDoc, fmt) -> Document`.
- **T1.2.4** Engine capability/priority (multiple engines support a type → pick by priority score).

### E1.3 — Format detection & routing
- **T1.3.1** Detector via magic bytes (zip header for docx/xlsx, `%PDF`, OLE2 for old doc/xls).
- **T1.3.2** Distinguish digital vs scanned PDF (text-layer count / image ratio) to hint OCR need.
- **T1.3.3** Registry: register engines by content_type; router picks the matching engine.
- **T1.3.4** Fallback chain when the preferred engine fails.

### E1.4 — Orchestrator
- **T1.4.1** Orchestrate a single file: route → extract → normalize → structure.
- **T1.4.2** Parameter hooks (output fmt, encoding override, ocr on/off, normalize form).
- **T1.4.3** Return `Document` (single) and prepare an extension point for batch (S7).

### E1.5 — Error & partial-failure policy
- **T1.5.1** Exception tree: `ViparseError` → `UnsupportedFormat`, `ExtractionError`,
  `EncodingError`, `EngineUnavailable`.
- **T1.5.2** Partial policy: a failed page/sheet still returns the extracted parts + a warning in
  metadata.
- **T1.5.3** `strict` vs `lenient` modes.

### E1.6 — Observability
- **T1.6.1** Structured logging (engine used, encoding detected, per-layer timing).
- **T1.6.2** Optional metrics hook (callback) so downstream can measure throughput.

## 5. Acceptance Criteria
- [ ] A **fake Engine** and **fake Normalizer** can be registered and run end-to-end through the
  orchestrator in tests, without heavy dependencies.
- [ ] Detector correctly identifies docx/xlsx/pdf/doc/xls from magic bytes (golden tests).
- [ ] Partial-failure: a 3-page file with 1 bad page → returns 2 pages + a warning in metadata.
- [ ] `mypy --strict` is green across `core`.

## 6. Design decisions
- **Protocols (PEP 544)** over heavy ABCs → third-party engines are easy to implement.
- Clear intermediate types between layers → isolated tests, no leaking of engine details.
- **Async-aware but sync-first**: public API is sync; parallel batch lives in S7.
- `core` has **no heavy dependencies** — stdlib only + (optional) pydantic for schema.

## 7. Risks
- Wrong interface early → costly refactor. *Mitigation:* lock interfaces with contract tests,
  review carefully at M1.
- PDF digital/scan detector imprecise. *Mitigation:* return a "hint" + allow manual override.
