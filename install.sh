#!/usr/bin/env bash
# One-line install: curl -fsSL https://raw.githubusercontent.com/vincentzz/zz-claude-marketplace/main/install.sh | bash
set -euo pipefail
command -v claude >/dev/null || { echo "Install Claude Code first: https://code.claude.com"; exit 1; }
command -v python3 >/dev/null || { echo "python3 is required"; exit 1; }
REPO="${PIPELINE_REPO:-vincentzz/zz-claude-marketplace}"

# Read the marketplace manifest (local checkout or GitHub repo) to install every plugin it lists.
if [ -d "$REPO" ]; then
  MANIFEST=$(cat "$REPO/.claude-plugin/marketplace.json")
else
  MANIFEST=$(curl -fsSL "https://raw.githubusercontent.com/$REPO/main/.claude-plugin/marketplace.json")
fi
MARKET=$(printf '%s' "$MANIFEST" | python3 -c "import json,sys; print(json.load(sys.stdin)['name'])")
PLUGINS=$(printf '%s' "$MANIFEST" | python3 -c "import json,sys; [print(p['name']) for p in json.load(sys.stdin)['plugins']]")

claude plugin marketplace add "$REPO"
for p in $PLUGINS; do
  claude plugin install "$p@$MARKET"
done

echo "Installed: $(echo $PLUGINS) (profile plugins stay disabled until bound to a project). In each project root:"
echo "  claude                        # plain session"
echo "  > /use-profile dev-pipeline   # or dev-pipeline-cn; writes .claude/settings.local.json"
echo "  # exit, then: claude          # starts directly in the profile's entry agent"
echo "(upgrade everything: claude plugin marketplace update $MARKET)"
