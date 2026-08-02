#!/usr/bin/env bash
# 派发门禁。读取 statusline-budget.sh 落盘的 budget.json，机械判定：
#   exit 0  OK      —— 额度余量与上下文余量均在阈值之上，可派发
#   exit 1  LOW     —— 任一余量低于阈值，停止派发新任务，等待重置
#   exit 2  UNKNOWN —— 数据缺失或过期（statusline 未装 / 会话刚启动）
# 阈值（环境变量可覆盖）：
#   PIPELINE_MIN_QUOTA_PCT    订阅额度(5h 与 7d 取小)最低余量，默认 20
#   PIPELINE_MIN_CONTEXT_PCT  architect 上下文最低余量，默认 15
#   PIPELINE_BUDGET_MAX_AGE   budget.json 最大可信年龄(秒)，默认 900
set -euo pipefail
ROOT="${1:?用法: check-token-budget.sh <project-root>}"

if [ "${PIPELINE_PROVIDER:-}" = "local" ]; then
  echo "OK 本地模式——订阅配额不适用，门禁短路"
  exit 0
fi

MIN_QUOTA="${PIPELINE_MIN_QUOTA_PCT:-20}" MIN_CTX="${PIPELINE_MIN_CONTEXT_PCT:-15}" \
MAX_AGE="${PIPELINE_BUDGET_MAX_AGE:-900}" python3 - "$ROOT" <<'PY'
import datetime as dt
import json
import os
import sys
import time

path = os.path.join(sys.argv[1], ".claude", "pipeline", "budget.json")
min_quota = float(os.environ["MIN_QUOTA"])
min_ctx = float(os.environ["MIN_CTX"])
max_age = int(os.environ["MAX_AGE"])

try:
    with open(path, encoding="utf-8") as f:
        b = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    print("UNKNOWN 未找到可信的 budget.json —— 请确认已按 README 配置 statusline-budget.sh")
    sys.exit(2)

age = int(time.time()) - int(b.get("written_at") or 0)
if age >= max_age:
    print(f"UNKNOWN budget.json 已过期 {age}s（阈值 {max_age}s）")
    sys.exit(2)

quotas = [v for v in (b.get("five_hour_left_pct"), b.get("seven_day_left_pct")) if v is not None]
quota_left = min(quotas) if quotas else None
ctx_left = b.get("context_left_pct")


def fmt_reset(ts):
    return dt.datetime.fromtimestamp(ts).strftime("%m-%d %H:%M") if ts else "?"


parts = []
if quota_left is not None:
    parts.append(
        f"额度余 {quota_left:.0f}%（5h:{b.get('five_hour_left_pct')}% 重置 {fmt_reset(b.get('five_hour_resets_at'))}"
        f" / 7d:{b.get('seven_day_left_pct')}% 重置 {fmt_reset(b.get('seven_day_resets_at'))}）"
    )
if ctx_left is not None:
    parts.append(f"上下文余 {ctx_left:.0f}%")
detail = " · ".join(parts) if parts else "无可用指标"

low = (quota_left is not None and quota_left < min_quota) or (
    ctx_left is not None and ctx_left < min_ctx
)
if quota_left is None and ctx_left is None:
    print(f"UNKNOWN {detail}（API 计费账号无 rate_limits 属正常，可自定义本脚本接入 ccusage 等）")
    sys.exit(2)
if low:
    print(f"LOW {detail} · 阈值 额度≥{min_quota:.0f}% 上下文≥{min_ctx:.0f}%")
    sys.exit(1)
print(f"OK {detail}")
PY
