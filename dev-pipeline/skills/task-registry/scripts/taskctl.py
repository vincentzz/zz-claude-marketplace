#!/usr/bin/env python3
"""taskctl — the sole legal editor of tasks/task.html.

Design goal: mechanically decidable. Every agent read or write against the task
registry must go through this script, so that "who changed which status to what,
and when" can be reconstructed mechanically from git log plus this script's
contract, and failure accountability stays decidable.

Row contract (inside task.html's <tbody id="tasks">, exactly one row per task):

  <tr data-task-id="0001" data-test="done" data-dev="in-progress">...</tr>

Parsing trusts only the data-* attributes and the <a> title text; a write
re-renders the whole row. Hand-editing a row's format violates the contract and
this script refuses to work, with an explicit error.

Gates (built into set; --force to bypass, with the reason recorded in notes):
  1. Dev must not leave not-started before Test=done
  2. set <id> test|dev done requires review closure from the matching reviewer:
     the latest review-N.md has no [BLOCKING], carries a
     "Conclusion: no blocking items" conclusion line, and N <= 2
     (same as the review-check subcommand)

Exit codes:
  0  success (for verify: acceptance is all green)
  2  usage error / contract violation / precondition not met
  3  next has no dispatchable task
  other  verify passes through acceptance.sh's exit code
"""

import argparse
import datetime
import fcntl
import html
import os
import re
import subprocess
import sys

STATUSES = ("not-started", "in-progress", "done")
DISPLAY = {"not-started": "Not Started", "in-progress": "In-Progress", "done": "Done"}
TBODY_OPEN = '<tbody id="tasks">'
TBODY_CLOSE = "</tbody>"

ROW_RE = re.compile(
    r'^<tr data-task-id="(\d{4})" data-test="(not-started|in-progress|done)"'
    r' data-dev="(not-started|in-progress|done)">'
    r'<td class="id">\1</td>'
    r'<td class="st \2">[^<]*</td>'
    r'<td class="st \3">[^<]*</td>'
    r'<td class="task"><a href="specs/\1\.html">(.*)</a></td></tr>$'
)


TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "templates")


def resolve_template(root: str, name: str) -> str:
    """Template resolution: in-project first (per-project override), skill-bundled as fallback (the self-seeding source for user-level installs)."""
    proj = os.path.join(root, "tasks", "specs", name) if name != "task.html" \
        else os.path.join(root, "tasks", name)
    if os.path.exists(proj):
        return proj
    bundled = os.path.normpath(os.path.join(TEMPLATES_DIR, name))
    if os.path.exists(bundled):
        return bundled
    die(f"template missing: neither the project nor the skill's bundled directory has {name}")


def ensure_seeded(root: str):
    """Self-seed tasks/task.html when missing (so a user-level install works with zero copies into the project)."""
    dst = os.path.join(root, "tasks", "task.html")
    if not os.path.exists(dst):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        src = os.path.normpath(os.path.join(TEMPLATES_DIR, "task.html"))
        with open(src, encoding="utf-8") as f, open(dst, "w", encoding="utf-8") as g:
            g.write(f.read())
        print(f"taskctl: self-seeded {dst}", file=sys.stderr)


def die(msg: str, code: int = 2):
    print(f"taskctl: {msg}", file=sys.stderr)
    sys.exit(code)


# harness state never enters the team repo (personal-tooling contract). The location
# stays where it is, guarded by mechanism: every run ensures .git/info/exclude
# (personal, non-shared) contains the excludes below.
PERSONAL_EXCLUDES = ("tasks/", ".worktrees/", ".claude/", "CLAUDE.local.md")


