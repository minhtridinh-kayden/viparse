# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What viparse is

A Vietnamese-first document loader for RAG. It turns Vietnamese documents (including legacy
TCVN3/VNI/VISCII fonts, scanned PDFs, and old `.doc`/`.xls`) into clean Unicode **NFC**
Markdown/JSON, ready to push into a vector DB.

The differentiator (the moat) is the **Vietnamese normalization layer**: detect & convert legacy
encodings to Unicode and enforce NFC. Generic loaders parse the file but emit garbled diacritics
or wrong normalization; viparse fixes exactly that.

## Architecture

The pipeline has four layers; each communicates through intermediate types so they stay decoupled
and independently testable:

```
viparse.load("file") -> list[Document]

  route      detect real format via magic bytes (not the extension); pick an engine
  extract    Engine adapter -> RawExtraction (raw text + font/encoding signals)
  normalize  Normalizer     -> NormalizedDoc  (legacy encoding -> Unicode, NFC, cleanup)
  structure  Renderer       -> Document       (text | markdown | json, + metadata)
```

- **Engines** (`extract`) are thin adapters wrapping well-maintained parse libraries. They carry
  no Vietnamese logic — they only extract and attach raw signals (e.g. run font name).
- **Normalizers** (`normalize`) own the Vietnamese layer (the moat).
- **Renderers** (`structure`) produce the RAG-ready output and metadata.

Heavy dependencies (OCR, LibreOffice) are **lazy-imported** behind extras so `core` stays light.

## Repository layout

```
docs/specs/      Spec map: README + SPEC-0 .. SPEC-8 (source of truth for scope)
docs/ops/        Linear <-> GitHub workflow mapping
src/viparse/     Package source (added incrementally per spec)
tests/           Test suite + golden fixtures
```

Specs are the source of truth for scope. Before implementing, read the relevant
`docs/specs/SPEC-*.md`.

## Commands

> The Python toolchain is added in SPEC-0 (E0.6) and SPEC-5 (packaging). Until then, these are the
> intended entry points.

```bash
# Setup (once the package exists)
pip install -e ".[all]"      # editable install with every extra

# Quality gates
ruff check .                 # lint
ruff format .                # format
mypy src                     # type-check (strict)
pytest                       # tests
pytest --cov=viparse         # tests with coverage

# CLI
viparse <file> -o md|text|json
viparse doctor               # list available engines per installed extras
```

## Workflow

- Hierarchy: **SPEC -> Epic -> Task**. In Linear, an epic is an issue and a **task is a sub-issue**
  (team key `VIP`). Sub-issues are created just-in-time per epic.
- **One task = one branch = one commit = one PR.** PR/commit title: `VIP-<id> <short imperative>`,
  no description.
- All committed artifacts (docs, comments, identifiers, commit titles) are in **English**.
