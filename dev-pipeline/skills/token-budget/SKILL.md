---
name: token-budget
description: 派发子代理前的 token 预算门禁。architect 每次唤起 qa/dev 之前、或用户询问额度余量时使用。
allowed-tools: Bash(bash ${CLAUDE_SKILL_DIR}/scripts/check-token-budget.sh *)
---

# Token 预算门禁

数据来源：`.claude/pipeline/statusline-budget.sh`（statusline 每次刷新把订阅额度 5h/7d 余量、重置时间与上下文余量写入 `.claude/pipeline/budget.json`）。门禁读该文件机械判定，不做任何估算。

检查命令（每次派发前必跑）：

```
bash ${CLAUDE_SKILL_DIR}/scripts/check-token-budget.sh ${CLAUDE_PROJECT_DIR}
```

## 判定与动作

| 退出码 | 含义 | architect 的动作 |
|---|---|---|
| 0 `OK` | 额度余量（5h 与 7d 取小）≥ 阈值，且上下文余量 ≥ 阈值 | 正常派发 |
| 1 `LOW` | 任一余量低于阈值 | **停止派发新任务**；向用户播报余量与重置时间；在跑的子代理任其收尾；然后给用户两个选项——等重置，或**切本地降级模式**（退出本会话，`PIPELINE_LOCAL_MODEL=<模型> bash ~/.claude/pipeline/pipeline-local.sh`；tasks/ 与 git 里状态齐全，重启无损，in-progress 任务重派即续）|
| 2 `UNKNOWN` | budget.json 缺失/过期（statusline 未装、会话刚启动、API 计费账号） | 提醒用户一次（指向 README 的 statusline 配置）；降级为同一时刻至多 1 个子代理继续 |

阈值经环境变量调整：`PIPELINE_MIN_QUOTA_PCT`（默认 20）、`PIPELINE_MIN_CONTEXT_PCT`（默认 15）、`PIPELINE_BUDGET_MAX_AGE`（默认 900 秒）。

上下文余量指 architect 主会话自身——它同样是稀缺资源：LOW 若由上下文触发，先让在跑任务收尾、汇总必要状态，再建议用户开新会话续跑（任务状态都在 `tasks/` 里，续跑无损）。
