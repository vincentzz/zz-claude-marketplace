---
name: pipeline-init
description: Idempotently initialize the pipeline for the current project (install the shim, run the build-conventions interview, seed state, self-check the environment). Use when architect's startup self-check finds the project uninitialized, or when the user asks to "put this project on the pipeline / init pipeline".
---

# Project Initialization (Idempotent)

This skill reduces "onboard a project onto the pipeline" to one mechanical checklist: **if an item exists, skip it; only fill in what is missing; repeated runs have zero side effects**. Repairs are additive only (create files, append lines) and never rewrite anything the project already has — the project's own CLAUDE.md and settings.json are not touched by a single byte.

## Checklist (execute in order)

1. **git repository**: is there a `.git/` at the project root? If not → stop and ask the user (every bit of accountability in this pipeline grows on git).
2. **Protocol in place (including upgrade refresh)**: does `~/.claude/pipeline/PROTOCOL.md` exist with a first-line version == this plugin's version?
   Missing or behind → copy from the plugin's `pipeline/PROTOCOL.md` and annotate the first line with `<!-- dev-pipeline vX.Y.Z -->`;
   sync the statusline script and pipeline-local.sh the same way into `~/.claude/pipeline/` (the shim imports a stable path, not the plugin cache — so an upgrade or reinstall never breaks the link).
3. **Install the shim**: does `CLAUDE.local.md` contain the verbatim line `@~/.claude/pipeline/PROTOCOL.md`?
   - File missing → create it; present but missing that line → append (it is the user's personal file, so appending is legitimate).
4. **Build-conventions block**: does the shim contain all five items — language baseline, full test command, per-task test selection mechanism, unimplemented stub, ticket-only slot (or `none`)? Any one missing → enter the **build-conventions interview** (below).
5. **Seed state and guard exclusions**: run `taskctl list` once — it self-seeds `tasks/task.html` and self-writes `.git/info/exclude` (existing mechanism; do not reinvent the wheel).
6. **Environment self-check**: does `~/.claude/settings.json` contain the statusLine and attribution keys? If missing, write them per `pipeline/settings.reference.json` **additively only** (never touch an existing key).

## Build-Conventions Interview (grill division of labor: look up facts yourself, let the user make the call)

First probe the build files at the project root, draft recommended answers from the table below, then **put each item to the user for a decision** — one at a time, with a one-line rationale, so the user can just reply "yes / make it X":

| Detected | Recommended: full test | Recommended: task selection | Recommended: unimplemented stub | Recommended: ticket-only slot |
|---|---|---|---|---|
| pom.xml | `mvn -q test` | JUnit5 `@Tag("task-<id>")` + `-Dgroups` | throw `UnsupportedOperationException` | failsafe `*IT` (runs under `mvn verify`, skipped by `mvn test`) |
| build.gradle(.kts) | `./gradlew test -q` | JUnit5 `@Tag` + `-DincludeTags` | same as above | a separate `integrationTest` source set |
| Cargo.toml | `cargo test -q` | test-name prefix `task_<id>` | `todo!()` | `#[ignore]` + `cargo test -- --ignored` |
| *.cabal / stack.yaml | `cabal test` / `stack test` | tasty `--pattern "task-<id>"` | `error "not implemented"` | `none` — shell steps in acceptance.sh |
| build.zig | `zig build test` | test-name prefix filter | `@panic("not implemented")` | `none` — shell steps |
| rebar.config | `rebar3 eunit` | scoping by module/group naming | `error(not_implemented)` | `none` — shell steps |
| package.json | depends on the test runner | vitest/jest `-t "task-<id>"` | `throw new Error(...)` | a separate config (e.g. `*.it.test.ts`) the default `test` script does not pick up |
| several / none | list the facts for the user, every call made by hand | | |  |

The ticket-only slot is where a check that must not run on every build can still be a test: something the full-test command skips and acceptance.sh invokes explicitly. The safe default is `none` — ticket-only checks are then shell steps in acceptance.sh, which every ecosystem supports. Recommend a slot only when the project already has one a fresh developer would recognize.

Write the decisions into the shim's build-conventions block. Completion test: all five items present + restated back to the user and confirmed + `taskctl list` runs clean.

## Boundaries

Never touch any tracked file the project already has; make only idempotent additions under `~/.claude/` (protocol/script sync and filling in missing settings keys); the legitimate output of a repeat init on the same project is "already initialized, nothing to do".
