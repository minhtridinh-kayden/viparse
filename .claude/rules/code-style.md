# Rule: code style

Python code in viparse is linted, formatted, and type-checked automatically. The tools are the
source of truth; this rule states the intent behind them.

## Tooling (enforced by CI and pre-commit)

- **ruff** for both lint and format — do not hand-format around it. Run `scripts/dev.sh lint`.
- **mypy strict** — `scripts/dev.sh type` must report no errors. Do not weaken strictness or add
  blanket `# type: ignore`; if an ignore is unavoidable, make it specific (`# type: ignore[code]`)
  and comment why.

## Conventions

- **Type hints are mandatory.** Every function signature (parameters and return) is annotated.
  Prefer precise types over `Any`; reach for `typing`/`collections.abc` generics.
- **English docstrings.** Public modules, classes, and functions have a short docstring, in English,
  describing behavior — not restating the signature.
- **English everywhere.** All identifiers, comments, and docstrings are in English. Vietnamese
  belongs only in test fixtures and data, never in code or prose.
- **NFC.** Any string literals or fixtures containing Vietnamese text are Unicode NFC.
