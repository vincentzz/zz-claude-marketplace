---
name: worktree-flow
description: How to use task worktrees, freshen them, and handle conflicts. Use when qa/dev work inside .worktrees/<id>, merge into the baseline branch, or resolve conflicts.
---

# Worktree Discipline

One tree per task: directory `.worktrees/<id>`, branch `task/<id>`, branched off the **baseline branch**. The baseline = the current branch at the moment architect dispatches, pinned in `tasks/specs/<id>/base-branch` — the single merge reference for the whole flow. qa/dev perform no git topology surgery whatsoever (creating trees, merging, removing trees are all architect's); they only work and commit inside the tree. An **evergreen baseline** is the invariant of the whole flow; how the baseline relates to develop/main is the team's CI/CD business.

## Iron Rule: cd Does Not Persist

Every Bash call inside a subagent is a fresh shell. **Every** operation inside the worktree either uses `git -C <tree-path> …` or does `cd <tree-path> && …` within the same command. Forget this and the command silently lands on the main checkout — the most expensive class of accident on this pipeline.

## Entering the Tree and Freshening (qa/dev's first step)

```
git -C <main-checkout> worktree list        # the tree should already exist, created by architect; absent = a dispatch defect, report it
BASE="$(cat <main-checkout>/tasks/specs/<id>/base-branch)"
cd <main-checkout>/.worktrees/<id> && git merge --no-edit "$BASE"   # pull in the latest baseline before starting
```

## Stage Rules

- **qa stage**: commit inside the tree only (`task <id>: acceptance tests (red)`), advance the branch and stop there. Red tests never enter the baseline.
- **dev stage**: once green — ① inside the tree, `git merge --no-edit "$BASE"` and run acceptance again to confirm it stays green; ② commit inside the tree (`task <id>: implement, acceptance green`); ③ **deliver and stop**: do not merge back into the baseline, do not remove the tree. Merging, the post-merge full test run (every task's tests), reverting on red, and removing the tree are architect's job at the acceptance gate. The branch `task/<id>` and `.worktrees/` are **never pushed** — the only thing pushed to the team remote is the baseline-branch commit produced at the acceptance gate and signed by you.

## Conflict Discipline

Conflicts are resolved inside the tree only. For each conflict hunk, answer "what does each side want", and find the answers in each side's first-hand source: for your side, the spec and this task's commit messages; for the other side, `git log -p "$BASE" -- <file>`. Synthesize a resolution from intent — **no bailing out with `--abort`, no mechanically keeping one side**. Once resolved, acceptance.sh must be re-run to green before you may continue. If you cannot work out whose intent is whose, stop and report to architect — architect issues an **intent brief** based on both specs (what each side of each conflict hunk wants; the other task's full spec is not attached), dev synthesizes the resolution from the brief and re-runs acceptance. Conflicts that surface during the acceptance-gate merge are aborted by architect (`--abort` is legitimate here: it is not resolving the conflict, it is refusing to resolve it at the gate) and re-dispatched together with the brief. Every code conflict is **a signal of orthogonality failure**: architect should record the reason for the overlap in the change log of the relevant spec, feeding back into partitioning quality.

<!-- The conflict discipline borrows the intent-tracing principle from resolving-merge-conflicts in mattpocock/skills (MIT). -->
