---
name: worktree-flow
description: 任务工作树的使用、freshen 与冲突纪律。qa/dev 在 .worktrees/<id> 内工作、合入基线分支、处理冲突时使用。
---

# 工作树纪律

一个任务一棵树：目录 `.worktrees/<id>`，分支 `task/<id>`，自**基线分支**分出。基线 = architect 派发那一刻的当前分支，钉于 `tasks/specs/<id>/base-branch`——全流程唯一合并参照，qa/dev 不做任何 git 拓扑手术（建树/合并/清树都在 architect 手里），只在树内工作与提交。**基线常绿**是全流程的不变量；基线与 develop/main 的关系归团队 CI/CD 管。

## 铁律：cd 不持久

子代理里每条 Bash 都是新 shell。**所有**工作树内的操作，要么 `git -C <树路径> …`，要么同一条命令里 `cd <树路径> && …`。忘记这条，命令会默默打在主检出上——那是本流水线最贵的一类事故。

## 进树与 freshen（qa/dev 第一步）

```
git -C <主检出> worktree list        # 树应已由 architect 建好；不在 = 派发缺陷，报告
BASE="$(cat <主检出>/tasks/specs/<id>/base-branch)"
cd <主检出>/.worktrees/<id> && git merge --no-edit "$BASE"   # 开工前吸入最新基线
```

## 阶段规则

- **qa 阶段**：只在树内提交（`task <id>: acceptance tests (red)`），推进分支即止。红色测试不进基线。
- **dev 阶段**：绿了之后——① 树内 `git merge --no-edit "$BASE"` 再跑一遍 acceptance 保持绿；② 树内提交（`task <id>: implement, acceptance green`）；③ **交付即止**：不合并回基线、不清树。合并、合并后全量测试（所有任务的测试）、红则 revert、清树，由 architect 在验收门执行。分支 `task/<id>` 与 `.worktrees/` **永不 push**——推向团队远端的只有验收门产出的、你本人签名的基线分支提交。

## 冲突纪律

冲突只在树内解决。逐个冲突块回答"两侧各自想要什么"，答案去两侧的一手来源找：本侧看 spec 与本任务提交信息，对侧看 `git log -p "$BASE" -- <文件>`。按意图合成解法，**禁 `--abort` 了事、禁机械保留单侧**。解完必须重跑 acceptance.sh 至绿才允许继续。解不出意图归属的，停下报告 architect——architect 依两侧 spec 出具**意图简报**（每个冲突块两侧各想要什么；不附他任务 spec 全文），dev 按简报合成解法、重新过验收。验收门 merge 时出现的冲突由 architect 中止合并（此处 `--abort` 合法：不是解决冲突，是拒绝在门口解决）并携简报重派。每次代码冲突都是**正交性失败的信号**：architect 应把重叠原因记入相关 spec 的变更记录，反哺切分质量。

<!-- 冲突纪律借鉴 mattpocock/skills 的 resolving-merge-conflicts（MIT）之意图溯源原则。 -->
