# Linear ↔ GitHub mapping

How work is tracked across Linear and GitHub for viparse. One system of record for planning
(Linear), one for code (GitHub); this doc keeps them in sync.

## Hierarchy

```
SPEC (docs/specs/SPEC-*.md)   scope & acceptance criteria — source of truth
  └─ Epic   Linear issue        e.g. VIP-5  "[S0·E0.6] Set up CI/CD & supply-chain bot"
       └─ Task  Linear sub-issue  e.g. VIP-29 "Add dependency scanning"
```

- A **SPEC** is a design document under `docs/specs/`. It defines epics and their tasks.
- An **Epic** is a Linear issue (team key `VIP`), assigned to a milestone (M0..M4).
- A **Task** is a Linear **sub-issue** of its epic. Tasks are created **just-in-time** when the
  epic is picked up, not all upfront.

## One task = one branch = one commit = one PR

Each task maps to exactly one unit of change on GitHub:

| Artifact      | Convention                                                        |
|---------------|-------------------------------------------------------------------|
| Branch        | `vip-<id>-<short-slug>` (Linear suggests it under "Copy git branch name") |
| Commit / PR   | Title `VIP-<id> <short imperative>`, ≤60 chars, no description body |
| Merge         | Squash-merge into `main`, delete the branch                       |

The Linear task id in the branch and title is what links the GitHub change back to the plan.

## Status flow

The Linear task status tracks the GitHub lifecycle:

| Linear status | GitHub state                                             |
|---------------|----------------------------------------------------------|
| Backlog       | Not started                                              |
| In Progress   | Branch created; work + local gates (`scripts/dev.sh`)    |
| In Progress   | PR open, CI running                                      |
| Done          | PR merged on green CI, branch deleted                    |

Tasks involving real code/logic also get a `/code-review` pass before the commit.

## Milestones & labels

- **Milestones** `M0..M4` group epics into delivery phases (M0 = Foundation).
- **Labels** `S0..S8` tag each issue with its originating SPEC (e.g. `S0-foundation`).

## Accounts

- GitHub repo: `minhtridinh-kayden/viparse` (TrizenX projects use the `minhtridinh-kayden` account).
- Linear team: `viparse` (key `VIP`).
