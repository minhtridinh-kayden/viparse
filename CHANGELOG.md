# Changelog

All notable changes to viparse are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Public API** — `viparse.load(source, *, output, encoding, ocr, normalize, max_bytes,
  cache)` and lazy `viparse.load_batch(...)`, returning Unicode-**NFC** `Document`s as
  markdown / text / json.
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

[Unreleased]: https://github.com/minhtridinh-kayden/viparse/commits/main
