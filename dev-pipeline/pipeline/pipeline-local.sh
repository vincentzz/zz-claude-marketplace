#!/usr/bin/env bash
# Local fallback-mode launcher: when the subscription quota runs out, switch the whole pipeline to a local LLM.
#   Usage:    PIPELINE_LOCAL_MODEL=qwen3-coder:30b bash ~/.claude/pipeline/pipeline-local.sh [extra claude args]
#   Optional: PIPELINE_LOCAL_URL   local Anthropic-compatible endpoint (default http://localhost:11434, Ollama >=0.14)
#             PIPELINE_LOCAL_SMALL small model for the two reviewers (defaults to the main model)
#             PIPELINE_DRYRUN=1    only generate the profile, do not launch (for testing)
# Note:  CLAUDE_CODE_SUBAGENT_MODEL(_FORCE) is deliberately unused: it is one model for every subagent,
#        which would flatten the reviewers' small-model distinction -- and without _FORCE it loses to
#        the frontmatter on Claude Code >= 2.1.251 anyway. Rewriting the frontmatter is version-proof.
# How:   mechanically derive ~/.claude-pipeline-local from ~/.claude (the agents' model lines are replaced
#        with the local model, skills/pipeline are copied verbatim, settings get the local essentials
#        injected), then launch through CLAUDE_CONFIG_DIR. The derived profile is regenerated every run --
#        no hand maintenance, zero contamination of the main profile.
set -euo pipefail

SRC="${CLAUDE_USER_DIR:-$HOME/.claude}"
DST="${SRC}-pipeline-local"
MODEL="${PIPELINE_LOCAL_MODEL:?PIPELINE_LOCAL_MODEL is required (e.g. qwen3-coder:30b)}"
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
        # KV cache protection: the attribution header slows local inference by ~90%, must be off in settings
        "CLAUDE_CODE_ATTRIBUTION_HEADER": "0",
        # Short-circuit the budget gate: quotas do not apply in local mode
        "PIPELINE_PROVIDER": "local",
        # Catch-all: map every tier-requested model to the local one
        "ANTHROPIC_DEFAULT_FABLE_MODEL": os.environ["PIPELINE_LOCAL_MODEL"],
        "ANTHROPIC_DEFAULT_OPUS_MODEL": os.environ["PIPELINE_LOCAL_MODEL"],
        "ANTHROPIC_DEFAULT_SONNET_MODEL": os.environ.get("PIPELINE_LOCAL_SMALL", os.environ["PIPELINE_LOCAL_MODEL"]),
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": os.environ.get("PIPELINE_LOCAL_SMALL", os.environ["PIPELINE_LOCAL_MODEL"]),
    },
}
json.dump(s, open(os.path.join(dst, "settings.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print(f"profile derived → {dst}")
PY

echo "endpoint: $URL · main model: $MODEL · reviewer: $SMALL"
echo "reminder: give the local model a context of >=64K (e.g. OLLAMA_CONTEXT_LENGTH=65536), or long sessions will hit the wall"
[ "${PIPELINE_DRYRUN:-0}" = "1" ] && exit 0

exec env \
  CLAUDE_CONFIG_DIR="$DST" \
  ANTHROPIC_BASE_URL="$URL" \
  ANTHROPIC_AUTH_TOKEN="${ANTHROPIC_AUTH_TOKEN:-local}" \
  claude --agent architect --model "$MODEL" "$@"
