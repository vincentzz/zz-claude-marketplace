---
name: coding-standards
description: The style contract for implementation code — correctness and readability first, declarative by default, modern language features, review-friendly, code always in English. Use when dev writes an implementation and when dev-reviewer reviews the standards axis.
---

# Implementation Style Contract

Partition first, then order. Partition test: **could this code become a performance bottleneck?**

- **Cold zone (default)**: correctness > readability > declarative concision > performance. The vast majority of code lives here; sacrificing readability for imagined performance is premature optimization.
- **Hot zone**: correctness > **performance** > readability > declarative concision. Performance ranks right behind correctness — but reordering does not exempt you from readability discipline: at equal performance take the more readable form, and naming and structure stay as they are.

Legitimate sources for declaring a hot zone (a judgment call needs a source too):

1. **Performance characteristics / hot-path markers declared in spec 2.1** — architect's design output; a performance constraint that matters should come with a mechanical AC.
2. **dev's local judgment** (allocation on a per-call path, O(n) on unbounded input, and the like) — allowed, but it must be registered in the free-choice list: "grounds for calling it a hot zone + the mechanism of the gain (which allocation/boxing/complexity was saved)". A gut-feel "this might be slow" is not grounds.
3. If the judgment is big enough to affect the interface shape, or worth a perf AC, it is a spec gap: report it to architect rather than expanding your own authority.

## Declarative by Default

- Express "what it is", not "how to do it step by step": streams/collectors instead of hand-written loops and accumulators; switch expressions + pattern matching instead of if-else cascades; early return instead of deep nesting.
- Immutability by default: `final` fields, immutable collections (`List.of` / `toUnmodifiableList`), pure functions preferred. Mutable state is an exception that needs a reason.
- **When imperative qualifies**: in the hot zone, per the sources above; in the cold zone, only when the declarative form is clearly more obscure. Both downgrades are choices made where the spec is silent — write them into the free-choice list, one line of "what was downgraded + why".

## Modern Language Features (unfold against the language baseline in the build conventions (project shim CLAUDE.local.md); the example below is Java 17)

`record` instead of hand-written POJOs, `sealed` + pattern matching with an exhaustive `switch`, switch expressions, text blocks, `var` (only when the right-hand-side type is obvious at a glance). Features serve readability, not showmanship: if you use `record`, stop building setter-flavored variant chains; if you use `sealed`, let the compiler exhaust the branches for you — this is the same "compile time beats runtime" stance as everywhere else.

When the language changes, **replace this section wholesale**; the priority ordering and the cold/hot partition test do not change (Rust: iterator chains, exhaustive `match`, a clippy baseline; Haskell: declarative already, so the hot zone shifts to strictness annotations and fusion; Zig: comptime traded for runtime branching…).

## Review-Friendly

- One intent per commit; the reading order of the diff tracks the behavioral order of the spec.
- A method fits on one screen, nesting ≤2 levels; naming uses the domain vocabulary of spec 2.1, never a second invented vocabulary.
- Comments say why, not what — the code says what. Provenance comments are the exception (`// per spec 2.1` / `// per AC-2 worked example`); they are part of the forbidden-knowledge audit.

## Language

**Code, identifiers, and in-code comments are always in English.** Non-English text (CJK and the like) belongs only in documents (spec, notes, review, completion report). Mechanical check: `grep -rnP '[\x{4E00}-\x{9FFF}]'` over the changed code files should return zero hits.
