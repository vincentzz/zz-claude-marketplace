# zz-claude-marketplace

Vincent's [Claude Code](https://code.claude.com) plugin marketplace.

## Plugins

| Plugin | Version | Description |
|---|---|---|
| [dev-pipeline](./dev-pipeline/) | 0.9.5 | A five-role software development pipeline: **architect / qa / dev** plus two read-only reviewers. Spec-driven, with mechanical acceptance (a single `acceptance.sh` exit code), review gates, and a clear accountability loop. Language-agnostic — build conventions are declared per project. |
| [dev-pipeline-cn](./dev-pipeline-cn/) | 0.9.5 | 中文版 of dev-pipeline — same pipeline with all agents, skills, and docs in Chinese. |
| [trade-study](./trade-study/) | 0.1.0 | A three-role trade-study pipeline for decision-making: **analyst / scout / challenger**. Isolated per-candidate research with source provenance, ordinal-weighted criteria matrix, adversarial review, deliverables as HTML + PDF + PPTX. |
| [trade-study-cn](./trade-study-cn/) | 0.1.0 | 中文版 of trade-study — same pipeline with all agents, skills, and docs in Chinese. |
| [profile-switcher](./profile-switcher/) | 0.9.6 | Always-on utility. `/use-profile` binds, switches, or unbinds the project's profile plugin: enables exactly one (explicit `false` for siblings) and pins its entry agent as the project default; unbind returns the project to plain Claude. |
| [websearch-tool](./websearch-tool/) | 0.1.0 | Always-on utility. Web search and page fetch that keep working when the built-in `WebSearch`/`WebFetch` tools are gone — the normal case under a non-Anthropic provider. See [Web access without the built-in tools](#web-access-without-the-built-in-tools). |

See [dev-pipeline/README.md](./dev-pipeline/README.md) for the full design, workflow, and tuning guide ([中文版](./dev-pipeline-cn/README.md)), and [trade-study/README.md](./trade-study/README.md) for the trade-study design ([中文版](./trade-study-cn/README.md)).

> Within each EN/CN pair (dev-pipeline / dev-pipeline-cn, trade-study / trade-study-cn), enable only **one** per project — the pair defines the same agent names, and enabling both at once has undefined behavior. Different pipelines (a dev-pipeline and a trade-study) also stay one-per-project: profiles are for switching, not stacking.

## Web access without the built-in tools

Point a session at a non-Anthropic endpoint — `ollama launch claude` against a local model, an OpenAI-compatible proxy — and the built-in `WebSearch` and `WebFetch` tools stop existing. Profiles that depend on research (trade-study's scouts, most of all) then quietly answer from training data instead of from the web. **websearch-tool** closes that hole with one skill and one script: `web.py fetch <url>` and `web.py search "<query>"`.

Results always carry a `CHANNEL` tag, a retrieval date, and the path of a saved copy under `$TMPDIR/claude-web/`. The tag is the point — it tells a reader whether the evidence is mechanically reproducible or best-effort scraping to discount.

| Capability | Needs | Anthropic provider | Local / non-Anthropic provider |
|---|---|---|---|
| Built-in `WebSearch` / `WebFetch` | nothing | ✅ used first — this plugin never shadows them | ❌ tools absent |
| **Fetch a URL** (`curl`, `raw-api`) | nothing | ✅ | ✅ **works with zero setup** |
| ↳ JS-free rewrites: github.com → raw/API, npm/PyPI/crates → registry JSON, `/llms.txt` probe | nothing | ✅ | ✅ |
| **Search** (`ddgr-best-effort`) | `brew install ddgr` | ✅ | ✅ once ddgr is installed |
| **Render a JS page** (`rendered`) | Node + `playwright` + a browser download | ✅ | ✅ once installed |

Honest limits:

- **Search needs `ddgr`.** Without it the script does not improvise and does not fall back to Google — it emits `NO-BACKEND` naming both paths that still work (give it a specific URL, or install ddgr). Fetch, the tier most work actually needs, requires nothing at all.
- **`ddgr` is best-effort scraping.** It parses DuckDuckGo's HTML, so it is subject to upstream markup changes and to throttling; it can break without notice. Treat titles and abstracts as hints and fetch the URL before citing anything. An empty result is reported as `EMPTY-OR-THROTTLED`, never as "no results found" — those mean opposite things, and the distinction is the reader's to make.
- **Rendering needs Node.** Tier 4 fires only on detection (a page that proves to be a JavaScript shell), never on prediction. With no browser available it stops at `RENDER_REQUIRED` and says the page was not retrieved, rather than letting the model fill in content it never saw.
- **No API keys, anywhere.** Not for search, not for fetch. GitHub API calls are unauthenticated and share the anonymous rate limit.

## Requirements

- Claude Code **≥ 2.1.219**
- `git` and `python3` on your `PATH`
- optional, for websearch-tool: `ddgr` (search) and Node + `playwright` (rendering JS-only pages)

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
