# Pipeline Protocol (binding on every role)

This repo runs a three-stage development pipeline: **architect** (the main session, started with `claude --agent architect`) owns alignment, design, spec writing, and dispatch; **qa** and **dev** are subagents that deliver the acceptance tests and the implementation respectively; **qa-reviewer** / **dev-reviewer** are nested read-only review subagents invoked by qa / dev. Role definitions live in `.claude/agents/`, discipline in `.claude/skills/`.

Language convention: documents (spec, notes, reviews, completion reports) are written in English; **code, identifiers, and in-code comments are always English**, as are commands and status values.

Build conventions are declared in the **project-side CLAUDE.local.md** (language baseline, full-test command, per-task test selection mechanism, unimplemented stub) — switching languages only touches the project shim, this protocol is language-agnostic at the mechanical layer, and every judgment converges on the `acceptance.sh` exit code. Wherever the text below says "build conventions", it means that block in the project shim.

## Directory Contract

```
.claude/CLAUDE.md                 This protocol (loaded via @import from the root CLAUDE.local.md;
                                  it neither occupies nor touches the project's own CLAUDE.md)
tasks/task.html                   Single source of truth for task state; modified only through taskctl
tasks/specs/<id>.html             Task spec (architect is the single writer)
tasks/specs/<id>/                 Resources referenced by the spec (images, etc.)
tasks/specs/<id>/acceptance.sh    Sole entry point for mechanical acceptance (delivered by QA): exit 0 ⟺ all ACs pass
tasks/specs/<id>/<agent>/         Per-role notes for this task (notes.md, review-N.md)
tasks/specs/_template.html        Spec template; _example.html is a filled-in sample
.worktrees/<id>                   Task worktree; branch task/<id>; created off the baseline branch (pinned by architect at dispatch)
tasks/specs/<id>/base-branch      Baseline branch name (written by architect when creating the tree; the one merge reference for the whole flow)
.claude/pipeline/budget.json      Quota data written to disk by statusline (data source for the token-budget gate)
```

`<id>` is always 4 digits (e.g. `0001`). Spec files whose names start with an underscore are not registered.

## Forbidden-Knowledge Discipline (forbidden to know, in effect for every task by default)

Forbidden knowledge ≠ read ban: the information to be excluded is usually already in your priors — the standard implementation, the idiomatic algorithm, "that's how everyone does it". The discipline is to **treat it as unknown**: forbidden information must play no part in any decision, however well you know it. Operationalized as a provenance constraint:

- **Provenance constraint**: every judgment must point at a legitimate source (spec 2.1/2.3/3 and their literal examples, the red tests). Knowledge whose source you cannot name is treated as nonexistent.
- **Test for where the spec is silent**: if the choice does not leak into observable interface behavior, it is implementation freedom granted by 2.2; if it does leak, the spec is defective — report it under "stop on overstep"; never patch the gap with the "standard practice" in your priors.
- **Supporting hygiene (read ban)**: do not read files the spec does not reference and do not go hunting for reference implementations — contamination that never gets in needs no "treat as unknown". qa is additionally banned from reading `specs/<id>/architect/dev-hints.md` and other tasks' tests; dev is additionally banned from reading other tasks' specs and worktrees.
- The audit surface is the artifact: any structure, constant, or semantics appearing in the tests or the implementation that cannot be derived from the spec is evidence of a forbidden-knowledge violation. Per-task additions are in spec 2.5.

## State Machine (the Test / Dev columns on each row of task.html)

```
Test: not-started ──dispatch qa──▶ in-progress ──qa delivers + review closure──▶ done
Dev : not-started ──dispatch dev──▶ in-progress ──green branch delivered + acceptance gate (merge + full suite green)──▶ done
Gate ①: Dev must not leave not-started before Test=done (mechanically blocked by taskctl)
Gate ②: advancing to done requires review closure — the corresponding reviewer's latest review-N.md
        has no [BLOCKING], carries the `Conclusion: no blocking items` conclusion line,
        and the round count is ≤2 (mechanically blocked by taskctl)
```

Only architect advances state, and only through `taskctl`. Row order is priority: the higher the row, the higher the priority.

## Write Permissions (single-writer principle)

- `tasks/**`: **architect is the only writer**, with two exceptions — qa/dev write their own `tasks/specs/<id>/<agent>/`, and qa writes `tasks/specs/<id>/acceptance.sh`. Reviewers never write to disk; the invoker writes the review text to disk as `review-N.md`.
- Production code and tests: **changed only inside the task worktree `.worktrees/<id>`**. No role may edit code files in the main checkout directly; the only route for code into the main checkout is the merge inside architect's acceptance gate.
- `tasks/**` and `.claude/**` are **personal tooling and stay out of the project repo** (masked via `.git/info/exclude`, see README). The main checkout is therefore clean by construction; the only thing pushed to the team remote is baseline-branch commits signed by you. If you want an evidence trail, set up a private git repo inside `tasks/`.

## Bash Discipline (required reading for subagents)

Inside a subagent, `cd` **does not persist across Bash calls**. Any command involving the worktree must either use `git -C <path> …` or do `cd <path> && …` within the same command. Always write `tasks/**` through paths under the main checkout (cwd defaults to the project root).

## Git Contract

- **Baseline branch** = the branch architect is on at dispatch time, pinned in `tasks/specs/<id>/base-branch`; the worktree is created from it, freshen merges from it, and the acceptance gate merges back into it. Merging into shared branches such as develop/main is **the team CI/CD's jurisdiction**, and the harness does not overstep — green inside the gate is your promise about your own branch; green in CI is the team's promise about the shared branch.
- Evergreen baseline: QA's red acceptance tests land only on the `task/<id>` branch, never on the baseline.
- dev stops at delivering a green branch: one last merge of the baseline into the branch, run `acceptance.sh` green inside the tree, commit. The `--no-ff` merge back into the baseline, the post-merge **full test suite** (every task's tests, to catch cross-task regressions), `revert -m 1` on red, and tearing down the tree are all performed by architect at the acceptance gate.
- Resolve conflicts inside the worktree by tracing back to intent; settling for `--abort` is banned. Once resolved, acceptance must be re-run.

## Stop on Overstep

Any role hitting an overstep situation — the spec is wrong, a test conflicts with the spec, the contract needs changing — stops the current action, writes the facts and its recommendation into its own notes, and reports upward for arbitration (qa/dev → architect; reviewer → its invoker). Never amend the spec, alter another role's artifacts, or "just fix it while you're in there".