def ensure_personal_exclude(root: str):
    """Idempotently write the harness excludes into .git/info/exclude.

    - Paths already tracked by git are skipped (a solo repo that deliberately
      commits them is left undisturbed; exclude is a no-op for tracked files
      anyway, so skipping merely avoids misleading output).
    - Any failure degrades silently into a notice — this function is a safety
      net, not a functional dependency.
    """
    try:
        git_info = os.path.join(root, ".git", "info")
        if not os.path.isdir(os.path.join(root, ".git")):
            return
        os.makedirs(git_info, exist_ok=True)
        exclude_path = os.path.join(git_info, "exclude")
        existing = ""
        if os.path.exists(exclude_path):
            with open(exclude_path, encoding="utf-8") as f:
                existing = f.read()
        lines = {l.strip() for l in existing.splitlines()}
        added = []
        for entry in PERSONAL_EXCLUDES:
            if entry in lines:
                continue
            tracked = subprocess.run(
                ["git", "-C", root, "ls-files", "--", entry.rstrip("/")],
                capture_output=True, text=True,
            )
            if tracked.returncode == 0 and tracked.stdout.strip():
                others = subprocess.run(
                    ["git", "-C", root, "ls-files", "--others", "--exclude-standard",
                     "--", entry.rstrip("/")],
                    capture_output=True, text=True,
                )
                if not others.stdout.strip():
                    continue  # fully committed (solo mode), respect the status quo
                # partially tracked (e.g. the team committed .claude/settings.json): still
                # write the exclude — ignore rules do not affect tracked files, this only
                # masks our personal additions
            added.append(entry)
        if added:
            with open(exclude_path, "a", encoding="utf-8") as f:
                if existing and not existing.endswith("\n"):
                    f.write("\n")
                f.write("# taskctl: harness personal tooling, never committed\n")
                f.writelines(e + "\n" for e in added)
            print(f"taskctl: wrote excludes into .git/info/exclude: {' '.join(added)}", file=sys.stderr)
    except Exception as e:  # noqa: BLE001
        print(f"taskctl: exclude guard skipped ({e})", file=sys.stderr)


def render_row(task_id: str, test: str, dev: str, title: str) -> str:
    return (
        f'<tr data-task-id="{task_id}" data-test="{test}" data-dev="{dev}">'
        f'<td class="id">{task_id}</td>'
        f'<td class="st {test}">{DISPLAY[test]}</td>'
        f'<td class="st {dev}">{DISPLAY[dev]}</td>'
        f'<td class="task"><a href="specs/{task_id}.html">{html.escape(title)}</a></td></tr>'
    )


class Registry:
    """Read-modify-write of task.html. Holds a file lock; writes replace atomically."""

    def __init__(self, root: str):
        self.root = os.path.abspath(root)
        self.path = os.path.join(self.root, "tasks", "task.html")
        if not os.path.isfile(self.path):
            die(f"{self.path} not found (does --root point at the project root?)")
        self.lock_path = self.path + ".lock"

    def __enter__(self):
        self._lock = open(self.lock_path, "w")
        fcntl.flock(self._lock, fcntl.LOCK_EX)
        with open(self.path, encoding="utf-8") as f:
            lines = f.read().splitlines(keepends=True)
        # Anchor contract: TBODY_OPEN and TBODY_CLOSE must each occupy a line of their own (surrounding whitespace allowed)
        opens = [i for i, l in enumerate(lines) if l.strip() == TBODY_OPEN]
        closes = [i for i, l in enumerate(lines) if l.strip() == TBODY_CLOSE]
        if len(opens) != 1 or len(closes) != 1 or closes[0] < opens[0]:
            die(f"{self.path} lacks a {TBODY_OPEN} … {TBODY_CLOSE} structure on lines of their own")
        self.head = "".join(lines[: opens[0]])
        self.tail = "".join(lines[closes[0] + 1 :])
        self.rows = []  # [(id, test, dev, title)]
        for line in lines[opens[0] + 1 : closes[0]]:
            line = line.strip()
            if not line:
                continue
            m = ROW_RE.match(line)
            if not m:
                die(f"row contract violated (do not hand-edit task.html rows): {line[:120]}")
            self.rows.append((m.group(1), m.group(2), m.group(3), html.unescape(m.group(4))))
        ids = [r[0] for r in self.rows]
        if len(ids) != len(set(ids)):
            die("duplicate taskId in task.html")
        return self

    def __exit__(self, exc_type, exc, tb):
        fcntl.flock(self._lock, fcntl.LOCK_UN)
        self._lock.close()
        return False

    def write(self):
        body = "".join(render_row(*r) + "\n" for r in self.rows)
        text = self.head + TBODY_OPEN + "\n" + body + TBODY_CLOSE + "\n" + self.tail
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, self.path)

    def index_of(self, task_id: str) -> int:
        for i, r in enumerate(self.rows):
            if r[0] == task_id:
                return i
        die(f"task {task_id} does not exist")


def cmd_list(reg: Registry, _args):
    for pos, (tid, test, dev, title) in enumerate(reg.rows, 1):
        print(f"{pos}\t{tid}\t{test}\t{dev}\t{title}")


