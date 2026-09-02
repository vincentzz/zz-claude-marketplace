---
name: review-test-cases
description: The two-axis yardstick and completion tests for reviewing acceptance tests. Use when qa-reviewer issues a review of the test cases and acceptance.sh for a single task.
---

# Reviewing Acceptance Tests

Examine the two axes separately; neither offsets the other. The coverage axis asks "was the contract copied out in full?"; the quality axis asks "are these tests worth trusting?".

## Coverage Axis (against the spec)

- **AC↔check bidirectional mapping**: every AC is carried by at least one regression test or ticket-only step, each labeled with its kind; every test and every step can point back to an AC. Orphan tests (behavior the spec never asked for) and orphan ACs (carried by nobody) are both [BLOCKING].
- **Every row of the failure-attribution table has a test**: each row of spec 2.3 is asserted on both exception type + mechanical decision basis. A missing row is [BLOCKING].
- **Skeleton fidelity**: the interface laid down matches spec 2.1 verbatim — one extra public member or one missing `throws` is [BLOCKING].
- **acceptance.sh contract**: conforms to the script contract in `/mechanical-acceptance`; tag selection scopes to this task's tests only; every ticket-only check is an explicit step there and nowhere else.

## Quality Axis (against the tests themselves)

- **Implementation coupling**: mocking internal collaborators, asserting on private state, verifying through a side door. Criterion: imagine a refactor that changes no behavior — would the tests go red? Implementation coupling is often **downstream evidence of a forbidden-knowledge violation** — a structure, constant, or algorithmic assumption appears in the tests that cannot be derived from spec 2.1/2.3/3 — whether it came from reading something that shouldn't have been read or from the standard practice in the priors, call it out either way; a missing provenance annotation on an assertion falls here too. [BLOCKING]
- **Tautology**: the expected value derived on the fly with the same algorithm as the code under test, snapshots that confirm themselves, a constant equal to itself. Expected values must come from an independent source of truth. [BLOCKING]
- **Hidden dependencies**: tests sharing mutable state or depending on ordering; one AC turning another red as collateral damage. [BLOCKING]
- **Environment coupling in the default suite**: a test the full-test command runs that needs a network, a service, an environment variable, a pre-existing local file, a prior build step, or that shells out to the build itself (a build-process verification inside the suite is circular: the build runs the suite, the suite runs the build). It fails for a stranger on a fresh checkout and it is misfiled — it belongs in acceptance.sh as a ticket-only step. Grep for it: `System.getenv`, `ProcessBuilder`, network clients, absolute paths. [BLOCKING]
- **Reason for red**: run acceptance.sh yourself — it must compile, be red at runtime, and each test must be red on the behavior it itself asserts. A compilation failure is [BLOCKING].
- Names that don't read like a restatement of the spec, and assertion messages that don't help attribute failure, are [SUGGEST].

## Completion Tests

In the review report, **every AC and every test method has been named** (either in the mapping table or in the findings); miss one and the review is not complete. The bar for [BLOCKING]: it would let a spec breach through, or it would misfire during a refactor. Anything below that bar is [SUGGEST] and is not promoted.
