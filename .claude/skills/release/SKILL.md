---
name: release
description: Cut a viparse release — bump the version, update the CHANGELOG, tag, and build the distribution. Use when publishing a new version of the package.
---

# Cut a release

viparse uses a single source of truth for the version: `src/viparse/__init__.py` (`__version__`),
read by hatchling at build time. Releases are cut from a green `main`.

Follow these steps.

## 1. Pre-flight

- Ensure `main` is up to date and CI is green.
- Run `scripts/dev.sh` locally — lint, type-check, and tests must pass.
- Decide the new version per **SemVer** (MAJOR.MINOR.PATCH) based on what changed since the last tag.

## 2. Bump the version

- Edit `__version__` in `src/viparse/__init__.py` to the new version.
- This is the only place the version is defined — do not duplicate it in `pyproject.toml`
  (it is `dynamic`).

## 3. Update the CHANGELOG

- Add a new `## <version> — <YYYY-MM-DD>` section at the top of `CHANGELOG.md`.
- Group entries under Added / Changed / Fixed / Removed. Summarize user-facing changes; link the
  relevant `VIP-<id>` tasks. Keep it in English.

## 4. Land the bump

- Open one PR titled `VIP-<id> Release v<version>` with the version bump + CHANGELOG.
- Merge once CI is green.

## 5. Tag and build

From the merged `main`:

```bash
git tag -a v<version> -m "v<version>"
git push origin v<version>
scripts/dev.sh build          # produces the wheel + sdist in dist/
```

- Verify the built artifacts carry the new version (`dist/viparse-<version>*`).
- Publish per the project's distribution process (e.g. PyPI) once configured.

## Checklist

- [ ] `main` green, `scripts/dev.sh` passes
- [ ] Version bumped only in `src/viparse/__init__.py`, per SemVer
- [ ] CHANGELOG updated with dated section linking `VIP-<id>`s
- [ ] Release PR merged on green CI
- [ ] Annotated tag `v<version>` pushed
- [ ] Wheel + sdist built and version-verified
