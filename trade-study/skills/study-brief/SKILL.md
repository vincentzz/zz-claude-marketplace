---
name: study-brief
description: The brief.md format and the studies/<id>/ directory contract. Use when analyst opens a new study after alignment, or when any role needs to know where a study artifact lives or what the brief must contain.
---

# Study Brief · format and directory contract

`brief.md` is the study's scope contract: scouts research against it, the synthesis is judged against it, the challenger reads it as the promise the study must keep. It is written once after `/grill-me` closes; a change after scouts dispatch is a scope change and goes back to the user (the matrix is only symmetric if every candidate was researched under the same brief).

## Directory contract

```
studies/<id>/                    <id> = zero-padded next free integer (0001, 0002, …)
├─ brief.md                      this contract
├─ evidence/<option>.md          one per candidate; written only by that candidate's scout
├─ synthesis.md                  single source of truth; written only by analyst
├─ challenger/review-N.md        adversarial review rounds, N = 1, 2 (max 2)
└─ out/                          synthesis.html · synthesis.pdf · deck.pptx — all derived from synthesis.md
```

`<option>` in filenames is the candidate name lowercased, spaces and slashes to `-` (e.g. `Google Docs` → `google-docs.md`).

## brief.md sections (all required; "none" is a valid entry, absence is not)

1. **Question** — one sentence: choose one <what> for <scenario/user>. Date opened.
2. **Candidates** — the closed roster, one line each with the exact name and homepage/repo. Anything not on this list is out of the study.
3. **Criteria & weights** — table: criterion · weight (user-assigned integer) · one-line definition of what would count as evidence for it. Weights need not sum to anything; only ratios matter.
4. **Hard constraints (vetoes)** — user-decided disqualifiers, verbatim. A candidate failing one is out regardless of score.
5. **Scenario distribution** — how usage splits, in the user's words with percentages where given. Scouts apportion attention by this; the synthesis reads close calls through it.
6. **Depth & cost posture** — light / moderate / deep, one line on what that means for this study (source classes in scope).
7. **Output language** — the deliverables' language; default is the language this brief is written in.
8. **Non-goals** — dimensions the user explicitly ruled out of scope, so nobody re-litigates them in review.

Every entry in 3–5 records a user decision from the interview — if you cannot point at who decided a weight and when, the interview is not done, and this file cannot be written yet.
