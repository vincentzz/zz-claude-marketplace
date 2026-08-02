---
name: task-registry
description: Command reference (taskctl) for reading and writing the task registry tasks/task.html. Use when querying tasks, picking one for dispatch, advancing status, registering a new task, adjusting priority, or running mechanical acceptance.
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/taskctl.py *)
---

# Task Registry (taskctl)

`tasks/task.html` is the single source of truth for task status and may **only** be read and written through taskctl. Row order is priority. Editing table rows by hand makes taskctl refuse service on a contract violation.

Uniform invocation (absolute path, independent of cwd):

```
python3 ${CLAUDE_SKILL_DIR}/scripts/taskctl.py --root ${CLAUDE_PROJECT_DIR} <subcommand>
```

## Subcommands

| Command | Purpose | Output / exit code |
|---|---|---|
| `list` | The whole table | TSV: `priority-index id test dev title` |
| `show <id>` | A single row | Same as above |
| `next test` | Highest-priority task with Test=not-started | Prints the id; exit 3 if none |
| `next dev` | Highest-priority task with Test=done and Dev=not-started | Prints the id; exit 3 if none |
| `set <id> test\|dev <status>` | Advance status (status ∈ not-started/in-progress/done) | Gate ①: Dev may not leave not-started before Test=done; Gate ②: advancing to done requires the corresponding review closure (same as review-check) |
| `review-check <id> test\|dev` | Verify review closure: the latest review-N.md has no [BLOCKING], contains the conclusion line `Conclusion: no blocking items`, and the round count is ≤2 | exit 0 = pass; 2 = not closed (reason on stderr) |
| `add "<title>" [--id NNNN] [--top\|--after ID\|--before ID]` | Register: create the spec from `_template.html`, create `specs/<id>/`, insert the row (tail by default) | Prints the new id |
| `move <id> --top\|--bottom\|--after ID\|--before ID` | Adjust priority | |
| `retitle <id> "<title>"` | Change the title | |
| `verify <id> [--checkout DIR]` | Run `tasks/specs/<id>/acceptance.sh`, accepting against the main checkout by default | **The exit code is the verdict**: 0 ⟺ all ACs pass |

## Self-Guarding Exclusions

Every taskctl run idempotently writes `tasks/`, `.worktrees/`, `.claude/`, and `CLAUDE.md` into `.git/info/exclude` (skipping paths already tracked by git) — harness state never entering the team repository is a mechanical invariant, not something that depends on anyone remembering an install step.

## Discipline

- Status advancement is performed by architect only; right after a `set`, do `git add tasks && git commit -m "tasks: …"`.
- `--force` is only for a special dispensation after arbitration, and the reason must be written into that task's architect notes at the same time.
- Exit code 2 = usage or contract violation (read the error on stderr), 3 = `next` has nothing to dispatch. A script error means the world and the contract disagree — fix the world or go to architect first, don't route around the script.
