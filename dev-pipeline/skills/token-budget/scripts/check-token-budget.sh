#!/usr/bin/env bash
# Dispatch gate. Reads the budget.json written to disk by statusline-budget.sh and decides mechanically:
#   exit 0  OK      -- both quota and context remaining are above threshold, dispatch is allowed
#   exit 1  LOW     -- either one is below threshold: stop dispatching new tasks and wait for the reset
#   exit 2  UNKNOWN -- data missing or stale (statusline not installed / session just started)
# Thresholds (overridable via environment variables):
#   PIPELINE_MIN_QUOTA_PCT    minimum subscription quota remaining (the lesser of 5h and 7d), default 20
#   PIPELINE_MIN_CONTEXT_PCT  minimum architect context remaining, default 15
#   PIPELINE_BUDGET_MAX_AGE   maximum trustworthy age of budget.json in seconds, default 900
set -euo pipefail
ROOT="${1:?usage: check-token-budget.sh <project-root>}"

if [ "${PIPELINE_PROVIDER:-}" = "local" ]; then
  echo "OK local mode -- subscription quotas do not apply, gate short-circuited"
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
    print("UNKNOWN no trustworthy budget.json found -- check that statusline-budget.sh is configured as per the README")
    sys.exit(2)

age = int(time.time()) - int(b.get("written_at") or 0)
if age >= max_age:
    print(f"UNKNOWN budget.json is {age}s stale (threshold {max_age}s)")
    sys.exit(2)

quotas = [v for v in (b.get("five_hour_left_pct"), b.get("seven_day_left_pct")) if v is not None]
quota_left = min(quotas) if quotas else None
ctx_left = b.get("context_left_pct")


def fmt_reset(ts):
    return dt.datetime.fromtimestamp(ts).strftime("%m-%d %H:%M") if ts else "?"


parts = []
if quota_left is not None:
    parts.append(
        f"quota {quota_left:.0f}% left (5h:{b.get('five_hour_left_pct')}% resets {fmt_reset(b.get('five_hour_resets_at'))}"
        f" / 7d:{b.get('seven_day_left_pct')}% resets {fmt_reset(b.get('seven_day_resets_at'))})"
    )
if ctx_left is not None:
    parts.append(f"context {ctx_left:.0f}% left")
detail = " · ".join(parts) if parts else "no metrics available"

low = (quota_left is not None and quota_left < min_quota) or (
    ctx_left is not None and ctx_left < min_ctx
)
if quota_left is None and ctx_left is None:
    print(f"UNKNOWN {detail} (no rate_limits is normal on API-billed accounts; adapt this script to pull from ccusage or similar)")
    sys.exit(2)
if low:
    print(f"LOW {detail} · thresholds quota>={min_quota:.0f}% context>={min_ctx:.0f}%")
    sys.exit(1)
print(f"OK {detail}")
PY
