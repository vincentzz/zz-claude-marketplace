#!/usr/bin/env python3
"""taskctl — tasks/task.html 的唯一合法编辑器。

设计目标：机械可判定。任何 agent 对任务注册表的读写都必须经过本脚本，
使得"谁在什么时候把状态改成了什么"可以从 git log 与本脚本的契约中
机械地还原，失败责任可判定。

行契约（task.html 的 <tbody id="tasks"> 内，每个任务恰好一行）：

  <tr data-task-id="0001" data-test="done" data-dev="in-progress">...</tr>

解析只信任 data-* 属性与 <a> 的标题文本；写入时整行重新渲染。
手改行格式即违反契约，本脚本会以明确报错拒绝工作。

门禁（set 内建，--force 越过需在 notes 说明理由）：
  1. Test=done 之前 Dev 不得离开 not-started
  2. set <id> test|dev done 要求对应 reviewer 的评审闭环：
     最新 review-N.md 无 [BLOCKING]、含「结论：无阻塞项」结论行、N ≤ 2
     （同 review-check 子命令）

退出码：
  0  成功（verify 时表示验收全绿）
  2  用法错误 / 契约违反 / 前置条件不满足
  3  next 无可派发任务
  其余  verify 透传 acceptance.sh 的退出码
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
    """模板解析：项目内优先（可逐项目覆盖），skill 自带兜底（用户级安装的自播种源）。"""
    proj = os.path.join(root, "tasks", "specs", name) if name != "task.html" \
        else os.path.join(root, "tasks", name)
    if os.path.exists(proj):
        return proj
    bundled = os.path.normpath(os.path.join(TEMPLATES_DIR, name))
    if os.path.exists(bundled):
        return bundled
    die(f"模板缺失：项目内与 skill 自带目录均无 {name}")


def ensure_seeded(root: str):
    """tasks/task.html 缺失则自播种（用户级安装下项目零拷贝即可用）。"""
    dst = os.path.join(root, "tasks", "task.html")
    if not os.path.exists(dst):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        src = os.path.normpath(os.path.join(TEMPLATES_DIR, "task.html"))
        with open(src, encoding="utf-8") as f, open(dst, "w", encoding="utf-8") as g:
            g.write(f.read())
        print(f"taskctl: 已自播种 {dst}", file=sys.stderr)


def die(msg: str, code: int = 2):
    print(f"taskctl: {msg}", file=sys.stderr)
    sys.exit(code)


# harness 状态永不入团队库（个人工装契约）。位置不换目录，靠机制守护：
# 每次运行时确保 .git/info/exclude（个人、非共享）含以下排除项。
PERSONAL_EXCLUDES = ("tasks/", ".worktrees/", ".claude/", "CLAUDE.local.md")


def ensure_personal_exclude(root: str):
    """幂等地把 harness 排除项写入 .git/info/exclude。

    - 已被 git 跟踪的路径跳过（solo 仓库有意入库的场景不受干扰；
      对已跟踪文件 exclude 本就无效，跳过只为不误导）。
    - 任何失败静默降级为提示——本函数是防护网，不是功能依赖。
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
                    continue  # 完整入库（solo 模式），尊重现状
                # 部分跟踪（如团队提交了 .claude/settings.json）：仍写排除——
                # ignore 规则不影响已跟踪文件，只为遮蔽我们的个人增量
            added.append(entry)
        if added:
            with open(exclude_path, "a", encoding="utf-8") as f:
                if existing and not existing.endswith("\n"):
                    f.write("\n")
                f.write("# taskctl: harness 个人工装，永不提交\n")
                f.writelines(e + "\n" for e in added)
            print(f"taskctl: 已写入 .git/info/exclude 排除项: {' '.join(added)}", file=sys.stderr)
    except Exception as e:  # noqa: BLE001
        print(f"taskctl: 排除守护跳过（{e}）", file=sys.stderr)


