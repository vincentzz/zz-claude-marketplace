#!/usr/bin/env bash
# Invoked by Claude Code's statusLine mechanism: the session JSON arrives on stdin.
# Responsibilities: 1) atomically write the subscription quota (5h/7d) and the remaining context
#                      to <project>/.claude/pipeline/budget.json
#                   2) print one status line (model | ctx remaining | 5h/7d remaining | 5h reset time)
# This is the only data source for the token-budget gate; without this script the gate returns UNKNOWN.
set -euo pipefail

STATUSLINE_JSON="$(cat)" python3 - <<'PY'
import datetime as dt
import json
import os
import sys
import tempfile
import time

data = json.loads(os.environ["STATUSLINE_JSON"])

proj = (data.get("workspace") or {}).get("project_dir") or data.get("cwd") or "."
out_dir = os.path.join(proj, ".claude", "pipeline")
os.makedirs(out_dir, exist_ok=True)

ctx_left = (data.get("context_window") or {}).get("remaining_percentage")
rl = data.get("rate_limits") or {}


def window(name):
    w = rl.get(name) or {}
    used = w.get("used_percentage")
    return (None if used is None else round(100 - used, 1)), w.get("resets_at")


h5_left, h5_reset = window("five_hour")
d7_left, d7_reset = window("seven_day")

budget = {
    "written_at": int(time.time()),
    "model": (data.get("model") or {}).get("display_name"),
    "context_left_pct": ctx_left,
    "five_hour_left_pct": h5_left,
    "five_hour_resets_at": h5_reset,
    "seven_day_left_pct": d7_left,
    "seven_day_resets_at": d7_reset,
}

fd, tmp = tempfile.mkstemp(dir=out_dir, prefix=".budget.")
with os.fdopen(fd, "w") as f:
    json.dump(budget, f, ensure_ascii=False)
os.replace(tmp, os.path.join(out_dir, "budget.json"))


def pct(v):
    return "--" if v is None else f"{v:.0f}%"


reset = ""
if h5_reset:
    reset = " · 5h reset " + dt.datetime.fromtimestamp(h5_reset).strftime("%H:%M")

model = budget["model"] or "?"
print(f"[{model}] ctx {pct(ctx_left)} left | quota 5h {pct(h5_left)} 7d {pct(d7_left)}{reset}")
PY