def cmd_show(reg: Registry, args):
    i = reg.index_of(args.id)
    tid, test, dev, title = reg.rows[i]
    print(f"{i + 1}\t{tid}\t{test}\t{dev}\t{title}")


def cmd_next(reg: Registry, args):
    for tid, test, dev, _title in reg.rows:  # row order is priority, top to bottom
        if args.stage == "test" and test == "not-started":
            print(tid)
            return
        if args.stage == "dev" and test == "done" and dev == "not-started":
            print(tid)
            return
    die(f"no dispatchable {args.stage} task", 3)


MAX_REVIEW_ROUNDS = 2
REVIEWER_OF = {"test": "qa-reviewer", "dev": "dev-reviewer"}
CONCLUSION_RE = re.compile(r"^Conclusion:\s*no blocking items")


def review_check(root: str, task_id: str, lane: str):
    """Mechanically verify review closure. Returns (ok, explanation).

    Pass conditions (against the latest review-N.md under tasks/specs/<id>/<reviewer>/):
      1. at least one review-N.md exists
      2. the highest round N <= MAX_REVIEW_ROUNDS
      3. the latest one contains no [BLOCKING] line
      4. the latest one carries a conclusion line starting with "Conclusion: no blocking items"
    """
    reviewer = REVIEWER_OF[lane]
    rdir = os.path.join(os.path.abspath(root), "tasks", "specs", task_id, reviewer)
    rounds = {}
    if os.path.isdir(rdir):
        for name in os.listdir(rdir):
            m = re.fullmatch(r"review-(\d+)\.md", name)
            if m:
                rounds[int(m.group(1))] = os.path.join(rdir, name)
    if not rounds:
        return False, f"no review file found for {reviewer} ({rdir}/review-N.md)"
    latest_n = max(rounds)
    if latest_n > MAX_REVIEW_ROUNDS:
        return False, f"review round {latest_n} exceeds the limit of {MAX_REVIEW_ROUNDS} (review-{latest_n}.md)"
    with open(rounds[latest_n], encoding="utf-8") as f:
        lines = f.read().splitlines()
    blocking = sum(1 for l in lines if l.lstrip().startswith("[BLOCKING]"))
    if blocking:
        return False, f"the latest review review-{latest_n}.md still carries {blocking} [BLOCKING] item(s)"
    if not any(CONCLUSION_RE.match(l.strip()) for l in lines):
        return False, f"the latest review review-{latest_n}.md lacks a \"Conclusion: no blocking items\" conclusion line"
    return True, f"{reviewer} review-{latest_n}.md closed (no [BLOCKING], conclusion line valid)"


def cmd_review_check(root: str, args):
    ok, msg = review_check(root, args.id, args.lane)
    if not ok:
        die(f"review not closed: {msg}")
    print(f"OK {args.id} {msg}")


def cmd_set(reg: Registry, args):
    i = reg.index_of(args.id)
    tid, test, dev, title = reg.rows[i]
    if args.field == "dev" and args.status != "not-started" and test != "done" and not args.force:
        die(f"gate: task {tid} has Test={test}; Dev must not advance before Test=done (--force bypasses, state the reason in notes)")
    if args.status == "done" and not args.force:
        ok, msg = review_check(reg.root, tid, args.field)
        if not ok:
            die(f"gate: the {args.field} review of task {tid} is not closed — {msg} (--force bypasses, state the reason in notes)")
    if args.field == "test":
        test = args.status
    else:
        dev = args.status
    reg.rows[i] = (tid, test, dev, title)
    reg.write()
    print(f"{tid}\t{args.field}\t{args.status}")


def _insert_at(reg: Registry, row, args):
    if args.top:
        reg.rows.insert(0, row)
    elif args.after:
        reg.rows.insert(reg.index_of(args.after) + 1, row)
    elif args.before:
        reg.rows.insert(reg.index_of(args.before), row)
    else:
        reg.rows.append(row)


