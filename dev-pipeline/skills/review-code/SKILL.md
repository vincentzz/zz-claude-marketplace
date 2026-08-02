---
name: review-code
description: The two-axis yardstick for reviewing implementation code (spec fidelity / code standards). Use when dev-reviewer issues a review of the implementation diff for a single task.
---

# Reviewing Implementation Code

Examine and report the two axes separately; never merge them into one ranking: compliant code can do the wrong thing, and code that does the right thing can violate discipline — rank them together and one axis will mask the other.

## Spec Axis (against the full spec)

- **Missing**: behavior the spec requires is absent or half-built; quote the spec sentence as evidence. [BLOCKING]
- **Extra**: public members, parameters, config options, or "while I was in there" features the spec never asked for — check against section 4, Non-Goals. This includes semantics carried in from the standard implementation: behavior with no provenance in the spec is overreach, however "standard" it may be. Speculative Generality is handled here too. [BLOCKING]
- **Skewed**: places that look implemented but whose semantics are questionable; quote the spec sentence + the code location. [BLOCKING]
- **Circumvented**: the implementation routes around the intent of the tests — hard-coded expected values, sniffing for the test environment, special-casing test inputs. This destroys the evidence accountability rests on. [BLOCKING]

## Standards Axis (against design discipline and the code-smell baseline)

First check the three deep-module items (using the vocabulary of `/deep-module-design`):

- **Interface gone shallow**: implementation details leaking into the interface (exposed internal state, parameters passing internal structures straight through).
- **Blurred responsibility boundary**: the exception types/messages thrown don't line up with spec 2.3's decision basis, so failures can't be attributed mechanically.
- **Self-constructed dependencies**: the module `new`s its own dependencies instead of receiving them explicitly.

Then check the style contract (`/coding-standards` is the shared yardstick with dev):
- **Mechanical precondition**: run `grep -rnP '[\x{4E00}-\x{9FFF}]'` over the code files changed by this task — any hit is [BLOCKING] (language contract: code and comments are always in English).
- Imperative style or mutable state: the hot-zone determination and the downgrade rationale must be findable in spec 2.1 or in dev's free-choice list in notes — not findable is [BLOCKING] (a break in the audit chain); findable but with dubious grounds (a gut-feel "this might be slow", no articulable mechanism of gain) is a [SUGGEST], named explicitly.
- Declarative opportunities in the cold zone (spots where a stream/switch expression/record would be clearer): [SUGGEST]. Do not raise purely stylistic suggestions in the hot zone unless a clearer form exists at equal performance.

Then run through the high-frequency code-smell baseline (Fowler's vocabulary, language-independent; all are judgment calls, not hard violations, and where they collide with a trade-off the spec states explicitly, the spec wins):

- **Mysterious Name** — the name doesn't match the thing → rename it; if you can't produce an honest name, the design is muddled.
- **Duplicated Code** — the same shape of logic in two or more places → extract the common shape.
- **Primitive Obsession** — primitive types carrying domain concepts → give the concept its own small type.
- **Shotgun Surgery** — one logical change scattered across many files → gather it into one module.
- **Long Method / deep nesting** — doesn't fit on a screen, nested more than three levels → split by intent.

Standards-axis findings are [SUGGEST] by default; the three deep-module items, when they hold, are [BLOCKING]. Do not re-review anything the tooling (compiler, formatter, static analysis) already enforces.

<!-- The two-axis structure and the code-smell baseline are adapted from code-review in mattpocock/skills (MIT), trimmed for Java and this pipeline. -->
