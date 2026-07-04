# Contributing to viparse

viparse is built one task at a time. Every change traces back to a task in Linear (team key
`VIP`) and lands as a single, self-contained pull request.

## One task = one branch = one commit = one PR

- **Branch:** `vip-<id>-<short-slug>` — the Linear task id plus a short kebab-case slug.
  Examples: `vip-31-add-minimal-pr-template`, `vip-33-add-scripts-dev-sh`.
  (Linear also suggests this name on each task under "Copy git branch name".)
- **Commit / PR title:** `VIP-<id> <short imperative>` — e.g. `VIP-31 Add minimal PR template`.
  No PR description is required; the checklist in the PR template is the review contract.
- Keep the PR scoped to its one task. If you discover unrelated work, open a new task for it.

## Before you push

Run the local quality gates — the same ones CI enforces:

```bash
scripts/dev.sh        # lint (ruff) + type-check (mypy) + tests (pytest + coverage) + build
```

## House rules

- All committed artifacts — docs, comments, identifiers, commit and PR titles — are in **English**.
- Output text is Unicode **NFC**. Never ship text that is not consistently normalized.
- Never hand-write a parser: wrap a well-maintained engine behind a thin adapter.
- Read the relevant `docs/specs/SPEC-*.md` before implementing; the specs are the source of truth
  for scope and acceptance criteria.
