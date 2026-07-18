# Changelog

All notable changes to viparse are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **VPS legacy encoding** — added the VPS (Vietnamese Professional System) → Unicode
  conversion table alongside TCVN3, VNI, and VISCII, selectable via an explicit
  `encoding="vps"` override. VPS shares VISCII's Latin-1 surface bytes, so it is
  intentionally excluded from content-frequency auto-detection to avoid mis-converting
  genuine VISCII text. The 112-byte mapping is cross-verified against four independent
  sources (vietunicode, the Encode::VN `.ucm`, `vietnameseConverter`, and
  `py-unicode-convert`) (VIP-71).

## [0.1.3] — 2026-07-18

### Fixed

- **Per-block encoding detection for mixed-encoding documents** — a document that mixes a
  legacy `.Vn*`/`VNI-` run with already-Unicode runs is now detected and converted per block,
  by each block's own font signal, instead of applying one file-wide verdict. A Unicode run
  containing a character that is also a legacy surface byte (e.g. `viparse® 2026`) is no longer
  corrupted (`viparseđ 2026`), while the adjacent legacy run still converts. Single-encoding
  documents are unaffected — their output is byte-for-byte identical (VIP-65).

## [0.1.2] — 2026-07-12

Dependency compatibility only — no code or behavior changes.

### Changed

- **Widened dependency upper bounds** so viparse installs alongside newer major releases:
  `pillow<13` (extra `ocr`), `langchain-core<2` (extra `langchain`), and `reportlab<6`
  (dev only). Verified against pillow 12, langchain-core 1.x, and reportlab 5 (#47, #48).

## [0.1.1] — 2026-07-12

Documentation and packaging only — no code or behavior changes.

### Added

- **MIT license** — added a `LICENSE` file and declared `license = "MIT"` in the package
  metadata (VIP-62).
- **README** — installation instructions (`pip install viparse` and extras), a usage section,
  and released status linking PyPI (VIP-62).
- **PyPI publishing** — a GitHub Actions workflow publishes to PyPI via Trusted Publishing
  (OIDC, no stored token) when a release is published (VIP-61).

### Fixed

- **Project URLs** — corrected the repository URL and added Homepage / Changelog links shown on
  the PyPI page (VIP-61).

## [0.1.0] — 2026-07-12

First tagged release. Covers the full M0–M5 feature set (VIP-1 … VIP-59).

### Added

- **Public API** — `viparse.load(source, *, output, encoding, ocr, normalize, max_bytes,
  cache, chunk, settings)` and lazy `viparse.load_batch(...)`, returning Unicode-**NFC**
  `Document`s as markdown / text / json.
- **Layered configuration** — `output` / `encoding` / `ocr` / `normalize` / `max_bytes` resolve
  from function args → `VIPARSE_*` env vars → a `viparse.toml` file → the built-in defaults. A
  validating `Settings` (via `load_settings()`) raises `ConfigError` on a bad value.
- **RAG chunking** — opt-in `chunk=ChunkOptions(max_tokens, overlap_tokens)` splits a document
  into retrieval-sized, section-aware `Chunk`s (never splitting a table row) with per-chunk
  `section` / `page` / `sheet` metadata and an ordinal `index`.
- **Framework integrations** — `to_langchain_documents(doc)` / `to_llamaindex_documents(doc)`
  map a `Document` (chunk-aware) onto LangChain / LlamaIndex document types, provenance
  flattened into their `metadata`. Lazy behind `viparse[langchain]` / `viparse[llamaindex]`.
- **CLI** — `viparse <files> -o md|text|json` (globs, directories, `--out`,
  `--encoding`/`--ocr`/`--normalize`) and `viparse doctor` (engine + binary availability).
- **Extraction engines** — DOCX, XLSX, digital PDF, scanned PDF via OCR (`viparse[ocr]`),
  and legacy binary `.doc`/`.xls` via LibreOffice — all thin adapters behind extras so the
  `core` install stays dependency-free.
- **Vietnamese normalization (the moat)** — legacy **TCVN3 / VNI / VISCII** → Unicode NFC,
  with font-signal detection, opt-in content-based detection (`encoding="auto"`), and text
  cleanup. Output is always NFC.
- **Structured output** — headings, GFM tables, and a versioned JSON schema
  (`viparse.SCHEMA_VERSION`).
- **Untrusted-input safety** — configurable file-size limit, zip-decompression-bomb guard,
  and per-engine process timeouts (`UnsafeInput`).
- **Caching** — content-hash `MemoryCache` / `DiskCache` to skip re-parsing unchanged files.
- **Parallel batch** — `load_batch(..., workers=N)` with bounded concurrency and per-source
  error isolation.

[Unreleased]: https://github.com/minhtridinh-kayden/viparse/compare/v0.1.2...HEAD
[0.1.2]: https://github.com/minhtridinh-kayden/viparse/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/minhtridinh-kayden/viparse/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/minhtridinh-kayden/viparse/releases/tag/v0.1.0
