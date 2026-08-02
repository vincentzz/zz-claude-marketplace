# zz-claude-marketplace

Vincent's [Claude Code](https://code.claude.com) plugin marketplace.

## Plugins

| Plugin | Version | Description |
|---|---|---|
| [dev-pipeline](./dev-pipeline/) | 0.9.5 | A five-role software development pipeline: **architect / qa / dev** plus two read-only reviewers. Spec-driven, with mechanical acceptance (a single `acceptance.sh` exit code), review gates, and a clear accountability loop. Language-agnostic — build conventions are declared per project. |
| [dev-pipeline-cn](./dev-pipeline-cn/) | 0.9.5 | 中文版 of dev-pipeline — same pipeline with all agents, skills, and docs in Chinese. |
| [profile-switcher](./profile-switcher/) | 0.9.5 | Always-on utility. `/use-profile` binds or switches the project's profile plugin: enables exactly one, writes explicit `false` for siblings, pins the profile's entry agent as the project default. |

See [dev-pipeline/README.md](./dev-pipeline/README.md) for the full design, workflow, and tuning guide ([中文版](./dev-pipeline-cn/README.md)).

> Install **either** dev-pipeline **or** dev-pipeline-cn, not both — they define the same agent names (architect, qa, dev, …) and enabling both at once has undefined behavior.

## Requirements

- Claude Code **≥ 2.1.219**
- `git` and `python3` on your `PATH`

## Installation

One-liner:

```bash
curl -fsSL https://raw.githubusercontent.com/vincentzz/zz-claude-marketplace/main/install.sh | bash
```

Or manually:

```bash
claude plugin marketplace add vincentzz/zz-claude-marketplace
claude plugin install dev-pipeline@zz-claude-marketplace
```

Profile plugins ship with `defaultEnabled: false` — installing loads them without enabling them anywhere. Bind one per project with the switcher (the project must be a git repository):

```bash
cd <your-project>
claude                        # plain session; profile-switcher is always on
> /use-profile dev-pipeline   # enable + disable siblings + pin entry agent, all in .claude/settings.local.json
# exit, then:
claude                        # starts directly in architect (with its frontmatter model)
```

The restart is required: the `agent` settings key is read at startup only. After binding, switching profiles between projects is just `cd`. Manual alternative without the switcher: `claude plugin enable dev-pipeline@zz-claude-marketplace --scope local`, then add `"agent": "dev-pipeline:architect"` to the same `.claude/settings.local.json`.

On first run the architect detects an uninitialized project and walks through `/pipeline-init` — an idempotent setup that installs the protocol shim, interviews you about build conventions, and seeds the task registry. Re-running it on an initialized project is a no-op.

## Updating

Pull the latest version with a single command:

```bash
claude plugin marketplace update zz-claude-marketplace
```

or from within a Claude Code session:

```
/plugin marketplace update zz-claude-marketplace
```

This refetches the marketplace listing and updates installed plugins in one step. To apply the update in a running session, run `/reload-plugins`; otherwise the new version loads on the next startup.

You can also enable auto-update: `/plugin` → **Marketplaces** tab → select `zz-claude-marketplace` → **Enable auto-update** (third-party marketplaces have it disabled by default).

## Enabling / disabling

```bash
claude plugin enable dev-pipeline@zz-claude-marketplace --scope local    # or disable
```

or use the `/plugin` UI. `--scope local` writes the project's `.claude/settings.local.json` (the local layer overrides project and user layers), so the profile is bound to the project — switching profiles is just `cd`. Note that `enabledPlugins` entries fall through per plugin: a missing entry at one layer inherits from the layer below, so to force a plugin off in one project, write an explicit `false`. Convention: enable exactly one pipeline profile per project.

## Local development

Point Claude Code at your working copy — changes take effect without reinstalling:

```bash
claude plugin marketplace add /path/to/zz-claude-marketplace
```

## License

MIT
