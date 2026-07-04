# Rule: commit & PR titles

Every task lands as **one commit = one PR** with a single-line title and **no description body**.

## Format

```
VIP-<id> <short imperative>
```

- Start with the Linear task id (`VIP-<id>`), then a short imperative summary.
- Keep the whole title **≤ 60 characters**.
- Imperative mood, capitalized, no trailing period. Write "Add", not "Added"/"Adds".
- **No PR description.** The PR template checklist is the review contract; a body is not required.
- **No `Co-Authored-By` trailer.**

## Examples

```
VIP-31 Add minimal PR template
VIP-33 Add scripts/dev.sh
```

Not:

```
Added a PR template.                     # past tense, no VIP id
VIP-31: add minimal pull request template for the repository   # too long, colon, lowercase
```