def render_row(task_id: str, test: str, dev: str, title: str) -> str:
    return (
        f'<tr data-task-id="{task_id}" data-test="{test}" data-dev="{dev}">'
        f'<td class="id">{task_id}</td>'
        f'<td class="st {test}">{DISPLAY[test]}</td>'
        f'<td class="st {dev}">{DISPLAY[dev]}</td>'
        f'<td class="task"><a href="specs/{task_id}.html">{html.escape(title)}</a></td></tr>'
    )


class Registry:
    """task.html 的读-改-写。持文件锁，写入原子替换。"""

    def __init__(self, root: str):
        self.root = os.path.abspath(root)
        self.path = os.path.join(self.root, "tasks", "task.html")
        if not os.path.isfile(self.path):
            die(f"找不到 {self.path}（--root 指向项目根了吗？）")
        self.lock_path = self.path + ".lock"

    def __enter__(self):
        self._lock = open(self.lock_path, "w")
        fcntl.flock(self._lock, fcntl.LOCK_EX)
        with open(self.path, encoding="utf-8") as f:
            lines = f.read().splitlines(keepends=True)
        # 锚定契约：TBODY_OPEN 与 TBODY_CLOSE 必须各自独占一行（允许首尾空白）
        opens = [i for i, l in enumerate(lines) if l.strip() == TBODY_OPEN]
        closes = [i for i, l in enumerate(lines) if l.strip() == TBODY_CLOSE]
        if len(opens) != 1 or len(closes) != 1 or closes[0] < opens[0]:
            die(f"{self.path} 缺少独占一行的 {TBODY_OPEN} … {TBODY_CLOSE} 结构")
        self.head = "".join(lines[: opens[0]])
        self.tail = "".join(lines[closes[0] + 1 :])
        self.rows = []  # [(id, test, dev, title)]
        for line in lines[opens[0] + 1 : closes[0]]:
            line = line.strip()
            if not line:
                continue
            m = ROW_RE.match(line)
            if not m:
                die(f"行契约违反（请勿手改 task.html 的行）：{line[:120]}")
            self.rows.append((m.group(1), m.group(2), m.group(3), html.unescape(m.group(4))))
        ids = [r[0] for r in self.rows]
        if len(ids) != len(set(ids)):
            die("task.html 中存在重复 taskId")
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
        die(f"任务 {task_id} 不存在")


def cmd_list(reg: Registry, _args):
    for pos, (tid, test, dev, title) in enumerate(reg.rows, 1):
        print(f"{pos}\t{tid}\t{test}\t{dev}\t{title}")


def cmd_show(reg: Registry, args):
    i = reg.index_of(args.id)
    tid, test, dev, title = reg.rows[i]
    print(f"{i + 1}\t{tid}\t{test}\t{dev}\t{title}")


def cmd_next(reg: Registry, args):
    for tid, test, dev, _title in reg.rows:  # 行序即优先级，自上而下
        if args.stage == "test" and test == "not-started":
            print(tid)
            return
        if args.stage == "dev" and test == "done" and dev == "not-started":
            print(tid)
            return
    die(f"没有可派发的 {args.stage} 任务", 3)


MAX_REVIEW_ROUNDS = 2
REVIEWER_OF = {"test": "qa-reviewer", "dev": "dev-reviewer"}
CONCLUSION_RE = re.compile(r"^结论[：:]\s*无阻塞项")


