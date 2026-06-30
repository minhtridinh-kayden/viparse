# SPEC-0 — Foundation & Project Ops

| | |
|---|---|
| **Status** | Draft |
| **Depends on** | — |
| **Blocks** | All other SPECs |
| **Milestone** | M0 |

## 1. Goal

Stand up the operational infrastructure every later SPEC relies on: repo, CI/CD, commit/MR
conventions, and especially the **Claude optimization layer** (CLAUDE.md, rules, skills, memory)
so each task is executed consistently, rigorously, and with minimal omissions.

## 2. Scope

**In scope**
- GitHub repo `minhtridinh/viparse` + Linear project + two-way mapping.
- Claude guidance files: `CLAUDE.md`, `.claude/rules/`, `.claude/skills/`, memory seeds.
- CI: lint + type-check + test + coverage gate; dependency-update bot.
- Standard workflow: branch → CI → self-review → MR → push → Linear sync.

**Out of scope**
- Parse/normalize logic (S1–S4).
- Deep security policy (S8; S0 only enables basic CI scaffolding).

## 3. Epics & Tasks

### E0.1 — Initialize repo & project
- **T0.1.1** `gh repo create minhtridinh/viparse` (private), add remote, push first commit.
- **T0.1.2** Create Linear project "viparse" + labels per SPEC (S0..S8) + milestones M0..M4.
- **T0.1.3** Document Linear↔GitHub mapping (issue ID ↔ branch ↔ PR) in `docs/ops/`.

### E0.2 — Root CLAUDE.md
- **T0.2.1** Write `CLAUDE.md`: architecture summary, golden rules, build/test/lint commands.
- **T0.2.2** Golden rules: (1) never hand-write a parser; (2) always NFC; (3) thin adapters;
  (4) heavy engines lazy-imported via extras; (5) every task has acceptance criteria.

### E0.3 — Claude rules (.claude/rules)
- **T0.3.1** Commit/MR rule: short imperative title (≤ 60 chars), **no description**.
- **T0.3.2** "review-before-push" rule: checklist (tests green, type-check, coverage not lowered,
  no sensitive fixtures leaked, NFC-safe).
- **T0.3.3** Code-style rule: ruff + mypy strict, English docstrings, mandatory type hints.

### E0.4 — Custom skills (.claude/skills)
- **T0.4.1** Skill `add-engine`: scaffold a new Engine adapter (file + test + registry entry).
- **T0.4.2** Skill `add-encoding`: scaffold a new encoding table (mapping + golden test).
- **T0.4.3** Skill `release`: bump version, update CHANGELOG, tag, build.

### E0.5 — Memory seeds
- **T0.5.1** Record memory: original pain points (legacy fonts, CVEs, diacritic-aware OCR).
- **T0.5.2** Record memory: locked architectural decisions (Python, RAG-first, thin adapters).

### E0.6 — CI/CD & supply-chain bot
- **T0.6.1** GitHub Actions: `lint` (ruff) + `type` (mypy) + `test` (pytest) + `coverage`.
- **T0.6.2** Coverage gate (start ≥ 80% for core, tighten over time).
- **T0.6.3** Renovate/Dependabot config + `pip-audit` job.
- **T0.6.4** Pre-commit hooks (ruff, end-of-file, trailing-whitespace, NFC check).

### E0.7 — Process & templates
- **T0.7.1** Minimal PR template (review checklist only, no long description required).
- **T0.7.2** Branch naming: `s<spec>/<epic>-<slug>` (e.g. `s3/e3.1-tcvn3-table`).
- **T0.7.3** `scripts/dev.sh` bundling common commands (test, lint, build).

## 4. Acceptance Criteria (SPEC Definition of Done)

- [ ] Repo is release-ready; CI green on the first commit.
- [ ] `CLAUDE.md` + `.claude/rules` + ≥ 3 skills exist and are referenced in the PR template.
- [ ] A trial Linear issue → branch → PR → merge runs correctly through the workflow.
- [ ] `pip-audit` runs in CI with no high-severity findings at baseline.

## 5. Design decisions
- **Linear via MCP** for auto-sync; fallback: create manually + paste issue IDs.
- **gh CLI** creates the repo (already authed as `minhtridinh`).
- Short MR titles, no description — compensated by acceptance criteria in specs + Linear issues.

## 6. Risks
- Linear MCP not yet connected → blocks auto-sync. *Mitigation:* allow manual mode.
- Coverage gate too strict too early → slows momentum. *Mitigation:* raise gradually per milestone.
