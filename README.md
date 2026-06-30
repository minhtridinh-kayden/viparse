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

Early design. See [`docs/specs/`](docs/specs/README.md) for the full spec map (SPEC-0 … SPEC-8).

## Planned usage

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

TBD.
