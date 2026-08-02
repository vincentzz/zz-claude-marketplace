# Agent Pipeline · Three-Stage Development Pipeline

An architect → qa → dev pipeline on Claude Code: architect runs as the main session and owns alignment, design, and scheduling; qa / dev run as subagents and deliver, respectively, **red mechanical acceptance** and **the implementation that turns it green**; two read-only reviewers are invoked nested by qa / dev. The single source of truth for task state is `tasks/task.html`, every read and write goes through `taskctl`, and the acceptance verdict collapses to the exit code of `acceptance.sh`.

Skill authoring and decomposition follow [mattpocock/skills](https://github.com/mattpocock/skills) (MIT): small, composable, decidable; the borrowing map is at the end of this document.

```
                    ┌────────────────────────────────────────────────────────────┐
 user ↔ architect   │ /grill-me → /deep-module-design → /task-spec               │  main session (claude --agent architect)
   (single writer)  │ taskctl add/set/next/verify · /token-budget                │
                    └──────────────┬──────────────────────────┬──────────────────┘
                             dispatch (bg)              dispatch (bg)
                    ┌──────────────▼──────────┐           ┌───▼─────────────────────┐
                    │           qa            │           │           dev           │   subagents, one taskId each
                    │  skeleton + red tests   │─worktree─▶│ implement→green→deliver │   .worktrees/<id> · task/<id> (architect creates, acceptance gate reaps)
                    └──────────────┬──────────┘           └───┬─────────────────────┘
                            invoke (nested)            invoke (nested)
                    ┌──────────────▼──────────┐           ┌───▼─────────────────────┐
                    │       qa-reviewer       │           │      dev-reviewer       │   read-only pure functions → [BLOCKING]/[SUGGEST]
                    └─────────────────────────┘           └─────────────────────────┘
```

## Layout

```
CLAUDE.md                         Shared protocol for all roles (directory contract / state machine / single writer / git contract)
.claude/agents/                   architect · qa · dev · qa-reviewer · dev-reviewer
.claude/skills/                   12 skills (see the matrix at the end); each role preloads its own discipline via the skills field
.claude/skills/task-registry/scripts/taskctl.py          Sole editor of task.html + review-closure gate review-check (verified end-to-end)
.claude/skills/token-budget/scripts/check-token-budget.sh Dispatch gate (all OK/LOW/UNKNOWN branches verified)
.claude/pipeline/statusline-budget.sh                     statusline → budget.json data source
.claude/settings.json             statusline wiring + suggested git/mvn approval bypass
tasks/task.html                   Task registry (empty template)
tasks/specs/_template.html        spec template (auto-instantiated by taskctl add)
tasks/specs/_example.html + _example/acceptance.sh        A filled-in, full-marks example
```

## Installation

Prerequisites: Claude Code **≥ 2.1.219** (relies on nested subagents being on by default and on `${CLAUDE_PROJECT_DIR}` substitution), python3, git. jq is not needed.

1. Unpack **anywhere** (not straight into the project root) and run `bash install.sh <project-root>`. The installer **never overwrites an existing file**:
   - The pipeline protocol lives in `.claude/CLAUDE.md` and is loaded through a one-line `CLAUDE.local.md` shim at the repo root (`@.claude/CLAUDE.md`) — **your project's own CLAUDE.md is not touched by a single byte**, and both take effect at once (memory files stack, they don't override). If you already have a CLAUDE.local.md, the import line is appended idempotently (that file was yours to begin with).
   - All personal config lives in `.claude/settings.local.json` (the official personal slot, auto-gitignored) — statusline, permission list, attribution off, all in there, never colliding with the `.claude/settings.json` your team may commit.
   - Any existing file with a name the install would claim is skipped and listed, for you to merge by hand.
   Exclusion is a mechanical invariant: every taskctl run writes `tasks/`, `.worktrees/`, `.claude/`, and `CLAUDE.local.md` into `.git/info/exclude` (idempotent; paths already tracked by git are skipped). For a **personal repo** where you do want the contract-change history committed: just commit normally — taskctl gets out of the way for already-tracked paths.
