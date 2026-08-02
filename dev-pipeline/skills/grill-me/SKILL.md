---
name: grill-me
description: Requirements-alignment interview. Use when the user raises a new requirement, wants to open a new task, says "let's align / grill me", or when architect needs to eliminate ambiguity before writing a spec. The deliverable is a shared understanding solid enough to start writing the spec.
---

Interrogate the user with no blind spots left, until the two of you share one understanding of the requirement. Walk down the decision tree branch by branch, untangling the dependencies between decisions one at a time.

Rules:

- **Ask one question at a time**, and wait for the answer before the next one. Dumping a string of questions at once only earns a string of perfunctory answers.
- Every question comes with **your recommended answer** plus a one-line rationale, so the user can just reply "yes / no / make it X".
- **Look up facts yourself; leave decisions to the user.** Anything findable in the codebase, the filesystem, or your tools (what the existing interface looks like, which library is in use) — look it up before asking; whatever you cannot find, plus every trade-off decision, goes to the user one item at a time and waits for an answer.
- Every answer from the user can sprout new branches — chase them until no branch is left open.

## Boundary Interview (mandatory whenever new functionality is involved)

First finish the homework in `/deep-module-design`'s "Boundary Determination" (dependency exploration + the placement triple test), then put all three classes of **decision** to the user one question at a time — each with evidence and a recommended answer:

1. **Dependency trade-off**: "I looked into capability X: <evidence citation>. I suggest <upgrade to vN / build it ourselves / pull in Y>, because <one-line rationale>. Your call?" — "maybe a different dependency version already solves it" must be confirmed or refuted right here; defaulting to building it yourself is not allowed.
2. **Placement**: "Triple-test result <summary>, I suggest <merge into M / open new module N>. Your call?" — except when the three tests conflict or the answer is self-evident (self-evident does not go on the table).
3. **Change-distribution calibration**: "My guess at the plausible future changes is these N <list>, and each would touch these modules <draft impact matrix>. Which will actually happen? What did I miss?" — **the user is the best available oracle for the distribution of change**, and the orthogonality bet rides on the calibrated distribution, not on architect's prior imagination.

Completion tests (alignment is complete only when all four hold at once; do nothing whatsoever before that):

1. You can write the spec's "Background & Goals" with no "TBD / roughly / possibly" anywhere in it.
2. You can list the spec's "Non-Goals" — the things the user explicitly said are out of scope.
3. For every settled trade-off you can point to who made the call, under which question.
4. When new functionality is involved: the dependency trade-off and the placement have a recorded user decision, and the change-impact matrix has been corrected by the user (or "placement self-evident" has been recorded).

Once alignment is complete, restate the conclusion back to the user and get confirmation before moving on to design and writing the spec.

<!-- Adapted from grilling in mattpocock/skills (MIT), with the completion tests hardened for this pipeline's spec output. -->
