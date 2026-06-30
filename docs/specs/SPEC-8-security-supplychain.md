# SPEC-8 — Security & Supply-chain Hardening

| | |
|---|---|
| **Status** | Draft |
| **Depends on** | S0, S5 |
| **Blocks** | stable release |
| **Milestone** | M4 |

## 1. Goal

Directly address the root pain: **"old tools have too many CVEs / are abandoned"**. Isolate
dependencies, scan for vulnerabilities automatically, handle untrusted input safely, and have a
fast-patch process when an engine gets a CVE.

## 2. Scope

**In scope**: dependency isolation, CVE scanning, input safety, SBOM, SemVer/release/CHANGELOG.
**Out of scope**: deep penetration testing (future). This is foundational hardening.

## 3. Epics & Tasks

### E8.1 — Dependency isolation
- **T8.1.1** Split extras so heavy/CVE-prone deps don't enter core by default.
- **T8.1.2** Pin versions + lock; periodic update policy.
- **T8.1.3** Minimize dependencies; prefer well-maintained libs with few transitive deps.

### E8.2 — Automated CVE scanning
- **T8.2.1** `pip-audit` in CI (block high-severity).
- **T8.2.2** Renovate/Dependabot opens update PRs automatically.
- **T8.2.3** Periodic security review schedule + a `security` label on Linear.

### E8.3 — Untrusted-input safety
- **T8.3.1** Limit file size & processing time (defend against zip-bombs, malicious files).
- **T8.3.2** Sandbox/timeout external processes (LibreOffice/Tesseract).
- **T8.3.3** Never eval/execute file content; guard path traversal when unzipping docx/xlsx (zip).
- **T8.3.4** Bound XML parsing resources (defend against billion-laughs/XXE in OOXML).

### E8.4 — SBOM & fast patching
- **T8.4.1** Generate an SBOM (CycloneDX) per release.
- **T8.4.2** Runbook: when an engine gets a CVE → swap adapter / pin patched / fast release.
- **T8.4.3** Security policy (`SECURITY.md`) + a vulnerability reporting channel.

### E8.5 — Release & versioning
- **T8.5.1** SemVer + `CHANGELOG.md` (keep-a-changelog).
- **T8.5.2** Release process via the `release` skill (bump, tag, build, publish).
- **T8.5.3** Signed/verified release artifacts where feasible.

## 4. Acceptance Criteria
- [ ] `pip-audit` runs on every PR; high-severity blocks merge.
- [ ] Core installs minimally, pulling no heavy deps; extras are cleanly separated.
- [ ] Size/time limits + path-traversal/XXE guards are in place when opening OOXML.
- [ ] SBOM is generated automatically on release; `SECURITY.md` + CVE-patch runbook exist.

## 5. Design decisions
- **Isolation via extras** is the primary CVE weapon — users who don't need OCR don't carry OCR deps.
- Prefer well-maintained engines over "powerful but abandoned" ones.
- Treat input with a "every file is untrusted" mindset (especially zip-based OOXML).

## 6. Risks
- External engines are the main CVE source, outside our control. *Mitigation:* thin adapters for
  fast swaps + runbook + extras isolation.
- Resource limits too strict block valid large files. *Mitigation:* configurable thresholds.