2. The project root must be a git repository; the pipeline runs on **the branch you currently have checked out** (the baseline branch, pinned at dispatch time), and its relationship to develop/main is your team's CI/CD problem. `chmod +x .claude/pipeline/*.sh .claude/skills/*/scripts/*`.
3. On the first `claude` launch, accept workspace trust (both the statusline and project skills' allowed-tools depend on it).
4. statusline: `.claude/settings.local.json` already wires up `statusline-budget.sh`. If you have your own statusline, add a line `tee >(bash .claude/pipeline/statusline-budget.sh >/dev/null)` to your script or call it directly — **without it, /token-budget is UNKNOWN forever** (the gate degrades rather than fails).
5. Launch: `claude --agent architect --model fable` (the frontmatter already says `model: fable`; pinning it again on the command line is insurance for the main session — to make it the default, add `"agent": "architect"` to settings.json). Consider `--permission-mode acceptEdits`, or keep the git/mvn approval-bypass list in settings; otherwise permission prompts from background subagents keep surfacing and interrupting you.

## Installation (plugin distribution)

```bash
claude plugin marketplace add vincentzz/zz-claude-marketplace     # or a one-line curl install.sh
claude plugin install dev-pipeline@zz-claude-marketplace
cd <any project root> && claude --agent architect --model fable # init runs automatically
```

Upgrade: `claude plugin marketplace update zz-claude-marketplace` (or autoUpdate in settings).

**Profile switching**: `claude plugin enable|disable dev-pipeline`, or the `/plugin` UI — both are really just editing `enabledPlugins` in settings (key = `plugin@marketplace`, tri-state: true / false / absent → the plugin's defaultEnabled). The right lever for switching per project is **each project's `.claude/settings.local.json`** — settings has four layers, Managed > Local > Project > User, higher wins, so a plugin enabled at the project layer cannot be turned off at the user layer; only local can hold it down. And local stays personal and out of the repo, consistent with this harness's personal-tooling principle. Older versions of `/plugin` may write only the user layer; in that case, edit the local file by hand.

**Profiles are for switching, not for stacking**: multiple plugins can be enabled at once (independent booleans, no mutual exclusion), but every enabled plugin's full set of skill descriptions lives permanently in every session's system prompt (a token tax), and the collision semantics of two profiles sharing an agent name (both called architect) are undefined. The convention: exactly one pipeline profile enabled at each project's local layer; anything common across profiles gets split into its own small plugin — that is the stackable unit; a new profile's plugin.json ships with `defaultEnabled: false` (v2.1.154+), so installing it does nothing and only switching activates it. Dev mode: `claude plugin marketplace add /path/to/this-repo` (a local-path marketplace — edit the repo and it takes effect, no symlink needed).

**Three things to measure after install** (version-sensitive spots after the move to plugins; go to production once they're green): whether the `skills:` preload in agent frontmatter needs a `dev-pipeline:` prefix for in-plugin skills; how `${CLAUDE_SKILL_DIR}` resolves inside plugin skills; whether the statusline shows up once init has written it. If any one of the three is red, fall back to the manual user-level install (kept as backstop documentation).

## Manual user-level install (fallback path)

`bash install.sh user` puts the machinery into `~/.claude/` (5 agents, 12 skills, the protocol text `pipeline/PROTOCOL.md`, the statusline; settings.json is only added to, never modified — the statusLine and attribution keys are written only if absent). After that, **any project plugs in with zero copying**: run `claude --agent architect --model fable` at the project root, architect's startup self-check finds the project uninitialized, and it runs `/pipeline-init`'s idempotent checklist — create the `CLAUDE.local.md` shim (`@~/.claude/pipeline/PROTOCOL.md`), run the **build-conventions interview** (probe pom.xml/Cargo.toml/build.zig… and propose answers you approve item by item: language / full-test command / task selection mechanism / unimplemented stub), then `taskctl` self-seeds `tasks/` and writes the exclusion guard. The legitimate output of a repeat init is "already initialized, nothing to do".

memory stacking semantics: `~/.claude/CLAUDE.md` (if present) is **concatenated** with the project CLAUDE.md and CLAUDE.local.md — which is why the protocol text does not live in `~/.claude/CLAUDE.md` (it would pour into every unrelated project); the project shim imports it on demand. Know the inherent cost of the user-level install: the descriptions of the agents/skills sit permanently in the system prompt of **every** project (a few hundred tokens), and names like `qa`/`dev` appear in every project's agent list — inert and harmless, but present. The full per-project copy (`install.sh project <root>`) is still available, and suits anyone who wants to hack the protocol itself project by project.

## Directory layout after install (measured on a team repo)

Sandbox scenario: the project has its own `CLAUDE.md` (shared team context), a team-tracked `.claude/settings.json`, and one team skill. After installing and running taskctl once (`[T]` = git-tracked · team-shared, `[x]` = masked by `.git/info/exclude` · personal tooling):

```
├─ CLAUDE.md                       [T]  Shared team context, not one word changed
├─ CLAUDE.local.md                 [x]  Loader shim (@.claude/CLAUDE.md)
├─ pom.xml · src/**                [T]  The project proper (code and tests from tasks merge in here; you sign the commit)
├─ .claude/
│  ├─ settings.json                [T]  Shared team settings, tracked as usual
│  ├─ skills/team-conventions/     [T]  Shared team skill, tracked as usual
│  ├─ CLAUDE.md                    [x]  Pipeline protocol text
│  ├─ settings.local.json          [x]  Personal settings (statusline / permissions / attribution off)
│  ├─ agents/ (5)                  [x]
│  └─ skills/ (11) · pipeline/     [x]
└─ tasks/                          [x]  spec · task.html · notes · reviews
```

Three takeaways: **the boundary is at file level, not directory level** — ignore rules don't affect already-tracked files, so with all of `.claude/` in exclude the team's assets sit untouched while the personal delta goes entirely invisible; **all five mechanical checks pass** — the team's tracked file list is unchanged to the letter, `git status` is completely clean, a dry `git add -A` finds nothing to add (immune to a slip of the hand), `check-ignore -v` can name the exact rule line masking each path, and a teammate's clone shows zero trace of the harness; **runtime memory stacks in three layers** — the team's root CLAUDE.md plus the personal shim importing the pipeline protocol, so shared context and personal protocol are both live and neither knows the other exists.

## Mapping to the original design

| Your item | Where it landed |
|---|---|
| architect a. grill-me alignment | `/grill-me` (adapted from mattpocock/grilling, adding a "ready to put pen to spec" completion criterion + **boundary interrogation**: dependency trade-offs / the three-part placement test / change-distribution calibration — the procedure does the homework, the judgment call stays with you) |
| architect b. deep module interface and responsibility boundary | `/deep-module-design`: Ousterhout's vocabulary + orthogonality/composability partitioning criteria + the **three-way boundary split** (must know 2.1 / need not know 2.2 / must not know 2.5, forbidden knowledge) + the **failure-attribution table** (mechanical accountability, built for blame) + design it twice. Forbidden knowledge ≠ read ban: the core is a provenance constraint of being **treated as unknown** (knowledge with no spec provenance may not enter a decision, priors in the weights included); the discipline lives in CLAUDE.md, the per-task delta in spec 2.5, and implementation hints travel the `specs/<id>/architect/dev-hints.md` channel |
| architect c./d. generate specs, maintain status and priority | `/task-spec` + `taskctl`; row order is priority, `add --top/--after` jumps the queue, `move` reorders |
| architect e./f. wake QA/dev only when remaining budget ≥20%, and update the list | the `/token-budget` gate (dispatch only on exit 0) + `taskctl set … in-progress` |
| architect g. remaining <20%, stop dispatching, wait for refresh | gate exit 1 → stop dispatching new tasks and announce the `resets_at` reset time |
| QA a–f | `qa.md` steps 1–8: enter the worktree (architect creates it and pins the baseline before dispatch) → **lay down the skeleton** → red tests → acceptance.sh → qa-reviewer closure → commit |
| dev a–f | `dev.md` steps 1–6: enter the worktree → implement to green → dev-reviewer closure → deliver a green branch (merging and worktree teardown happen at architect's acceptance gate) |
| qa-reviewer / dev-reviewer | read-only nested subagents + the `/review-test-cases` and `/review-code` yardsticks, emitting [BLOCKING]/[SUGGEST] |
| task-management directory structure | exactly as you gave it; task.html's `taskId/Test/Dev/Task` header is preserved verbatim |
| a skill of its own per agent | the subagent frontmatter's `skills:` field **preloads the full text** of each role's discipline (see the matrix) |

## Eight deliberate deviations (design decisions, open to debate)

1. **QA does not merge red tests into the baseline branch.** Your "QA commits and merges" landed as: commit and advance the `task/<id>` branch, and pull the baseline into the branch before starting work; architect merges it back with `--no-ff` at the acceptance gate (see items 7 and 8). What that buys is the **evergreen baseline** invariant — otherwise `taskctl verify` on the main checkout means nothing.
2. **"Go ask architect for work" landed as a dispatch model.** Single-writer task.html is the bedrock of accountability, and qa/dev helping themselves would introduce multiple writers. Pull semantics are preserved mechanically by `taskctl next test|dev` (auditable selection rules), and the "asking" happens inside architect's dispatch prompt. True pull semantics were vetoed along with teams (see the decision record at the end); `taskctl next` is pull's auditable stand-in.
3. **"Remaining tokens" takes the subscription-quota window semantics.** You said "wait for token refresh", which maps to the `rate_limits` 5h/7d windows Claude Code's statusline provides (including `resets_at`). The gate compares the **smaller** of the 5h and 7d remainders against the threshold (default 20%), plus a separate architect context-remaining threshold (default 15%) — running out of context kills the scheduling session just as dead. API-billed accounts have no rate_limits, so the gate degrades to UNKNOWN automatically (patch the script yourself to hook up ccusage or similar).
4. **New: acceptance.sh as the single mechanical acceptance entry point.** Your "mechanically decidable" is made concrete as: one command, the exit code is the verdict, qa delivers it, and dev and architect run the same script in two places and reach the same conclusion. `taskctl verify <id>` is its wrapper.
5. **Java's test-first compilation problem → interface skeleton up front.** Tests before implementation, in Java, means it won't even compile. The fix is built into the flow: spec 2.1 requires **compile-complete** interface signatures (delivered by architect), and qa's first step turns them into a skeleton that throws `UnsupportedOperationException` — so "red" always means **red at runtime**, and a compile failure is defined as a contract violation on qa's side. Accountability stays clear.

6. **Review closure moved into the status gate.** In your original design reviewers only "made suggestions"; here "the suggestions have been dealt with" becomes a mechanically decidable fact: `taskctl set … done` has review-check built in — the corresponding reviewer's latest `review-N.md` must contain no `[BLOCKING]`, must include the verbatim conclusion line "Conclusion: no blocking items", and the round count must be ≤2, or the status won't move. Review closure still happens as an inner loop in qa/dev's hot context (fixes are cheap there), but **the verdict on whether it closed belongs to the gate** — the reviewed party may do the work, but may not sign for itself. `--force` is the only escape hatch, and it must leave a trace in notes.
7. **Merge authority lives at the acceptance gate.** dev stops at delivering a green branch; the `--no-ff` merge, the **full test suite** after merging (every task's tests, to catch cross-task regressions), the revert on red, and the worktree teardown are all executed by architect inside the gate. The evergreen baseline is upgraded from "detected after the fact" to "mechanically prevented at the door", and irreversible steps and status-advancing authority collapse into one role. Tamper-evident history for review files is optional: stand up a private git inside `tasks/` (the harness stays out of the team repo, see the decision record). Conflict-resolution authority does **not** move up with it: architect's don't-write-code invariant stays absolute — on a conflict it issues a cross-task intent brief (it wrote both specs; that is knowledge only it legitimately has), and dev synthesizes the resolution inside the worktree and re-runs acceptance.

8. **Relative baseline branch + worktree lifecycle owned by architect.** The harness presumes no main: the baseline is whatever branch is current at the moment architect dispatches, pinned in `tasks/specs/<id>/base-branch`; the worktree is created by architect before dispatch (eliminating the "qa creates the tree at runtime, you switched branches in the meantime" baseline race); the acceptance gate merges back into that same baseline, and mechanically checks at the door that the current branch == the pinned baseline. Merging into shared branches like develop/main is your team's CI/CD jurisdiction — green inside the gate is your promise about your own branch; green in CI is the team's promise about the shared branch.

## What one round looks like

```
you:        build me an in-process token-bucket rate limiter
architect:  (grill-me aligns question by question → deep-module design → taskctl add "token-bucket rate limiter" → pin baseline, create worktree)
            Registered 0001, spec at tasks/specs/0001.html. Budget OK, dispatching qa.
qa (bg):    enter architect's prepared .worktrees/0001 → lay down the skeleton → write @Tag("task-0001") tests → acceptance.sh red state
            → invoke qa-reviewer → handle 2 BLOCKING items → commit → hand in report (AC↔test mapping, red-state evidence)
architect:  report complete → taskctl set 0001 test done (built-in qa-reviewer review-closure check) → budget OK → dispatch dev.
dev (bg):   merge baseline → turn each AC green → dev-reviewer closure → green again → deliver a green branch (no merge) → hand in report
architect:  acceptance gate: verify --checkout green → --no-ff merge → full test suite green → set 0001 dev done (built-in review-closure check) → tear down worktree → report all green.
```

Any role that finds an error in the spec: stop, write notes, escalate for arbitration (CLAUDE.md's "stop on overstep"). An architect reversal is recorded in the spec's change log — the accountability chain never breaks.

## Role × skill matrix

| Skill | architect | qa | dev | qa-rev | dev-rev | Source |
|---|---|---|---|---|---|---|
| grill-me | call | | | | | adapted from mattpocock/grilling |
| deep-module-design | call | | | | preload | adapted from codebase-design + DESIGN-IT-TWICE, extended with the failure-attribution table |
| task-spec | call | | | | | original (aligned with the to-spec idea) |
| task-registry (taskctl) | call | read-only ref | read-only ref | | | original |
| worktree-flow | | preload | preload | | | conflict discipline borrowed from resolving-merge-conflicts |
| mechanical-acceptance | | preload | | preload | | three anti-patterns distilled from tdd |
| agent-notes | | preload | preload | | | original |
| review-test-cases | | | | preload | | original |
| review-code | | | | | preload | adapted from code-review's two axes + trimmed for Java code smells |
| coding-standards | | | preload | | preload | original: cold/hot partitioning priorities (in the hot path, performance is second only to correctness, and the call needs provenance), modern features, English-only code (with a mechanical grep check) |
| pipeline-init | call | | | | | original: idempotent project init — loader shim, build-conventions interview (fact self-check / decision sign-off), taskctl self-seeding reuse |
| token-budget | call | | | | | original (statusline rate_limits data source) |

"preload" = the subagent frontmatter's `skills:` field injects the full text at startup; "call" = triggered by description or invoked explicitly as `/name`. The upstream repos are MIT-licensed; adaptations are credited in a footnote at the end of each SKILL.md.

## Porting to other languages

The mechanical layer (taskctl, task.html, the gates, budget, review closure) is **language-agnostic** — every verdict collapses to the exit code of `acceptance.sh`, and the script is the language seam. There are five porting surfaces, each with a single customization point:

1. **The build-conventions block in CLAUDE.md**: language baseline, full-test command, per-task test selection mechanism, unimplemented stub (every other file merely references this block; no language details are duplicated).
2. **The contents of acceptance.sh**: swap in `cargo test task_<id>` / `pytest -m task_<id>` / `cabal test --test-options="--pattern task-<id>"` and so on — the script contract (exit 0 ⟺ everything passed, idempotent, non-interactive) is unchanged.
3. **The language-features section of coding-standards**: replace the whole section with target-language instances; the priorities and cold/hot partitioning stay.
4. **settings.local.json permissions**: swap `Bash(mvn *)` for your build tool.
5. **The example spec** (`_example.html`) is a Java demo, for reference only; no need to port it.

The general statement of the red-state rule: the build must pass (compilation for compiled languages, load/import for dynamic ones), and red must be red at a runtime assertion or an unimplemented stub.

## Local fallback mode (everyone switches to a local LLM when quota runs out)

One command to switch: `PIPELINE_LOCAL_MODEL=qwen3-coder:30b bash ~/.claude/pipeline/pipeline-local.sh`. How it works: switching everyone at once needs no process separation (BASE_URL is process-scoped to begin with, so the whole thing follows along); on each run the launcher **mechanically derives** the local profile `~/.claude-pipeline-local` from `~/.claude` (agents' `model:` lines replaced with the local model, reviewers optionally pinned to a smaller model, settings injected with the local essentials) and launches through `CLAUDE_CONFIG_DIR` — the derived artifact is never hand-maintained, the main profile stays uncontaminated, and switching back to the subscription restores the original state.

Three things handled automatically: frontmatter `fable`/`opus` sent verbatim to a local endpoint would 404 — already substituted per role, with tier-mapping env vars as a backstop; the attribution header invalidates the local KV cache on every request (~90% slower) — already turned off in the derived settings; the budget gate has no rate_limits locally, so it would be permanently UNKNOWN and drop concurrency — `PIPELINE_PROVIDER=local` short-circuits it to OK. **The mechanical layer runs exactly as before**: taskctl, the status gates, review-check, and acceptance exit codes don't know what model you're on, and verify holds local output to the same yardstick as Fable's.

### Decision table: what signal, what action

| Trigger signal (readable from check output / in-session notices) | Verdict | Action |
|---|---|---|
| LOW, triggered by the **5h** remainder (7d still has room) | at most a 5-hour wait | **Wait.** Stop dispatching new tasks, let the running ones finish; a few hours isn't worth a context switch |
| LOW, triggered by the **7d** weekly cap (reset measured in days) | the main scenario for local fallback | Run the mechanical criterion: `taskctl next dev` **produces something** (a task with spec + red tests ready exists) → switch to local and work the dev lane; exit 3 (nothing dev-ready) → wait for the reset, don't send a local model to do grilling/spec work |
| **Fable's 50% pool** hits the cap (an in-session notice, not in budget.json) | not a pipeline-level event | **Don't switch to local.** `/model opus` in the main session, temporarily drop dev-reviewer to `opus` — only the two Fable roles are affected, everything else carries on |
| LOW, triggered by the **context** remainder (quota still has room) | not a quota problem | **Don't switch to local.** Let running tasks finish → restart the architect session (state lives in tasks/, nothing lost) → re-dispatch the in-progress rows |
| UNKNOWN (statusline not installed / API billing / stale data) | a data problem | Fix the statusline, or accept degrading to one subagent at a time; unrelated to local fallback |
| **Hard cut mid-session** (messages rejected outright, not blocked by the gate) | quota exhausted mid-task | The subagent is dead but nothing is lost: worktree, commits, and notes are all on disk. Switch to local per the table above or wait for the reset; after restarting, re-dispatch from task.html's in-progress rows and the idempotent flow picks up where it left off |

### Switching sequence

**Subscription → local**: ① confirm the local endpoint is up, the model is pulled, and context is ≥64K (`OLLAMA_CONTEXT_LENGTH=65536`); ② exit the subscription session; ③ `PIPELINE_LOCAL_MODEL=<model> bash ~/.claude/pipeline/pipeline-local.sh`; ④ architect's startup self-check → `taskctl list` → re-dispatch in-progress and dev-ready tasks; ⑤ work the dev lane only, and for tasks where the local model repeatedly fails verify or hits maxTurns: set them back to in-progress, note it, and leave them for the subscription.

**Local → subscription** (reset time arrives): ① let the running local subagents finish, or just abandon them (idempotent — re-dispatch resumes); ② exit, `claude --agent architect --model fable`; ③ the gate returns to OK and scheduling continues as usual; ④ optional quality backfill: for tasks merged during the local period (qa/dev notes should carry a local marker), pick the important ones and have the subscription-side reviewer re-check the diff — anything a local reviewer waved through is worth one after-the-fact spot check by a strong verifier.

General discipline: after switching, the weakest link flips from dev to architect/qa judgment, so local mode works the dev lane first; `maxTurns` is the backstop against tool infinite loops; switching in either direction is only "restart the session + re-dispatch" — tasks/ plus git is the entire state.

### Operational discipline (capability reality)

After switching to local, the weakest link flips from dev to architect/qa judgment: local mode **works the dev lane first** (tasks whose spec and red tests are ready, where a weak model is backstopped by mechanical acceptance); leave grilling, spec writing, and arbitration for new requirements to the subscription model after the reset. Give the local endpoint a `maxTurns` backstop (tool_choice may be ignored), and plenty of context, 64K+.

### Situational playbook (signal → diagnosis → action)

| Signal | Diagnosis | Action |
|---|---|---|
| LOW, 5h reset within hours | 5h window exhausted | Wait for the reset by default; switch to local only if `taskctl next dev` produces something and it's urgent |
| LOW, 7d bottomed out, reset days away | weekly cap exhausted | The main scenario: there's a backlog of Test=done awaiting dev → switch to local and work the dev lane; only grilling-pending work left → wait |
| LOW but quota is fine, context <15% | architect session bloat | **Don't switch to local**: finish up → exit → reopen the subscription session (state lives in tasks/, nothing lost) |
| Fable unavailable / auto-downgraded | Fable's 50% pool capped, total pool not exhausted | `/model opus` and carry on; temporarily drop dev-reviewer to opus |
| Gate permanently UNKNOWN | statusline not installed / just started / API billing | Install the statusline; if you won't, accept one subagent at a time |
| Decided to go local | — | Preflight: model in place, context ≥64K, endpoint reachable → `PIPELINE_LOCAL_MODEL=… pipeline-local.sh`; in-flight losses are re-dispatched from the in-progress rows |
| Subscription resets while running local | — | Push through to the acceptance gate or just stop → reopen the subscription session; optional: run one subscription-level review over the range merged during the local period |
| Local dev won't converge | tool_choice ignored | maxTurns backstops the timeout, verify bounces it back for re-dispatch |

The principle running through all of it: on LOW, first identify which pool triggered it (5h / 7d / context — the prescriptions differ); the mechanical precondition for going local is the exit code of `taskctl next dev`; switching direction is always restarting a session, never migrating state — state never lives in the session.

## Decision record: agent teams (vetoed)

**Conclusion: qa/dev are permanently architect's subagents; agent teams are not adopted.** The rationale is frozen below so nobody relitigates it later:

1. **Token economics (decisive)**: the official docs themselves admit teams have high coordination overhead and consume noticeably more tokens than a single session. Structural reason: a teammate is a long-lived session whose context grows monotonically across tasks — exactly the shape where cache-read amplification, which we've quantified, is most expensive; a subagent is read-once-then-discard, capped at 45–90K of context and then thrown away, so per-task cost has a hard ceiling.
2. **skills preloading stops working**: teammates don't apply the `skills`/`mcpServers` fields of an agent definition — the "each role carries its own discipline" design breaks, and discipline has to be injected by message, which is pricier and less reliable.
3. **Experimental feature**: flag-gated, `/resume` doesn't restore teammates, behavior drifts between versions.
4. **Conflicts with the forbidden-knowledge structure**: a long-lived dev that worked task A *remembers* A, so on task B "treated as unknown" degrades from a structural guarantee into a discipline burden. A subagent's read-once-then-discard is the mechanical implementation of a clean room — the dev handed each task has never seen any other task.

The auditable stand-in for true pull semantics (teammates claiming their own work) is `taskctl next`: the selection rule is mechanical and the single writer is intact. SendMessage is a teams-gated tool, and this design depends on no session continuation whatsoever — continuing work is always a re-dispatch, and the idempotent flow (reuse the tree if it exists, pick up from notes if they exist) makes re-dispatch lossless.

## Decision record: the harness is personal tooling and stays out of the team repo

**Conclusion: in a team repository, `.claude/**` and `tasks/**` belong to the committer personally, permanently untracked (via `.git/info/exclude`).**

Rationale: **the final committer is the sole accountable party, Claude is not** — an entity that cannot be held accountable has no business on the accountability chain. Three things follow:

1. **Bring your own tools, sign your own output**: the harness is in the same category as your editor config — private means of production for the output you commit. Whether you use Claude, what model matrix you use, how many review rounds you run, are all the committer's private business; what the team judges is the artifact you signed and committed (code + tests, through the team's own PR/CI process), not your production process.
2. **Don't manufacture shared things to blame**: committing the harness would give birth to "the pipeline's fault" as an excuse entity. As personal tooling, attribution for commit quality is unique: you chose your tools, you signed your output.
3. **Single attribution**: `.claude/settings.local.json` already sets `attribution: {commit: "", pr: ""}` — no Co-Authored-By: Claude and no Generated with footer in commits; git history contains only people.

The line between deliverable and tooling: `src/**` (including tests — they merge in with the task branch) is signed over to the team; `tasks/**` (spec, notes, review) and `.claude/**` stay with you. **The executable part of the contract (the tests) goes into the team repo; the negotiation record of the contract (spec / reviews) stays in your personal workshop.**

The accompanying layout decision: `tasks/` **stays at the project root and does not move into `.claude/`**. Three reasons: it is the human face of the harness (specs get read, task.html gets opened in a browser, notes get flipped through), and a dot directory hides it and gets skipped by `rg` by default; the premise ".claude/ isn't committed" is unreliable — teams deliberately committing `.claude/` (shared commands/skills) is exactly the official design intent, so stuffing tasks in there makes it *more* likely to get swept into a commit; and `.claude/` is Claude Code's reserved namespace, where colliding with the tool's future directory claims is worse than colliding with the project. The accidental-commit risk is mechanically eliminated by taskctl's self-guarding exclusion (the tool that owns the state guarantees the state stays out of the repo).

The price, already accounted for: tamper-evident review files drop from git history to an optional private git (`cd tasks && git init`, one line); specs are invisible across team members, so cross-person coordination of task-level orthogonality goes back to the human layer (PRs, design reviews) — where it belonged anyway. Personal repos aren't bound by this (see the two modes in the installation section).

## Tuning knobs

- **Model matrix** (already in the frontmatter): architect=`fable`, qa=`opus`, dev=`opus`, qa-reviewer=`opus`, dev-reviewer=`fable`. Rationale: spec and arbitration are the highest-leverage points, so Fable is spent on architect; the dev line keeps the "cheap generator + expensive verifier" asymmetry (dev-reviewer is the cheapest session in the whole pipeline, so upgrading it to Fable has the lowest marginal cost and the highest payoff). Note that on a Max subscription Fable counts into the shared pool at roughly 2× weight and is capped at 50% of the weekly limit — hitting that cap affects only the Fable roles, and you just temporarily drop architect/dev-reviewer to `opus` (edit the frontmatter, or use `/model`). Aliases drift with new releases; to pin them hard, substitute the full model strings from the `/model` list. **The matrix is a default, not a constant**: Agent invocations support a per-invocation model override (resolution order: `CLAUDE_CODE_SUBAGENT_MODEL` env > call parameter > frontmatter > main session), and architect picks models dynamically on three criteria — difficulty downshift (simple dev tasks go to sonnet, backstopped by the mechanical layer), watermark downshift (below 40% remaining, drop one tier to extend the runway), failure upshift (a re-dispatch goes one tier above the last attempt) — forming a fable→opus→sonnet→local continuum of graceful degradation. Note that `CLAUDE_CODE_SUBAGENT_MODEL` has the highest priority and will flatten every per-agent distinction; don't set it globally.
- **Dynamic model gradient**: architect can pass a per-invocation model parameter at dispatch (the sonnet/opus/haiku enum only; fable and local models can't be passed — the former relies on frontmatter, the latter requires switching the whole process, see local fallback mode). Policy: in the comfortable band, follow the matrix; in the tight band, drop dev to sonnet (the Sonnet 5 / Opus 5 price gap has narrowed to 1.67×, so a downshift saves about 40% rather than the 5× of the old days — worth it for dev only, not for qa); a downshifted task bounced back by verify goes up to opus on re-dispatch. **Do not set CLAUDE_CODE_SUBAGENT_MODEL** (upstream bug: it swallows the per-invocation parameter).
- **Concurrency**: architect hardcodes 1 qa + 1 dev. Before adding concurrency, think through merge serialization (several devs merging back into the baseline at once needs a merge queue).
- **Thresholds**: `PIPELINE_MIN_QUOTA_PCT` (20), `PIPELINE_MIN_CONTEXT_PCT` (15), `PIPELINE_BUDGET_MAX_AGE` (900s).
- **Review rounds**: the cap of 2 is already mechanically enforced by taskctl (`MAX_REVIEW_ROUNDS`); "at most two rounds" in the agent files is just a restatement of the same contract.
- **Shape of the acceptance command**: the examples use Maven + JUnit5 `@Tag`; switching build systems only requires editing section 3's sketch in `_template.html` and `_example/acceptance.sh`.

## Known pitfalls

- `cd` inside a subagent doesn't persist across commands — every in-worktree operation uses `git -C` or `cd … && …` (CLAUDE.md makes this an iron rule; it's still the most common source of accidents).
- Continuing a subagent = **re-dispatch**: SendMessage is a teams-gated tool that doesn't exist in the default configuration (upstream issue #35240), and this design doesn't rely on it — the qa/dev flows are idempotent, and a re-dispatched fresh instance picks up from spec/notes/worktree.
- The door check in step ① of the acceptance gate: the main checkout should be clean — with `tasks/` and `.claude/` out of the repo it's clean by construction, so if it's dirty, some role has overstepped and touched the code area.
- Recovering a session: task state lives entirely in `tasks/` and git, so if the architect session dies, just reopen with `claude --agent architect` and carry on; half-run subagents don't recover automatically — re-dispatch from task.html's in-progress rows (both the qa and dev flows are designed idempotent: reuse the tree if present, skip the skeleton if present).
- `tasks/task.html.lock` is taskctl's lock file; don't commit it (already in .gitignore).
- Repos that already have a `tasks/` directory at the project root hit a name collision: the harness's `tasks/` path is hardcoded in the protocol files and in taskctl, so it needs a global find-and-replace before use (known limitation).
- The substance of forbidden knowledge is the provenance discipline of "treated as unknown", and it **cannot be implemented with access control** — most of the knowledge to be banned is in the weights. The mechanical handholds are on the artifact side: qa assertions must cite spec provenance in a margin note (if you can't write it, delete the assertion); dev notes must contain a "free-choice list" for the places the spec is silent; reviewers run a derivability check (any structure/constant/semantics not derivable from the spec = evidence of violation). Banning Read by path with `disallowedTools` only hardens the auxiliary read-ban hygiene (blocking incremental contamination); don't expect it to carry the substance of forbidden knowledge.
