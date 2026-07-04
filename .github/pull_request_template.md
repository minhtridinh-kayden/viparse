<!--
Keep PRs to one task. Title: `VIP-<id> <short imperative>`. No long description needed.
This checklist is the review contract; delete lines that genuinely do not apply.
-->

## Checklist

- [ ] One task, one commit — scope matches a single `VIP-<id>`
- [ ] Acceptance criteria from the spec are met
- [ ] Output stays Unicode **NFC** (if this touches text handling)
- [ ] No hand-written parser — engines wrapped behind thin adapters (if this touches extraction)
- [ ] Lint, type-check, and tests pass locally (`scripts/dev.sh`)
- [ ] All committed text is in English
