#!/usr/bin/env bash
# 由 Claude Code 的 statusLine 机制调用：stdin 收到会话 JSON。
# 职责：1) 把订阅额度(5h/7d)与上下文余量原子写入 <project>/.claude/pipeline/budget.json
#      2) 打印一行状态（模型 | ctx 余量 | 5h/7d 余量 | 5h 重置时间）
# 这是 token-budget 门禁的唯一数据来源；不装本脚本则门禁返回 UNKNOWN。
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
    reset = " · 5h重置 " + dt.datetime.fromtimestamp(h5_reset).strftime("%H:%M")

model = budget["model"] or "?"
print(f"[{model}] ctx余{pct(ctx_left)} | 额度 5h余{pct(h5_left)} 7d余{pct(d7_left)}{reset}")
PY
