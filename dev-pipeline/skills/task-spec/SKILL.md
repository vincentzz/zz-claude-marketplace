---
name: task-spec
description: The section contract and completion tests for writing a task spec (tasks/specs/<id>.html). Use when architect starts writing the spec, after grill-me alignment and deep-module-design finalization.
---

# Writing a Task Spec

The spec is the only contract text between architect and qa/dev. qa tests only what the spec says, dev builds only what the spec says — so anything not written in the spec does not exist, and anything written vaguely is a landmine.

Template: `tasks/specs/_template.html` (`taskctl add` instantiates it automatically).

## Completion Tests per Section

1. **Background & Goals** — everything comes from settled conclusions in grill-me; any "TBD / roughly / possibly" means it is unfinished.
2. **Deep Module Design** — per `/deep-module-design` (the three-way boundary split: must know 2.1 / need not know 2.2 / must not know 2.5):
   - 2.1 Interface: **compile-level complete** signatures + contract comments. qa will lay this down as the skeleton word for word, so one missing `throws` or one wrong generic becomes a pipeline incident. Performance-sensitive interfaces mark the hot path here (which flips dev's style priorities), and performance constraints that matter come with a mechanical AC.
   - 2.2 states only "what is hidden", not "how it is done" — qa reads this section too. Implementation hints go in `specs/<id>/architect/dev-hints.md` and are listed under 2.5 as forbidden knowledge for qa.
   - 2.3 Failure-attribution table: all four columns filled on every row, with a decision basis a program can assert on.
   - 2.5 Forbidden knowledge: list only the increment beyond the baseline (CLAUDE.md), each row with a reason and an alternative source; write "baseline only" if there is no increment. Self-check: is everything qa needs to write the tests already in 2.1/2.3/3? If not, extend the spec rather than leaving a gap that forces qa to go dig where it shouldn't.
3. **Acceptance Criteria** — one row per AC, five columns: number, behavior description, decision command, pass standard (always exit 0), carrying check (left for qa to fill in: a regression test that stays in the suite, or a ticket-only step in acceptance.sh — see the two kinds in `/mechanical-acceptance`; an AC about the build or packaging process, a real service, or one-time state is ticket-only by nature, so write its decision command as the shell step rather than as a test). AC descriptions use the nouns of 2.1 and the failure classes of 2.3, introducing no new concepts. The count is governed by "covers the target behavior + covers every row of the failure-attribution table", not by hitting a number.
4. **Non-Goals** — at least one. This is dev's hard boundary and the basis on which review vetoes Speculative Generality.
5. **Resources** — referenced files go into `tasks/specs/<id>/` and are cited by the relative path `<id>/xxx`; write "none" if there are none.
6. **Change Log** — after the spec is finalized, every change (including a reversal from arbitration) appends a row: date, change, responsible party.

## Order of Writing

Run `taskctl add "<title>"` first to get the id and the skeleton file, then fill in the content — creating the file by hand breaks registration consistency. When done, self-check section 3 once more: can every AC's decision command be typed into a terminal verbatim right now? If not, it isn't finished.
