# viparse

> Vietnamese-first document loader for RAG.

One command turns any Vietnamese document — including legacy **TCVN3/VNI/VISCII** fonts, scanned
PDFs, and old `.doc`/`.xls` files — into clean Unicode **NFC** Markdown/JSON, ready to push into a
vector DB.

## Why

Generic loaders *parse the file* but often emit **garbled diacritics** (legacy fonts) or **wrong
Unicode normalization**. `viparse` handles exactly that Vietnamese layer: detect & convert legacy
encodings to Unicode, enforce NFC, and offer diacritic-aware OCR.

**Backbone principle:** never hand-write a parser. Wrap well-maintained engines behind thin
adapters; if an engine gets a CVE or is abandoned, swap the adapter without touching the rest.
Heavy dependencies are lazy-imported via extras (`viparse[ocr]`, `viparse[office]`).

## Status

Released — [`viparse` 0.1.0 on PyPI](https://pypi.org/project/viparse/). See
[`docs/specs/`](docs/specs/README.md) for the full spec map (SPEC-0 … SPEC-8) and
[`CHANGELOG.md`](CHANGELOG.md) for release notes.

## Installation

```bash
pip install viparse               # core — pure stdlib, no parser/OCR binaries
pip install "viparse[office]"     # .docx / .xlsx and legacy .doc / .xls
pip install "viparse[pdf]"        # digital PDFs
pip install "viparse[ocr]"        # scanned PDFs (needs the Tesseract binary)
pip install "viparse[all]"        # every engine
```

Run `viparse doctor` to see which engines your installed extras enable.

## Usage

```python
import viparse

docs = viparse.load("tai_lieu_cu.pdf")            # list[Document], already NFC
docs = viparse.load("bang_luong.xlsx", output="markdown", encoding="auto")
```

```bash
viparse ./docs/**/*.pdf -o md
viparse doctor        # list available engines per installed extras
```

## License

[MIT](LICENSE) © 2026 minhtridinh
