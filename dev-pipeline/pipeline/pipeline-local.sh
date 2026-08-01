#!/usr/bin/env bash
# 本地降级模式启动器：订阅额度耗尽时，全流水线切换到本地 LLM。
#   用法:  PIPELINE_LOCAL_MODEL=qwen3-coder:30b bash ~/.claude/pipeline/pipeline-local.sh [claude 附加参数]
#   可选:  PIPELINE_LOCAL_URL   本地 Anthropic 兼容端点（默认 http://localhost:11434，Ollama ≥0.14）
#          PIPELINE_LOCAL_SMALL 给两个 reviewer 用的小模型（缺省与主模型相同）
#          PIPELINE_DRYRUN=1    只生成 profile 不启动（测试用）
# 注意:  刻意不用 CLAUDE_CODE_SUBAGENT_MODEL——它优先级最高，会碾平 reviewer 的小模型区分。
# 原理:  从 ~/.claude 机械派生 ~/.claude-pipeline-local（agents 的 model 行替换为本地模型，
#        skills/pipeline 原样拷贝，settings 注入本地必需项），经 CLAUDE_CONFIG_DIR 启动。
#        派生产物每次重新生成——不手工维护，主 profile 零污染。
set -euo pipefail

SRC="${CLAUDE_USER_DIR:-$HOME/.claude}"
DST="${SRC}-pipeline-local"
MODEL="${PIPELINE_LOCAL_MODEL:?需要 PIPELINE_LOCAL_MODEL（如 qwen3-coder:30b）}"
SMALL="${PIPELINE_LOCAL_SMALL:-$MODEL}"
URL="${PIPELINE_LOCAL_URL:-http://localhost:11434}"

rm -rf "$DST" && mkdir -p "$DST/agents"
cp -r "$SRC/skills" "$SRC/pipeline" "$DST/" 2>/dev/null
for f in "$SRC"/agents/*.md; do
  base="$(basename "$f")"
  case "$base" in
    qa-reviewer.md|dev-reviewer.md) m="$SMALL" ;;
    *) m="$MODEL" ;;
  esac
  sed -E "s/^model: .*$/model: $m/" "$f" > "$DST/agents/$base"
done

python3 - "$DST" "$URL" <<'PY'
import json, os, sys
dst, url = sys.argv[1], sys.argv[2]
s = {
    "statusLine": {"type": "command",
                   "command": f"bash {dst}/pipeline/statusline-budget.sh"},
    "attribution": {"commit": "", "pr": ""},
    "env": {
        # KV cache 保护：attribution header 会让本地推理慢约 90%，必须在 settings 关
        "CLAUDE_CODE_ATTRIBUTION_HEADER": "0",
        # 预算门禁短路：本地模式配额不适用
        "PIPELINE_PROVIDER": "local",
        # 兜底：任何按层级请求的模型都映射到本地
        "ANTHROPIC_DEFAULT_OPUS_MODEL": os.environ["PIPELINE_LOCAL_MODEL"],
        "ANTHROPIC_DEFAULT_SONNET_MODEL": os.environ.get("PIPELINE_LOCAL_SMALL", os.environ["PIPELINE_LOCAL_MODEL"]),
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": os.environ.get("PIPELINE_LOCAL_SMALL", os.environ["PIPELINE_LOCAL_MODEL"]),
    },
}
json.dump(s, open(os.path.join(dst, "settings.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print(f"profile 已派生 → {dst}")
PY

echo "端点: $URL · 主模型: $MODEL · reviewer: $SMALL"
echo "提醒: 本地上下文 ≥64K（如 OLLAMA_CONTEXT_LENGTH=65536），否则长会话必碰壁"
[ "${PIPELINE_DRYRUN:-0}" = "1" ] && exit 0

exec env \
  CLAUDE_CONFIG_DIR="$DST" \
  ANTHROPIC_BASE_URL="$URL" \
  ANTHROPIC_AUTH_TOKEN="${ANTHROPIC_AUTH_TOKEN:-local}" \
  claude --agent architect --model "$MODEL" "$@"
