# SPEC-4 — RAG Output & Structuring

| | |
|---|---|
| **Status** | Draft |
| **Depends on** | S2, S3 |
| **Blocks** | S5 |
| **Milestone** | M1 (markdown) → M2 (chunk + JSON) → M3 (integrations) |

## 1. Goal

Turn clean text + block structure into something that pushes **straight into a vector DB**:
renderers (text/markdown/json), RAG-oriented chunking, a full metadata schema, and adapters for
LangChain/LlamaIndex.

## 2. Scope

**In scope**: renderers, a basic chunker (token/heading/layout + overlap), per-chunk metadata,
integration loaders.
**Out of scope**: advanced semantic/complex-layout chunking (consider splitting `viparse-rag` later).

## 3. Epics & Tasks

### E4.1 — Renderers
- **T4.1.1** `text` renderer: plain text, already NFC.
- **T4.1.2** `markdown` renderer: preserve headings, **tables** (GFM table), lists.
- **T4.1.3** `json` renderer: block structure + metadata, stable machine-readable schema.

### E4.2 — Chunking
- **T4.2.1** Token chunker (tiktoken-free, approximate count) with configurable overlap.
- **T4.2.2** Heading/section-aware chunking (respect block boundaries).
- **T4.2.3** Never split mid table-row; large tables get a dedicated split strategy.
- **T4.2.4** Attach per-chunk metadata (page/sheet/section/index).

### E4.3 — Metadata schema
- **T4.3.1** Standardize schema: `source, content_type, page, sheet, section, lang,
  encoding_detected, encoding_confidence, engine, chunk_index, char_span`.
- **T4.3.2** Schema versioning (so downstream can depend on it stably).

### E4.4 — Integrations
- **T4.4.1** LangChain `DocumentLoader` adapter (map `Document` → `langchain.Document`).
- **T4.4.2** LlamaIndex `Reader` adapter.
- **T4.4.3** End-to-end example: file → viparse → vector DB (docs/examples).

## 4. Acceptance Criteria
- [ ] The markdown renderer preserves tables (GFM) and headings from DOCX/PDF samples.
- [ ] The chunker produces correctly overlapping chunks, **never** splits mid table-row, and each
  chunk carries metadata.
- [ ] JSON output has a versioned, stable schema (snapshot test).
- [ ] LangChain/LlamaIndex adapters return correct types and run in the sample example.

## 5. Design decisions
- The basic chunker lives **in core**; advanced chunking can be split into a package later.
- Markdown is the default RAG output (preserves structure well, LLM-friendly).
- Metadata is **versioned** so the downstream contract stays stable.

## 6. Risks
- Complex tables (merged cells) are hard to render to markdown. *Mitigation:* fall back to JSON for
  complex tables.
- Token counts may not match the target model's tokenizer. *Mitigation:* allow a pluggable token
  counter.
