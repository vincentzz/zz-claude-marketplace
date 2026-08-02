---
name: evidence-discipline
description: Provenance rules and the evidence-file contract for scouts. Use when researching a candidate, writing evidence/<option>.md, or judging whether a claim is fact or inference.
---

# Evidence Discipline · provenance or label

A trade study has no acceptance script — analysis has no exit code. What substitutes for mechanical acceptance is a provenance chain: every claim in the synthesis traces to an evidence file, and every claim in an evidence file traces to a source or wears an inference label. Break the chain anywhere and the recommendation is opinion wearing a matrix.

## The provenance rule

- **Every factual claim carries a source and a retrieval date.** A source is something a reader can check: a URL, an official doc section, a version number + changelog entry, an issue/PR reference. Format inline: `…claim… (source: <link or citation>, retrieved 2026-08-02)`.
- **A claim you cannot source is written as inference, never as fact**: `[INFERENCE] <claim> — because <your reasoning from which sourced facts>`. An inference is legitimate material; an unlabeled one is a defect the challenger hunts.
- **Priors are treated as unknown.** "Everyone knows X is faster" has no standing until sourced — common knowledge and stock impressions are exactly the anchors this discipline exists to keep out. (Transplant of dev-pipeline's forbidden-knowledge rule: what lacks provenance may not enter a decision.)
- **Version-pin what you measure**: a claim about behavior names the version it was observed or documented in. "Fixed in 2.3" and "broken" can both be true.
- **Freshness matters at the margin**: for fast-moving candidates, prefer sources from the last year and note the date of the newest release you checked. A 2019 forum thread about performance is provenance for what was true in 2019.

## Anti-anchoring (structural)

You research one candidate blind to the others' findings: never read other candidates' evidence files, never read the synthesis, never use "X vs Y" head-to-head content as a primary source. Symmetric depth across the field is guaranteed by isolation — if every scout leans on the same comparison article, the study inherits that article's anchors and the parallel scouts were pointless. Extracting a claim *about your candidate* from such an article is permitted, but it still needs its own primary source or an [INFERENCE] label.

## evidence/<option>.md contract

1. **Header** — candidate, exact version(s) examined, date, depth posture actually spent.
2. **Hard constraints** — one line per veto item from the brief: pass / fail / unknown, each with a source. Never buried; a failed constraint is the headline.
3. **One section per criterion**, in the brief's order. Findings as sourced claims and labeled inferences; numbers over adjectives where the source gives numbers. A criterion the budget didn't reach gets `GAP: <what's missing and why>` — a declared gap is a finding, a padded section is a defect.
4. **Sources** — the consolidated list with retrieval dates.

Write for the analyst who will read all candidates' files side by side: findings, not narrative; the criterion's question answered, not the marketing page summarized.