def cmd_add(reg: Registry, args):
    if args.id:
        if not re.fullmatch(r"\d{4}", args.id):
            die("--id must be 4 digits")
        tid = args.id
    else:
        tid = f"{max((int(r[0]) for r in reg.rows), default=0) + 1:04d}"
    if any(r[0] == tid for r in reg.rows):
        die(f"task {tid} already exists")
    spec_dir = os.path.join(reg.root, "tasks", "specs")
    spec_path = os.path.join(spec_dir, f"{tid}.html")
    if os.path.exists(spec_path):
        die(f"{spec_path} already exists, refusing to overwrite")
    template_path = resolve_template(reg.root, "_template.html")
    with open(template_path, encoding="utf-8") as f:
        spec = f.read()
    spec = (
        spec.replace("{{TASK_ID}}", tid)
        .replace("{{TITLE}}", html.escape(args.title))
        .replace("{{DATE}}", datetime.date.today().isoformat())
    )
    os.makedirs(os.path.join(spec_dir, tid), exist_ok=True)
    with open(spec_path, "w", encoding="utf-8") as f:
        f.write(spec)
    _insert_at(reg, (tid, "not-started", "not-started", args.title), args)
    reg.write()
    print(tid)


def cmd_move(reg: Registry, args):
    i = reg.index_of(args.id)
    row = reg.rows.pop(i)
    if args.bottom:
        reg.rows.append(row)
    else:
        _insert_at(reg, row, args)
    reg.write()
    print(args.id)


def cmd_retitle(reg: Registry, args):
    i = reg.index_of(args.id)
    tid, test, dev, _ = reg.rows[i]
    reg.rows[i] = (tid, test, dev, args.title)
    reg.write()
    print(tid)


def cmd_verify(root: str, args):
    root = os.path.abspath(root)
    script = os.path.join(root, "tasks", "specs", args.id, "acceptance.sh")
    if not os.path.isfile(script):
        die(f"{script} missing (QA has not delivered the acceptance script yet)")
    checkout = os.path.abspath(args.checkout) if args.checkout else root
    proc = subprocess.run(["bash", script, checkout])
    sys.exit(proc.returncode)


def main():
    p = argparse.ArgumentParser(prog="taskctl", description=__doc__)
    p.add_argument("--root", default=".", help="project root (the one holding tasks/task.html)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="TSV: priority index, id, test, dev, title")

    sp = sub.add_parser("show", help="print a single task's TSV row")
    sp.add_argument("id")

    sp = sub.add_parser("next", help="print the id of the highest-priority dispatchable task")
    sp.add_argument("stage", choices=["test", "dev"])

    sp = sub.add_parser("set", help="advance a task's status")
    sp.add_argument("id")
    sp.add_argument("field", choices=["test", "dev"])
    sp.add_argument("status", choices=list(STATUSES))
    sp.add_argument("--force", action="store_true")

    sp = sub.add_parser("add", help="register a new task: create the spec, the resource directory, and the table row")
    sp.add_argument("title")
    sp.add_argument("--id")
    g = sp.add_mutually_exclusive_group()
    g.add_argument("--top", action="store_true")
    g.add_argument("--after", metavar="ID")
    g.add_argument("--before", metavar="ID")

    sp = sub.add_parser("move", help="adjust priority (row order)")
    sp.add_argument("id")
    g = sp.add_mutually_exclusive_group(required=True)
    g.add_argument("--top", action="store_true")
    g.add_argument("--bottom", action="store_true")
    g.add_argument("--after", metavar="ID")
    g.add_argument("--before", metavar="ID")

    sp = sub.add_parser("retitle", help="change a task's title")
    sp.add_argument("id")
    sp.add_argument("title")

    sp = sub.add_parser("verify", help="run acceptance.sh; its exit code is the verdict")
    sp.add_argument("id")
    sp.add_argument("--checkout", help="the checkout directory under acceptance, defaults to the project root (main checkout)")

    sp = sub.add_parser("review-check", help="verify review closure: no [BLOCKING], a \"no blocking items\" conclusion line, rounds <= 2")
    sp.add_argument("id")
    sp.add_argument("lane", choices=["test", "dev"])

    args = p.parse_args()
    ensure_personal_exclude(os.path.abspath(args.root))
    ensure_seeded(os.path.abspath(args.root))
    if args.cmd == "verify":
        cmd_verify(args.root, args)
        return
    if args.cmd == "review-check":
        cmd_review_check(args.root, args)
        return
    with Registry(args.root) as reg:
        {
            "list": cmd_list,
            "show": cmd_show,
            "next": cmd_next,
            "set": cmd_set,
            "add": cmd_add,
            "move": cmd_move,
            "retitle": cmd_retitle,
        }[args.cmd](reg, args)


if __name__ == "__main__":
    main()
