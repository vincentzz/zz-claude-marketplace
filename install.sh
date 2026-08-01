#!/usr/bin/env bash
# 一行安装：curl -fsSL https://raw.githubusercontent.com/vincentzz/zz-claude-marketplace/main/install.sh | bash
set -euo pipefail
command -v claude >/dev/null || { echo "先安装 Claude Code：https://code.claude.com"; exit 1; }
REPO="${PIPELINE_REPO:-vincentzz/zz-claude-marketplace}"
claude plugin marketplace add "$REPO"
claude plugin install dev-pipeline@zz-claude-marketplace
echo "完成。任意项目根运行: claude --agent architect --model fable"
echo "（architect 会经 /pipeline-init 幂等初始化该项目；升级: claude plugin marketplace update zz-claude-marketplace）"
