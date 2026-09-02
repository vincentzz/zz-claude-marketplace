---
name: mechanical-acceptance
description: The definition of mechanically decidable acceptance, the two kinds of check (regression tests that run on every build vs ticket-only checks that run only through acceptance.sh), the acceptance.sh script contract, the red-state rule, and test quality discipline. Use when qa lays down the skeleton, writes acceptance tests, or writes acceptance.sh.
---

# Mechanically Decidable Acceptance

**Definition**: one non-interactive command whose exit code is the verdict — exit 0 ⟺ pass. Nobody has to read the output to reach a conclusion. Any acceptance criterion that requires "take a look and confirm" is unfit; send it back for a spec rewrite.

## Two Kinds of Check (classify every AC before writing anything)

Every AC becomes exactly one of these, and the mapping table in qa's completion report names which:

- **Regression test** — asserts the behavior of spec 2.1/2.3/3 through the public interface. It joins the project's test suite, is tagged with this task's marker, and **runs in the full-test command on every future build, forever**. It is therefore hermetic: no network, no external service, no environment variable, no pre-existing local file or state, no dependence on a prior build step or on wall-clock timing. The bar is a **fresh checkout**: a developer with nothing but the toolchain named in the build conventions and zero knowledge of the project runs the full-test command, and it is green.
- **Ticket-only check** — proves that *this* ticket is done in *this* environment: verification of the build or packaging process, integration with a real service, a migration or other one-time state, a performance budget, anything that needs setup beyond the toolchain. It runs **only through acceptance.sh for this task** and never in the full-test command. It is a shell step in acceptance.sh, or a test in the project's ticket-only slot if the build conventions declare one (a slot the full-test command skips: Maven failsafe `*IT`, a pytest marker deselected by default, Rust `#[ignore]` + `--ignored`); with no slot declared, shell steps only.

**The fresh-checkout invariant**: at every commit on the baseline, the full-test command is green on a fresh clone with nothing but the toolchain. A build-process verification inside the default suite breaks this by construction — the build runs the suite, the suite runs the build — and so does any test that needs what your machine happens to have. Skipping a check to keep the default build green is legitimate; a default build a stranger cannot pass is not. Architect enforces the invariant mechanically at the acceptance gate (the full-test command in a fresh clone); qa-reviewer enforces it by reading.

## acceptance.sh Contract

Path `tasks/specs/<id>/acceptance.sh`, delivered by qa, the sole acceptance entry point for that task:

```bash
#!/usr/bin/env bash
set -euo pipefail
CHECKOUT="${1:?usage: acceptance.sh <checkout-dir>}"
cd "$CHECKOUT"
# regression tests of this task — they stay in the suite and run on every build
mvn -q test -Dgroups=task-<id>
# ticket-only checks — run here and nowhere else (e.g. AC-4, the packaging AC)
mvn -q -DskipTests package
unzip -l target/app.jar | grep -q 'META-INF/services/com.example.Plugin'   # per AC-4
```

- Idempotent, non-interactive, independent of the caller's cwd, read-only outside the checkout directory.
- dev runs it on the worktree; architect runs it on the main checkout after merging (`taskctl verify`) — the same script decides in both places, and the conclusions must agree.
- All ACs of a task converge into one command. This requires the language ecosystem to provide a **per-task test selection** mechanism (recorded in the build conventions (project shim CLAUDE.local.md)): Java = JUnit5 `@Tag` + `-Dgroups`; Rust = `cargo test task_<id>` (test-name prefix); pytest = `-m task_<id>`; Haskell tasty = `--pattern`; universal fallback = scoping by file/directory naming. The selection mechanism is an internal detail of acceptance.sh — the script is the language seam.
- Regression tests are selected by the task marker; ticket-only checks follow as explicit shell steps (or an explicit invocation of the ticket-only slot). The script never leaves a ticket-only check inside the default suite, and it never relies on anything the fresh-checkout invariant forbids without setting it up itself — a step that fails because its environment is absent is broken, not red.

## Red-State Rule (qa's delivery bar)

- **The build must pass, and red must be red at runtime**: an assertion failure or an unimplemented stub (Java's `UnsupportedOperationException`, Rust's `todo!()`, Haskell's `error`, Python's `NotImplementedError`, etc.; see the build conventions (project shim CLAUDE.local.md)). A build failure (compilation in a compiled language, load/import in a dynamic one) is not a red state — it means the skeleton was laid down wrong: fix the skeleton per spec 2.1, do not change the spec, and certainly do not start writing the implementation.
- Red must be in the right place: each AC's test goes red on the behavior it itself asserts. An AC that turns red as collateral damage from an earlier AC failing means the tests have a hidden dependency — split them apart.
- Red comes from the regression tests' assertions and stubs, or from a ticket-only step honestly failing on the not-yet-done work. A ticket-only step failing because its service, file, or variable is missing is not a red state — set it up inside the script, or drop the step.

## Test Quality (self-check every single test)

- **Test at the interface**: drive and observe only through spec 2.1's public interface. Testing private members, mocking internal collaborators, verifying through a side door into the database — all implementation coupling, and the tests shatter the moment you refactor. Criterion: change the implementation without changing behavior, and the tests must not go red.
- **Expected values come from an independent source of truth**: the spec's literal examples, hand-computed values, the fixed keywords from the failure-attribution table. Deriving the expected value on the fly with the same algorithm as the code under test is a tautology — it is constructively always true and will never catch a bug. An independent source of truth is a special case of forbidden knowledge: annotate the expected value with its provenance (spec section number / AC number / the hand computation), and that provenance comment is what the reviewer checks.
- **Failure attribution becomes tests row by row**: at least one test per row of spec 2.3, asserting the exception type and the mechanical decision basis (e.g. the message contains the parameter name), so accountability itself gets accepted.
- **One AC, one group of tests**, named so they read like a restatement of the spec (`refillSemantics`, `failureAttribution`). Do not stockpile tests for imagined behavior — behavior the spec does not state is not eligible for a test.

<!-- Test quality discipline distilled from tdd in mattpocock/skills (MIT): the implementation-coupling, tautology, and horizontal-slice anti-patterns. -->
