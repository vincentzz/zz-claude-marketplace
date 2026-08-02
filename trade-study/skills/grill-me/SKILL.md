---
name: grill-me
description: Decision-context alignment interview. Use when the user brings a comparison question, wants to open a new study, says "let's align / grill me", or when analyst needs to eliminate ambiguity before writing the brief. The deliverable is a shared understanding solid enough to write brief.md.
---

Interrogate the user with no blind spots left, until the two of you share one understanding of the decision. Walk down the decision tree branch by branch, untangling the dependencies between decisions one at a time.

Rules:

- **Ask one question at a time**, and wait for the answer before the next one. Dumping a string of questions at once only earns a string of perfunctory answers.
- Every question comes with **your recommended answer** plus a one-line rationale, so the user can just reply "yes / no / make it X".
- **Look up facts yourself; leave decisions to the user.** Anything findable with your tools (does candidate X even run on this OS, is the project archived) — look it up before asking; whatever you cannot find, plus every weighting and trade-off decision, goes to the user one item at a time and waits for an answer.
- Every answer from the user can sprout new branches — chase them until no branch is left open.

## Study Interview (mandatory for every new study)

Put all six classes of **decision** to the user, one question at a time — each with evidence where you have it and a recommended answer:

1. **The question itself**: restate the decision in one sentence with the selection context ("choose one X for scenario Y"). A comparison without a scenario is unanswerable — the same matrix ranks differently for different users.
2. **Candidate list**: is it closed? You may propose additions or removals with a one-line reason each, but the final roster is the user's call — a candidate the user won't adopt is wasted scout budget.
3. **Criteria and weights**: propose a starter criteria set with rationale; the user edits it and **assigns every weight**. Weights are never yours to invent — the user is the best available oracle of their own scenario distribution, and the ranking rides on these numbers, not on your prior.
4. **Hard constraints and vetoes**: which failures disqualify outright, regardless of score ("must be free", "must support IME"). Each veto is a user decision, recorded verbatim.
5. **Scenario distribution**: how usage actually splits ("90% quick edits, 10% large logs") — this calibrates where scouts spend attention and how you read close calls.
6. **Depth and cost posture**: light / moderate / deep research per candidate, and the output language if it should differ from the brief's own.

Completion tests (alignment is complete only when all four hold at once; do nothing whatsoever before that):

1. You can write every section of `brief.md` (per `/study-brief`) with no "TBD / roughly / possibly" anywhere in it.
2. Every weight and every veto has a recorded user decision — none traces back to your suggestion having been silently accepted by omission.
3. You can list the brief's "Non-goals" — dimensions the user explicitly said don't matter.
4. The depth posture and output language are recorded.

Once alignment is complete, restate the brief's key numbers (weights, vetoes, depth) back to the user and get confirmation before allocating the study directory.

<!-- Adapted from grilling in mattpocock/skills (MIT) via dev-pipeline's grill-me, with the completion tests retargeted from spec-writing to the study brief. -->
