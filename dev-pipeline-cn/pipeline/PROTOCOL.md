# 流水线协议（所有角色共同遵守）

本仓库跑一条三段式开发流水线：**architect**（主会话，`claude --agent architect` 启动）负责对齐、设计、写 spec、调度；**qa** 与 **dev** 是子代理，分别交付验收测试与实现；**qa-reviewer** / **dev-reviewer** 是由 qa / dev 唤起的嵌套只读评审子代理。角色定义在 `.claude/agents/`，纪律在 `.claude/skills/`。

语言约定：文档（spec、notes、review、完成报告）用中文；**代码、标识符、代码内注释一律英文**，命令、状态值同英文。

构建约定由**项目侧 CLAUDE.local.md** 声明（语言基线、全量测试命令、任务测试选取机制、未实现桩、仅本任务测试槽位）——换语言只改项目垫片，本协议与机械层语言无关，一切判定收敛于 acceptance.sh 退出码。下文凡称"构建约定"皆指项目垫片中的该块。

## 目录契约

```
.claude/CLAUDE.md                本协议正文（经根目录 CLAUDE.local.md 的 @import 装载，
                                  不占用、不触碰项目自己的 CLAUDE.md）
tasks/task.html                   任务状态唯一真源，只能经 taskctl 修改
tasks/specs/<id>.html             任务 spec（architect 单写者）
tasks/specs/<id>/                 spec 引用的资源（图片等）
tasks/specs/<id>/acceptance.sh    机械验收唯一入口（QA 交付）：exit 0 ⟺ 全部 AC 通过
tasks/specs/<id>/<agent>/         该任务下各角色的笔记（notes.md、review-N.md）
tasks/specs/_template.html        spec 模板（taskctl add 自动实例化）
.worktrees/<id>                   任务工作树；分支 task/<id>；自基线分支建（architect 派发时钉定）
tasks/specs/<id>/base-branch      基线分支名（architect 建树时写入，全流程唯一合并参照）
.claude/pipeline/budget.json      statusline 落盘的额度数据（token-budget 门禁数据源）
```

`<id>` 恒为 4 位数字（如 `0001`）。下划线开头的 spec 文件不参与注册。

## 禁知纪律（forbidden to know，默认对所有任务生效）

禁知 ≠ 禁读：要禁的信息往往就在你的先验里——通行实现、惯用算法、"大家都这么做"。纪律是**视同不知**：被禁信息不得参与任何决策，哪怕你烂熟于心。操作化为出处约束：

- **出处约束**：每个判定都要能指认合法来源（spec 2.1/2.3/3 及其字面例、红测试）。指认不出出处的知识，一律当作不存在。
- **spec 沉默处的判别法**：所做选择若不泄漏到接口可观察行为，是 2.2 授予的实现自由；若会泄漏，是 spec 缺陷——按「越界即停」上报，不得用先验里的"通行做法"填补。
- **辅助卫生（禁读）**：spec 未引用的文件不读、不检索参考实现——读不进来的污染无需再"视同不知"。qa 另禁读 `specs/<id>/architect/dev-hints.md` 与其他任务的测试；dev 另禁读其他任务的 spec 与工作树。
- 审计面在产物：测试或实现里出现 spec 推不出的结构、常量、语义，即禁知违反的证据。任务级增量见 spec 2.5。

## 状态机（task.html 每行的 Test / Dev 两列）

```
Test: not-started ──派发qa──▶ in-progress ──qa交付且评审闭环──▶ done
Dev : not-started ──派发dev──▶ in-progress ──交付绿分支+验收门(合并+全量绿)──▶ done
门禁①: Test=done 之前 Dev 不得离开 not-started（taskctl 机械拦截）
门禁②: 推进到 done 需评审闭环——对应 reviewer 最新 review-N.md
       无 [BLOCKING]、含「结论：无阻塞项」结论行、轮数 ≤2（taskctl 机械拦截）
```

状态推进只由 architect 执行，且只经 `taskctl`。行序即优先级，越靠上越高。

## 写权限（单写者原则）

- `tasks/**`：**只有 architect 写**，例外两处——qa/dev 写各自的 `tasks/specs/<id>/<agent>/`，qa 写 `tasks/specs/<id>/acceptance.sh`。reviewer 一律不写盘，评审文本由唤起方落盘为 `review-N.md`。
- 生产代码与测试：**只在任务工作树 `.worktrees/<id>` 内改**。主检出的代码文件任何角色不得直接编辑；代码进入主检出的唯一途径是 architect 验收门内的合并。
- `tasks/**` 与 `.claude/**` 是**个人工装，不入项目库**（经 `.git/info/exclude` 屏蔽，见 README）。主检出因此天然干净；推向团队远端的只有你本人签名的基线分支提交。想为证据链留痕，可在 `tasks/` 内自建私有 git。

## Bash 纪律（子代理必读）

子代理里 `cd` **不跨 Bash 调用持久**。凡涉及工作树的命令，要么 `git -C <path> …`，要么在同一条命令里 `cd <path> && …`。写 `tasks/**` 一律用主检出下的路径（cwd 默认即项目根）。

## Git 契约

- **基线分支** = architect 派发时的当前分支，钉于 `tasks/specs/<id>/base-branch`；worktree 自它建、freshen 合它、验收门合回它。合并进 develop/main 等共享分支是**团队 CI/CD 的辖区**，harness 不越界——门内绿是你对自己分支的承诺，CI 绿才是团队对共享分支的承诺。
- 基线常绿：QA 的红色验收测试只进 `task/<id>` 分支，不进基线。常绿的含义是**对陌生人绿**：基线每个提交上，全量测试命令在只有工具链的全新克隆里必须过。需要更多的检查——构建过程验证、真实服务、一次性状态——都是仅本任务检查，只经 `acceptance.sh` 运行（见 `/mechanical-acceptance` 的两类检查）。
- dev 交付绿分支即止：最后一次把基线合入分支、树内跑 `acceptance.sh` 至绿、提交。`--no-ff` 合并回基线、合并后在全新克隆里跑**全量测试**（所有任务的回归测试，防跨任务回归，也防只在一台机器上过的东西）、红则 `revert -m 1`、清树——全部由 architect 在验收门执行。
- 冲突在工作树内按意图溯源解决，禁 `--abort` 了事；解完必须重跑 acceptance。

## 越界即停

任何角色遇到 spec 有误、测试与 spec 冲突、需要改动契约之类的越界情况：停下当前动作，把事实与建议写进自己的 notes，向上级（qa/dev → architect；reviewer → 唤起方）报告仲裁。不得自行改 spec、改他人产物或"顺手修一下"。
