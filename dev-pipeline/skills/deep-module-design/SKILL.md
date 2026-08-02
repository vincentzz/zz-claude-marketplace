---
name: deep-module-design
description: Design discipline for deep module interfaces and responsibility boundaries. Use when designing or reworking a module interface, deciding where a seam goes, writing section 2 of a spec, reviewing interface shape, or whenever another skill needs this vocabulary.
---

# Deep Module Design

Design **deep modules**: a lot of behavior hidden behind a small interface, standing on a clean seam, testable from the interface alone. At the same time, the interface must make **failure responsibility mechanically decidable** — that is the accountability bedrock of this pipeline.

## Vocabulary (use these terms strictly; do not substitute synonyms)

- **Module**: anything with a distinction between interface and implementation — function, class, or package alike, scale-independent.
- **Interface**: **everything** a caller needs to know to use the module correctly — the type signature, plus invariants, call-ordering constraints, error modes, configuration requirements, performance characteristics. The signature is only one corner of the interface.
- **Implementation**: all the code behind the interface.
- **Deep/shallow**: deep = learn a little interface, get a lot of behavior; shallow = the interface is nearly as complex as the implementation.
- **Seam**: the place the interface sits, where behavior can be swapped without changing the code at that point. Where to put it is an independent design decision.
- **Adapter**: the concrete thing that satisfies the interface at a seam.
- **Orthogonal**: two modules share no reason to change. One new requirement should hit exactly one spec; wanting to change 2.1 in two specs at once means the boundary was cut along the axis of change instead of between axes of change. Failure-attribution tables sharing no rows is the mechanical projection of orthogonality onto accountability.
- **Composable**: all the knowledge needed to compose two modules = the sum of both 2.1s. If the composition point needs anything from either side's 2.2 to hook up, the seam is in the wrong place.

## The Three-Way Boundary Split (every module boundary has three layers)

1. **Must know** — the interface (spec 2.1): everything needed to use and accept it correctly.
2. **Need not know** — hidden (spec 2.2): where implementation freedom lives. For a human engineer, reading more is merely a waste.
3. **Must not know** — forbidden knowledge (spec 2.5, forbidden to know): information that, if used, pollutes behavior or breaks accountability. For an LLM agent this layer **cannot be enforced by access control** — most of the knowledge to be banned is already in the weights (the standard implementation, the idiomatic algorithm). The operational form is **treated as unknown**: knowledge with no legitimate provenance (a citable basis inside the spec) may not take part in a decision. This is the agent version of clean-room engineering: a human clean room hires people who have never seen the original source; an agent cannot hire a version of itself that "doesn't know about token buckets", so it can only simulate that ignorance with provenance discipline. The audit surface therefore sits in the artifacts, not in a read log: a structure, constant, or semantic in the tests or implementation that cannot be derived from the spec is the evidence of a violation.

Designing a module = designing all three layers at once. A boundary that draws 2.1/2.2 but not 2.5 is, for an agent pipeline, only half drawn.

## Principles

- **Depth is a property of the interface, not of the implementation.** The implementation may be split into small pieces internally and keep internal seams for its own tests — as long as none of it leaks into the interface.
- **The deletion test**: imagine deleting this module. Complexity vanishes with it → it was just a pass-through layer; complexity regrows at N call sites → it was earning its keep.
- **The interface is the test surface**: callers and tests go through the same seam. Wanting to bypass the interface to test internals usually means the module has the wrong shape.
- **One adapter is a hypothetical seam; two adapters make it a real seam.** Without a second implementation (even a test double), don't erect a seam.
- **Dependencies are wired by hand and passed explicitly**: a module receives dependencies, it does not construct them. Containers and magic injection do not exist on this pipeline.

## Failure-Attribution Table (how to write spec 2.3)

An interface design isn't finished until failure attribution is drawn. For each class of possible failure, answer four questions:

| Failure class | Manifestation (exception type / return value) | Responsible party | Mechanical decision basis |
|---|---|---|---|

- **Responsible party** takes only four values: caller (argument/ordering breach), assembler (configuration/dependency breach), this module (implementation defect), normal business state (no responsible party).
- **Mechanical decision basis** must be a signal a program can assert on: exception type, a fixed keyword in the exception message, the shape of the return value. "Go look at the logs" is not a decision basis.
- Completion test: for any production failure, this table lets you name the responsible party without reading the implementation; QA turns the table into tests row by row.

## Boundary Determination (homework for grill-me, not an independent verdict)

When new functionality is involved, mechanically finish the homework below first and carry the conclusion into grill-me's boundary interview as a **recommended answer**; if the determination is self-evident (all three tests pass unopposed and no new dependency is involved), it does not go on the table — just write "placement self-evident" in the spec change log.

**Step 0 · Dependencies first** (cheapest and reversible, always ask the world first): dispatch an explore subagent to run a fixed checklist — ① each dependency's current version and latest version; ② grep the changelog between those two versions for keywords of the target capability; ③ whether the existing API surface already covers it; ④ if a new dependency is needed: number of new transitive dependencies, maintenance signals (last release, bus factor), share of the consuming surface. The report must **cite evidence** (version numbers + changelog lines/doc links); an uncited "probably not there" is not a conclusion. The burden of proof is inverted: building it yourself when a dependency already provides it = Duplicated Code against the ecosystem, and the reason (license / measured performance / semantic difference / supply chain) must be registered in the spec.

**The placement triple test** (existing module vs new module, each item observable against the spec draft):
- **Reason-for-change test**: can the new functionality's failure-attribution rows go into the existing 2.3 table without adding a responsible-party category or a new kind of decision basis? Needs an addition → separate reason to change → new module.
- **Vocabulary test**: can it be fully specified using the existing vocabulary of the current module's 2.1? Needs more than two or three new domain nouns → it's another module's story.
- **Interface-increment test**: if merging forces an existing public member to take an extra parameter or a mode switch → new module; conversely, if the new-module option cannot produce a second adapter and has no independent reason to change → merge it in.
Where the three tests conflict, the reason-for-change test wins; the conclusion and its evidence go into the spec change log — the judgment may be made by a human, but the trace of the judgment must be mechanically inspectable.

## Design It Twice

When you are unsure of the interface shape, invoke 2–3 Explore subagents in parallel, give each the same slice of requirements, and ask each to return an interface draft that is **stylistically radically different** (for example: imperative vs value semantics, coarse-grained vs fine-grained). Compare the returns on three axes — depth, clarity of failure attribution, seam placement — take the best of each, synthesize, then finalize. The first instinct is usually the shallowest version.

<!-- Vocabulary and principles adapted from codebase-design and its DESIGN-IT-TWICE in mattpocock/skills (MIT);
     the failure-attribution table is this pipeline's extension (blame-oriented programming: make failure responsibility mechanically decidable). -->
