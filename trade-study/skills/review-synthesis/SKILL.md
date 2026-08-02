---
name: review-synthesis
description: The three-pass yardstick for adversarially reviewing a synthesis (mechanical / evidence / adversarial). Use when challenger reviews synthesis.md against the brief and the evidence directory.
---

# Reviewing a Synthesis

Run the three passes in order and report them separately; never merge them into one ranking: a synthesis can be mechanically complete and still rest on unsourced claims, or evidence-clean and still hide a fragile winner — collapse the passes and one failure mode masks another.

## Mechanical pass (decidable, no judgment)

- **Empty cell**: any criteria×candidates cell without a rating, or a vetoed candidate not marked as such in the matrix. [BLOCKING]
- **Broken arithmetic**: recompute every weighted total from the stated ratings (`--`/`-`/`0`/`+`/`++` → −2…+2) and the brief's weights; any mismatch, or a ranking sentence that contradicts the totals. [BLOCKING]
- **Missing veto verdict**: any veto item from the brief without an explicit per-candidate pass/fail, or a candidate that failed a veto still ranked as if alive. [BLOCKING]
- **Orphan rating**: a matrix cell with no justification subsection, or a justification citing no evidence file. [BLOCKING]
- **Scope drift**: a criterion, weight, or candidate in the synthesis that is not in the brief, or one from the brief that vanished. [BLOCKING] — the brief is the promise; renegotiating it happens with the user, not in the synthesis.

## Evidence pass (against the provenance chain)

- **Unsourced fact**: a load-bearing claim (one the recommendation rests on) with no traceable citation into an evidence file. [BLOCKING]
- **Laundered inference**: a claim labeled [INFERENCE] in evidence that appears in the synthesis as plain fact. [BLOCKING]
- **Stretched citation**: the evidence file says less than the synthesis claims (evidence: "startup ~200ms on the author's M1"; synthesis: "fastest startup in class"). [BLOCKING] when load-bearing, [SUGGEST] otherwise.
- **Spot-check failures**: WebFetch the two or three strongest citations; a source that does not say what the chain claims it says is [BLOCKING].
- **Undeclared gap**: a criterion rated confidently for a candidate whose evidence section declared a GAP there. [BLOCKING]. (A rating over a declared gap is allowed only if the synthesis says it is provisional and why.)

## Adversarial pass (judgment, argued with the study's own numbers)

- **Best case for the runner-up**: build it honestly from the evidence files. If it is stronger than the synthesis admits, name what the synthesis underweighted. [SUGGEST], or [BLOCKING] if the case actually wins under the brief's own weights.
- **Fragile winner**: if a one-step change (one weight ±1, one rating one notch) flips the ranking and the sensitivity section does not say so, that omission is [BLOCKING] — the user is about to decide on a coin flip presented as a verdict.
- **Scenario misreading**: if the brief's scenario distribution plausibly reads a different way than the synthesis assumed, spell out the alternative reading and where it would change ratings. [SUGGEST].

Findings cite the exact location (file § heading) and state what would resolve them. End with exactly one conclusion line: `Conclusion: no blocking items` or `Conclusion: N blocking items` — the analyst's close-out gates on that literal string. Do not pad: a clean mechanical pass is expected, not praiseworthy, and three [SUGGEST]s that restate taste are worth less than one that re-reads the scenario.
