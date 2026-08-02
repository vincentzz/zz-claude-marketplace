---
name: token-budget
description: The token budget gate checked before dispatching a subagent. Use before architect invokes qa/dev each time, or when the user asks about remaining quota.
allowed-tools: Bash(bash ${CLAUDE_SKILL_DIR}/scripts/check-token-budget.sh *)
---

# Token Budget Gate

Data source: `.claude/pipeline/statusline-budget.sh` (on every statusline refresh it writes the 5h/7d subscription quota headroom, reset times, and context headroom into `.claude/pipeline/budget.json`). The gate decides mechanically from that file and estimates nothing.

Check command (run before every dispatch):

```
bash ${CLAUDE_SKILL_DIR}/scripts/check-token-budget.sh ${CLAUDE_PROJECT_DIR}
```

## Verdicts and Actions

| Exit code | Meaning | architect's action |
|---|---|---|
| 0 `OK` | Quota headroom (the smaller of 5h and 7d) ≥ threshold, and context headroom ≥ threshold | Dispatch normally |
| 1 `LOW` | Either headroom is below its threshold | **Stop dispatching new tasks**; report the headroom and reset times to the user; let running subagents wind down; then offer the user two options — wait for the reset, or **switch to local fallback mode** (exit this session, `PIPELINE_LOCAL_MODEL=<model> bash ~/.claude/pipeline/pipeline-local.sh`; state is complete in tasks/ and git, restarting loses nothing, and an in-progress task resumes on re-dispatch) |
| 2 `UNKNOWN` | budget.json missing/stale (statusline not installed, session just started, API-billed account) | Remind the user once (point at the statusline setup in the README); degrade to at most 1 subagent at a time and continue |

Thresholds are adjusted via environment variables: `PIPELINE_MIN_QUOTA_PCT` (default 20), `PIPELINE_MIN_CONTEXT_PCT` (default 15), `PIPELINE_BUDGET_MAX_AGE` (default 900 seconds).

Context headroom refers to architect's own main session — it is a scarce resource too: if LOW is triggered by context, first let running tasks wind down and summarize the necessary state, then suggest the user open a new session to continue (all task state lives in `tasks/`, so continuing loses nothing).
