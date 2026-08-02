---
name: use-profile
description: Bind or switch the profile plugin for the current project — enable exactly one profile, write its entry agent as the project's default agent, then have the user restart into it. Use when the user says "use profile X", "switch profile", "切换 profile", "bind this project to X", "enable the pipeline here", or asks why bare `claude` doesn't start in a profile's agent.
---

# use-profile · bind one profile plugin to this project

Profile plugins (dev-pipeline, ppt decks, 3D modeling, …) ship `defaultEnabled: false` and are meant to be enabled **one per project**. This skill does the whole binding in one pass: pick a profile → write `.claude/settings.local.json` (enable it, explicitly disable sibling profiles, pin its entry agent) → tell the user to restart. The `agent` settings key is read only at startup, so the restart is irreducible — never promise a live switch.

## Steps

1. **Discover installed profiles**: run `claude plugin list --json`. For each installed plugin, find its manifest in the version cache (`ls ~/.claude/plugins/cache/<marketplace>/<plugin>/*/.claude-plugin/plugin.json`, take the newest version dir) and read it. A **profile plugin** is one whose manifest carries an `entryAgent` field. Collect: name, marketplace, entryAgent, current enabled state.
2. **Pick the target**: if the user already named one, match it (fuzzy on plugin name). Otherwise AskUserQuestion with the discovered profiles as options (mark the currently enabled one). If no profile plugins are installed, say so and point to `claude plugin install <name>@<marketplace>`.
3. **Bind** — run the deterministic writer (never hand-edit the JSON):

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/use-profile/scripts/bind-profile.py" \
     --enable <plugin>@<marketplace> \
     --agent <plugin>:<entryAgent> \
     --disable <other-profile>@<marketplace> [--disable …]
   ```

   Pass `--disable` for **every other** discovered profile plugin — explicit `false` entries shield the project from stray user-level `true`s (enabledPlugins entries fall through per plugin when absent). Non-profile plugins (no `entryAgent`) are none of this skill's business: never disable them.
4. **Model**: the entry agent's frontmatter model applies automatically; do not write a `model` key unless the user explicitly asks, and if they do, warn that a frontmatter model on the entry agent takes precedence (only `claude --model` truly overrides).
5. **Close**: report what was written and tell the user: exit this session and run bare `claude` from the project root — it will start directly in the profile's entry agent. Re-running this skill later switches profiles the same way.

## Boundaries

- Writes only the project's `.claude/settings.local.json` (personal layer, auto-gitignored). Never touch `~/.claude/settings.json`, project `.claude/settings.json`, or any file outside the project.
- One profile per project is the invariant this skill exists to keep — never enable two profiles at once, even if asked casually; explain the same-agent-name collision instead and let the user insist explicitly before deviating.
