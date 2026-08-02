---
name: mechanical-acceptance
description: The definition of mechanically decidable acceptance, the acceptance.sh script contract, the red-state rule, and test quality discipline. Use when qa lays down the skeleton, writes acceptance tests, or writes acceptance.sh.
---

# Mechanically Decidable Acceptance

**Definition**: one non-interactive command whose exit code is the verdict — exit 0 ⟺ pass. Nobody has to read the output to reach a conclusion. Any acceptance criterion that requires "take a look and confirm" is unfit; send it back for a spec rewrite.

## acceptance.sh Contract

Path `tasks/specs/<id>/acceptance.sh`, delivered by qa, the sole acceptance entry point for that task:

```bash
#!/usr/bin/env bash
set -euo pipefail
CHECKOUT="${1:?usage: acceptance.sh <checkout-dir>}"
cd "$CHECKOUT"
mvn -q test -Dgroups=task-<id>
```

- Idempotent, non-interactive, independent of the caller's cwd, read-only outside the checkout directory.
- dev runs it on the worktree; architect runs it on the main checkout after merging (`taskctl verify`) — the same script decides in both places, and the conclusions must agree.
- All ACs of a task converge into one command. This requires the language ecosystem to provide a **per-task test selection** mechanism (recorded in the build conventions (project shim CLAUDE.local.md)): Java = JUnit5 `@Tag` + `-Dgroups`; Rust = `cargo test task_<id>` (test-name prefix); pytest = `-m task_<id>`; Haskell tasty = `--pattern`; universal fallback = scoping by file/directory naming. The selection mechanism is an internal detail of acceptance.sh — the script is the language seam.

## Red-State Rule (qa's delivery bar)

- **The build must pass, and red must be red at runtime**: an assertion failure or an unimplemented stub (Java's `UnsupportedOperationException`, Rust's `todo!()`, Haskell's `error`, Python's `NotImplementedError`, etc.; see the build conventions (project shim CLAUDE.local.md)). A build failure (compilation in a compiled language, load/import in a dynamic one) is not a red state — it means the skeleton was laid down wrong: fix the skeleton per spec 2.1, do not change the spec, and certainly do not start writing the implementation.
- Red must be in the right place: each AC's test goes red on the behavior it itself asserts. An AC that turns red as collateral damage from an earlier AC failing means the tests have a hidden dependency — split them apart.

## Test Quality (self-check every single test)

- **Test at the interface**: drive and observe only through spec 2.1's public interface. Testing private members, mocking internal collaborators, verifying through a side door into the database — all implementation coupling, and the tests shatter the moment you refactor. Criterion: change the implementation without changing behavior, and the tests must not go red.
- **Expected values come from an independent source of truth**: the spec's literal examples, hand-computed values, the fixed keywords from the failure-attribution table. Deriving the expected value on the fly with the same algorithm as the code under test is a tautology — it is constructively always true and will never catch a bug. An independent source of truth is a special case of forbidden knowledge: annotate the expected value with its provenance (spec section number / AC number / the hand computation), and that provenance comment is what the reviewer checks.
- **Failure attribution becomes tests row by row**: at least one test per row of spec 2.3, asserting the exception type and the mechanical decision basis (e.g. the message contains the parameter name), so accountability itself gets accepted.
- **One AC, one group of tests**, named so they read like a restatement of the spec (`refillSemantics`, `failureAttribution`). Do not stockpile tests for imagined behavior — behavior the spec does not state is not eligible for a test.

<!-- Test quality discipline distilled from tdd in mattpocock/skills (MIT): the implementation-coupling, tautology, and horizontal-slice anti-patterns. -->
