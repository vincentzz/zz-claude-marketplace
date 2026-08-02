---
name: task-registry
description: 任务总表 tasks/task.html 的读写命令参考（taskctl）。查询任务、派发选取、推进状态、注册新任务、调整优先级、机械验收时使用。
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/taskctl.py *)
---

# 任务注册表（taskctl）

`tasks/task.html` 是任务状态唯一真源，**只能**经 taskctl 读写。行序即优先级。手改表格行会被 taskctl 以契约违反拒绝服务。

统一调用形式（绝对路径，与 cwd 无关）：

```
python3 ${CLAUDE_SKILL_DIR}/scripts/taskctl.py --root ${CLAUDE_PROJECT_DIR} <子命令>
```

## 子命令

| 命令 | 作用 | 输出 / 退出码 |
|---|---|---|
| `list` | 全表 | TSV：`优先级序号 id test dev 标题` |
| `show <id>` | 单行 | 同上 |
| `next test` | 最高优先级、Test=not-started 的任务 | 打印 id；无则 exit 3 |
| `next dev` | 最高优先级、Test=done 且 Dev=not-started 的任务 | 打印 id；无则 exit 3 |
| `set <id> test\|dev <status>` | 推进状态（status ∈ not-started/in-progress/done） | 门禁①：Test=done 之前 Dev 不得离开 not-started；门禁②：推进到 done 需对应评审闭环（同 review-check） |
| `review-check <id> test\|dev` | 校验评审闭环：最新 review-N.md 无 [BLOCKING]、含「结论：无阻塞项」结论行、轮数 ≤2 | exit 0 通过；2 未闭环（stderr 给出原因） |
| `add "<标题>" [--id NNNN] [--top\|--after ID\|--before ID]` | 注册：从 `_template.html` 建 spec、建 `specs/<id>/`、插行（默认队尾） | 打印新 id |
| `move <id> --top\|--bottom\|--after ID\|--before ID` | 调优先级 | |
| `retitle <id> "<标题>"` | 改标题 | |
| `verify <id> [--checkout DIR]` | 运行 `tasks/specs/<id>/acceptance.sh`，默认对主检出验收 | **退出码即判定**：0 ⟺ 全部 AC 通过 |

## 排除自守护

taskctl 每次运行会幂等地把 `tasks/`、`.worktrees/`、`.claude/`、`CLAUDE.md` 写入 `.git/info/exclude`（已被 git 跟踪的路径跳过）——harness 状态永不入团队库是机械不变量，不依赖任何人记得安装步骤。

## 纪律

- 状态推进只由 architect 执行；`set` 之后随手 `git add tasks && git commit -m "tasks: …"`。
- `--force` 只用于仲裁后的特批，且必须同时在该任务的 architect notes 里写明理由。
- 退出码 2 = 用法或契约违反（读 stderr 的中文报错），3 = `next` 无可派发。脚本报错说明世界与契约不一致——先修世界或找 architect，不要绕过脚本。
