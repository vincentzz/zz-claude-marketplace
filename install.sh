#!/usr/bin/env bash
# One-line install: curl -fsSL https://raw.githubusercontent.com/vincentzz/zz-claude-marketplace/main/install.sh | bash
set -euo pipefail
command -v claude >/dev/null || { echo "Install Claude Code first: https://code.claude.com"; exit 1; }
REPO="${PIPELINE_REPO:-vincentzz/zz-claude-marketplace}"
claude plugin marketplace add "$REPO"
claude plugin install dev-pipeline@zz-claude-marketplace
echo "Installed (not yet enabled — profile plugins enable per project). In each project root:"
echo "  claude plugin enable dev-pipeline@zz-claude-marketplace --scope local"
echo "  claude --agent architect --model fable"
echo "(architect initializes the project idempotently via /pipeline-init; upgrade: claude plugin marketplace update zz-claude-marketplace)"
