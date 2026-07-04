# Rule: review before push

Before pushing a branch and opening its PR, verify every item below. If a task involves real
code or logic, also run `/code-review` on the working changes and resolve its findings first.

## Checklist

- [ ] **Tests green** — `scripts/dev.sh test` passes locally.
- [ ] **Type-check clean** — `scripts/dev.sh type` (mypy strict) reports no errors.
- [ ] **Lint & format** — `scripts/dev.sh lint` passes (ruff check + format).
- [ ] **Coverage gate met** — coverage stays at or above the `fail_under` threshold.
- [ ] **No sensitive fixtures** — no secrets, credentials, or private/real documents committed;
      test fixtures are synthetic or properly licensed.
- [ ] **NFC-safe** — any emitted or committed text is Unicode NFC (the pre-commit `nfc-check`
      hook must pass).
- [ ] **Scope** — the diff matches exactly one `VIP-<id>`; nothing unrelated is bundled in.

Running `scripts/dev.sh` (no argument) covers lint + type-check + test in one go — the same gates
CI enforces.
