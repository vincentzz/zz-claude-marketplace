---
name: agent-notes
description: The contract for how each role records valuable information under tasks/specs/<id>/<agent>/. Use when qa/dev wrap up and write notes, write review text to disk, or hand off to the next role.
---

# Role Notes

Path contract: `tasks/specs/<id>/<role-name>/notes.md` (a path under the main checkout, not the worktree). Review text is written to disk by the **invoking side** as `review-N.md` in the same directory, with N counting up from 1.

## What to record (every entry must be able to change a later reader's behavior)

- **Decisions and rationale**: took A, not B, and why. A decision recorded without its rationale is not recorded at all.
- **Traps**: things you stepped in once that someone else will step in again — environment quirks, hidden pitfalls in dependencies, sentences in the spec that are easy to misread.
- **Deviations from the spec and arbitration outcomes**: who approved it, on what grounds (this is a link in the accountability chain).
- **Runtime environment marker**: for work completed in local fallback mode (PIPELINE_PROVIDER=local), mark `[local-mode]` on the first line of notes — the quality spot-check backfill after the subscription is restored uses this as its index.
- **Handoff**: one sentence for the next role — qa writes to dev (which AC is the nastiest), dev writes to architect (the single most worth-knowing thing about the implementation).

## What not to record

Running commentary ("ran the tests"), musings unrelated to this task, facts readable straight off git log and the diff. Notes are incremental information, not a log.

Format is free: one subheading per item, short sentences, straight to the point. Notes belong to personal tooling along with `tasks/**` and do not enter the project repository.
