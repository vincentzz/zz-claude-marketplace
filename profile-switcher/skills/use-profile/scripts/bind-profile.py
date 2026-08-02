#!/usr/bin/env python3
"""Bind a profile plugin to the current project's .claude/settings.local.json.

Merges (never clobbers) the existing file: sets enabledPlugins[<enable>]=true,
writes explicit false for every other known profile plugin, and pins the
project's default agent. Idempotent — re-run to switch profiles.
"""
import argparse
import json
import pathlib
import sys

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--project", default=".", help="project root (default: cwd)")
ap.add_argument("--enable", required=True, metavar="PLUGIN@MARKETPLACE")
ap.add_argument("--agent", required=True, metavar="PLUGIN:AGENT",
                help="entry agent, plugin-prefixed")
ap.add_argument("--disable", action="append", default=[], metavar="PLUGIN@MARKETPLACE",
                help="other profile plugins to explicitly disable (repeatable)")
ap.add_argument("--model", help="settings-level model override; note that an "
                "entry agent with a frontmatter model ignores this")
args = ap.parse_args()

path = pathlib.Path(args.project) / ".claude" / "settings.local.json"
path.parent.mkdir(exist_ok=True)

cfg = {}
if path.exists():
    try:
        cfg = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        sys.exit(f"refusing to touch unparseable {path}: {e}")

enabled = cfg.setdefault("enabledPlugins", {})
enabled[args.enable] = True
for other in args.disable:
    if other != args.enable:
        enabled[other] = False
cfg["agent"] = args.agent
if args.model:
    cfg["model"] = args.model

path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")
print(f"wrote {path}")
print(f"  enabled : {args.enable}")
for other in args.disable:
    if other != args.enable:
        print(f"  disabled: {other}")
print(f"  agent   : {args.agent}")
if args.model:
    print(f"  model   : {args.model} (an entry-agent frontmatter model overrides this)")
print("Restart to take effect: exit this session and run `claude`.")