def review_check(root: str, task_id: str, lane: str):
    """机械校验评审闭环。返回 (ok, 说明)。

    通过条件（对 tasks/specs/<id>/<reviewer>/ 下最新的 review-N.md）：
      1. 至少存在一份 review-N.md
      2. 最大轮数 N ≤ MAX_REVIEW_ROUNDS
      3. 最新一份内不含任何 [BLOCKING] 行
      4. 最新一份内存在以「结论：无阻塞项」起头的结论行
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
        return False, f"未找到 {reviewer} 的评审文件（{rdir}/review-N.md）"
    latest_n = max(rounds)
    if latest_n > MAX_REVIEW_ROUNDS:
        return False, f"评审轮数 {latest_n} 超过上限 {MAX_REVIEW_ROUNDS}（review-{latest_n}.md）"
    with open(rounds[latest_n], encoding="utf-8") as f:
        lines = f.read().splitlines()
    blocking = sum(1 for l in lines if l.lstrip().startswith("[BLOCKING]"))
    if blocking:
        return False, f"最新评审 review-{latest_n}.md 仍含 {blocking} 个 [BLOCKING] 项"
    if not any(CONCLUSION_RE.match(l.strip()) for l in lines):
        return False, f"最新评审 review-{latest_n}.md 缺少「结论：无阻塞项」结论行"
    return True, f"{reviewer} review-{latest_n}.md 闭环（无 [BLOCKING]，结论行合格）"


def cmd_review_check(root: str, args):
    ok, msg = review_check(root, args.id, args.lane)
    if not ok:
        die(f"评审未闭环：{msg}")
    print(f"OK {args.id} {msg}")


def cmd_set(reg: Registry, args):
    i = reg.index_of(args.id)
    tid, test, dev, title = reg.rows[i]
    if args.field == "dev" and args.status != "not-started" and test != "done" and not args.force:
        die(f"门禁：任务 {tid} 的 Test={test}，Test=done 之前不得推进 Dev（--force 可越过，需在 notes 说明理由）")
    if args.status == "done" and not args.force:
        ok, msg = review_check(reg.root, tid, args.field)
        if not ok:
            die(f"门禁：任务 {tid} 的 {args.field} 评审未闭环——{msg}（--force 可越过，需在 notes 说明理由）")
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
            die("--id 必须是 4 位数字")
        tid = args.id
    else:
        tid = f"{max((int(r[0]) for r in reg.rows), default=0) + 1:04d}"
    if any(r[0] == tid for r in reg.rows):
        die(f"任务 {tid} 已存在")
    spec_dir = os.path.join(reg.root, "tasks", "specs")
    spec_path = os.path.join(spec_dir, f"{tid}.html")
    if os.path.exists(spec_path):
        die(f"{spec_path} 已存在，拒绝覆盖")
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
        die(f"缺少 {script}（QA 尚未交付验收脚本）")
    checkout = os.path.abspath(args.checkout) if args.checkout else root
    proc = subprocess.run(["bash", script, checkout])
    sys.exit(proc.returncode)


def main():
    p = argparse.ArgumentParser(prog="taskctl", description=__doc__)
    p.add_argument("--root", default=".", help="项目根目录（含 tasks/task.html）")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="TSV: 优先级序号 id test dev 标题")

    sp = sub.add_parser("show", help="打印单个任务的 TSV 行")
    sp.add_argument("id")

    sp = sub.add_parser("next", help="打印可派发的最高优先级任务 id")
    sp.add_argument("stage", choices=["test", "dev"])

    sp = sub.add_parser("set", help="推进任务状态")
    sp.add_argument("id")
    sp.add_argument("field", choices=["test", "dev"])
    sp.add_argument("status", choices=list(STATUSES))
    sp.add_argument("--force", action="store_true")

    sp = sub.add_parser("add", help="注册新任务：建 spec、建资源目录、插入表格行")
    sp.add_argument("title")
    sp.add_argument("--id")
    g = sp.add_mutually_exclusive_group()
    g.add_argument("--top", action="store_true")
    g.add_argument("--after", metavar="ID")
    g.add_argument("--before", metavar="ID")

    sp = sub.add_parser("move", help="调整优先级（行序）")
    sp.add_argument("id")
    g = sp.add_mutually_exclusive_group(required=True)
    g.add_argument("--top", action="store_true")
    g.add_argument("--bottom", action="store_true")
    g.add_argument("--after", metavar="ID")
    g.add_argument("--before", metavar="ID")

    sp = sub.add_parser("retitle", help="修改任务标题")
    sp.add_argument("id")
    sp.add_argument("title")

    sp = sub.add_parser("verify", help="运行 acceptance.sh，退出码即判定")
    sp.add_argument("id")
    sp.add_argument("--checkout", help="被验收的检出目录，默认项目根（主检出）")

    sp = sub.add_parser("review-check", help="校验评审闭环：无 [BLOCKING]、结论行「无阻塞项」、轮数≤2")
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
