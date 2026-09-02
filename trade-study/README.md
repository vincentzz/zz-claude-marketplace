# Trade Study · Three-Role Decision Pipeline

A structured comparison of solutions or tech stacks, built for decision-making: **analyst** runs as the main session and owns the interview, the synthesis, and the deliverables; one **scout** per candidate researches in parallel and in isolation; a **challenger** attacks the result before it ships. Deliverables: `synthesis.html` + `synthesis.pdf` + `deck.pptx`, all derived from a single `synthesis.md`.

```
                 ┌───────────────────────────────────────────────┐
 user ↔ analyst  │ /grill-me → brief.md → dispatch → synthesis.md│  main session (profile entry agent)
                 │ /study-brief · /render                        │
                 └───────┬───────────────────────────┬───────────┘
                 dispatch (bg, parallel)        dispatch (bg, after draft)
            ┌────────────▼────────────┐      ┌───────▼─────────────────┐
            │    scout × N candidates │      │        challenger       │
            │  one candidate each,    │      │ mechanical / evidence / │
            │  blind to the others    │      │ adversarial passes      │
            │  → evidence/<option>.md │      │ → [BLOCKING]/[SUGGEST]  │
            └─────────────────────────┘      └─────────────────────────┘
```

## What holds it together

Analysis has no ground truth to turn from red to green, so this pipeline substitutes **structural adversity** for mechanical acceptance:

- **Provenance chain** (`/evidence-discipline`): every claim in the synthesis traces to an evidence file; every claim there carries a source + retrieval date or an explicit `[INFERENCE]` label. Priors are treated as unknown.
- **Structural anti-anchoring**: scouts never read each other's reports — symmetric depth is guaranteed by isolation, not discipline. (Both rules are transplants from dev-pipeline's forbidden-knowledge discipline.)
- **User-owned numbers**: criteria weights, veto items, and the scenario distribution are user decisions the analyst may propose but never invent — the user is the best available oracle of their own usage distribution.
- **Adversarial close** (`/review-synthesis`): the challenger recomputes the weighted arithmetic, checks every matrix cell is non-empty, hunts unsourced claims, and builds the honest case for the runner-up. Max two rounds; the study closes only on `Conclusion: no blocking items`.

Scoring is **ordinal + weights**: matrix cells hold `--`/`-`/`0`/`+`/`++` (mapped −2…+2), user weights produce the ranking — a defensible ordering without the fake precision of 7.3-vs-7.1. Vetoed candidates are out regardless of score.

## Study layout

```
studies/<id>/
├─ brief.md                  decision context: candidates, criteria×weights, vetoes, scenario, depth
├─ evidence/<option>.md      one per candidate, written only by its scout
├─ synthesis.md              single source of truth
├─ challenger/review-N.md    adversarial rounds (≤2)
└─ out/                      synthesis.html · synthesis.pdf · deck.pptx (+ make_deck.py)
```

Deliverables follow the language the brief is written in. PDF rendering wants Chrome/Chromium, weasyprint, or LibreOffice on the PATH; PPTX wants `python-pptx` — `/render` checks before promising and tells you what to install if something is missing.

## Install & bind

```bash
claude plugin install trade-study@zz-claude-marketplace
cd <your-project>
claude            # plain session
> /use-profile trade-study
# exit, restart: claude now opens in analyst
```

Ships `defaultEnabled: false` and `entryAgent: analyst` — installing enables nothing; `/use-profile` (from the always-on profile-switcher) binds it per project. A Chinese variant, **trade-study-cn**, ships the same pipeline with all prose in Chinese — enable only one of the two (same agent names).

Models: analyst `fable`, scout `sonnet`, challenger `opus`, named in each agent's frontmatter as tier names. On a machine with a different model set, rebind the tiers with `ANTHROPIC_DEFAULT_FABLE_MODEL` / `ANTHROPIC_DEFAULT_OPUS_MODEL` / `ANTHROPIC_DEFAULT_SONNET_MODEL`, or pin every subagent with `CLAUDE_CODE_SUBAGENT_MODEL` plus `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` (Claude Code ≥ 2.1.257; add `--model` for the analyst session itself). `CLAUDE_CODE_SUBAGENT_MODEL` on its own has been outranked by the frontmatter since 2.1.251 and changes nothing here.

## Deliberately thin

No task queues, no worktrees, no state machines, no gates beyond the challenger — 3 agents, 5 skills. 0.1.0 starts minimal by design; every addition needs evidence from a real study.

## License

MIT
