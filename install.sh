#!/usr/bin/env bash
# One-line install: curl -fsSL https://raw.githubusercontent.com/vincentzz/zz-claude-marketplace/main/install.sh | bash
set -euo pipefail
command -v claude >/dev/null || { echo "Install Claude Code first: https://code.claude.com"; exit 1; }
REPO="${PIPELINE_REPO:-vincentzz/zz-claude-marketplace}"
claude plugin marketplace add "$REPO"
claude plugin install dev-pipeline@zz-claude-marketplace
claude plugin install profile-switcher@zz-claude-marketplace
echo "Installed. Profile plugins stay disabled until bound to a project. In each project root:"
echo "  claude                     # plain session"
echo "  > /use-profile dev-pipeline   # writes .claude/settings.local.json (enable + entry agent)"
echo "  # exit, then: claude       # starts directly in architect"
echo "(architect initializes the project idempotently via /pipeline-init; upgrade: claude plugin marketplace update zz-claude-marketplace)"
