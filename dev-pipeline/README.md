# Agent Pipeline · 三段式开发流水线

Claude Code 上的 architect → qa → dev 流水线：architect 作主会话负责对齐、设计与调度；qa / dev 作子代理分别交付**红色的机械验收**与**变绿的实现**；两个只读 reviewer 由 qa / dev 嵌套唤起。任务状态唯一真源是 `tasks/task.html`，一切读写走 `taskctl`，验收判定收敛为 `acceptance.sh` 的退出码。

技能写法与拆分参照 [mattpocock/skills](https://github.com/mattpocock/skills)（MIT）：小、可组合、可判定；借用对照见文末。

```
                    ┌────────────────────────────────────────────┐
 用户 ↔  architect  │ /grill-me → /deep-module-design → /task-spec│  主会话 (claude --agent architect)
        （单写者）   │ taskctl add/set/next/verify · /token-budget │
                    └──────┬─────────────────────────┬───────────┘
                     派发(后台)                  派发(后台)
                    ┌──────▼──────┐            ┌─────▼───────┐
                    │     qa      │            │     dev     │      子代理，各处理一个 taskId
                    │ 骨架+红测试  │──worktree──▶│ 实现→绿→交付 │      .worktrees/<id> · task/<id>（architect 建，验收门收）
                    └──────┬──────┘            └─────┬───────┘
                      唤起(嵌套)                 唤起(嵌套)
                    ┌──────▼──────┐            ┌─────▼───────┐
                    │ qa-reviewer │            │ dev-reviewer│      只读纯函数，产出 [BLOCKING]/[SUGGEST]
                    └─────────────┘            └─────────────┘
```

## 目录

```
CLAUDE.md                         全角色共享协议（目录契约/状态机/单写者/git 契约）
.claude/agents/                   architect · qa · dev · qa-reviewer · dev-reviewer
.claude/skills/                   12 个技能（见文末矩阵），各角色经 skills 字段预载各自纪律
.claude/skills/task-registry/scripts/taskctl.py          task.html 唯一编辑器 + 评审闭环门禁 review-check（已端到端验证）
.claude/skills/token-budget/scripts/check-token-budget.sh 派发门禁（已验证 OK/LOW/UNKNOWN 全分支）
.claude/pipeline/statusline-budget.sh                     statusline → budget.json 数据源
.claude/settings.json             statusline 接线 + git/mvn 免审批建议
tasks/task.html                   任务总表（空模板）
tasks/specs/_template.html        spec 模板（taskctl add 自动实例化）
tasks/specs/_example.html + _example/acceptance.sh        填好的满分示范
```

## 安装

前置：Claude Code **≥ 2.1.219**（依赖子代理嵌套默认开启与 `${CLAUDE_PROJECT_DIR}` 替换）、python3、git、jq 不需要。

1. 解压到**任意位置**（不要直接解进项目根），运行 `bash install.sh <项目根>`。安装器**不覆盖任何既有文件**：
   - 流水线协议在 `.claude/CLAUDE.md`，经根目录一行 `CLAUDE.local.md` 垫片（`@.claude/CLAUDE.md`）装载——**项目自己的 CLAUDE.md 一个字节不碰**，两者同时生效（memory 文件是叠加不是覆盖）。你已有 CLAUDE.local.md 则幂等追加 import 行（它本就是你的个人文件）。
   - 个人配置全在 `.claude/settings.local.json`（官方个人位，auto-gitignored）——statusline、权限清单、归因关闭都在里面，与团队可能提交的 `.claude/settings.json` 互不相扰。
   - 与项目同名的既有文件一律跳过并列出清单，由你手工合并。
   排除是机械不变量：taskctl 每次运行自动把 `tasks/`、`.worktrees/`、`.claude/`、`CLAUDE.local.md` 写入 `.git/info/exclude`（幂等；已被 git 跟踪的路径跳过）。**个人仓库**想入库换契约历史的：正常提交即可，taskctl 对已跟踪路径自动让路。
2. 项目根必须是 git 仓库；流水线运行在**你当前检出的分支**上（基线分支，派发时钉定），与 develop/main 的关系归团队 CI/CD 管。`chmod +x .claude/pipeline/*.sh .claude/skills/*/scripts/*`。
3. 首次 `claude` 启动时接受 workspace trust（statusline、项目技能的 allowed-tools 都依赖它）。
4. statusline：`.claude/settings.local.json` 已接好 `statusline-budget.sh`。若你已有自己的 statusline，把你的脚本里加一行 `tee >(bash .claude/pipeline/statusline-budget.sh >/dev/null)` 或直接调用它——**没有它，/token-budget 永远 UNKNOWN**（门禁会降级而不是失效）。
5. 启动：`claude --agent architect --model fable`（frontmatter 已写 `model: fable`，命令行再钉一次是主会话的保险；想固定为默认，在 settings.json 加 `"agent": "architect"`）。建议配 `--permission-mode acceptEdits` 或维持 settings 里的 git/mvn 免审批清单，否则后台子代理的权限询问会频繁上浮打断你。

## 安装（plugin 分发）

```bash
claude plugin marketplace add vincentzz/zz-claude-marketplace     # 或 curl install.sh 一行装
claude plugin install dev-pipeline@zz-claude-marketplace
cd <任意项目根> && claude --agent architect --model fable # init 自动走
```

升级：`claude plugin marketplace update zz-claude-marketplace`（或 settings 里 autoUpdate）。

**profile 切换**：`claude plugin enable|disable dev-pipeline` 或 `/plugin` 界面，本质是编辑 settings 的 `enabledPlugins`（键 = `plugin@marketplace`，三态：true / false / 缺省→plugin 的 defaultEnabled）。按项目切的正确杠杆是**各项目的 `.claude/settings.local.json`**——settings 四层 Managed > Local > Project > User 高层胜，项目层开的插件用户层关不掉、只有 local 压得住；且 local 个人不入库，与本 harness 的个人工装原则一致。老版本 `/plugin` 可能只写用户层，届时手改 local 文件。

**profile 按切换用，不按叠加用**：多个 plugin 可同时 enable（布尔独立无互斥），但每个 enabled 插件的全部 skill 描述常驻每个会话的系统提示词（token 税），且两个 profile 的同名 agent（都叫 architect）冲突语义未定义。约定：每项目 local 层恰好启用一个 pipeline profile；跨 profile 通用件拆成独立小 plugin 才是可叠加单元；新 profile 的 plugin.json 带 `defaultEnabled: false` 出厂（v2.1.154+），装而不生效、切换才生效。开发模式：`claude plugin marketplace add /path/to/本仓库`（本地路径市场，改仓库即生效，无需 symlink）。

**装后三个实测项**（plugin 化后的版本敏感点，绿了再上生产）：agent frontmatter 的 `skills:` 预载对 plugin 内技能是否需要 `dev-pipeline:` 前缀；`${CLAUDE_SKILL_DIR}` 在 plugin 技能内的解析；statusline 经 init 写入后的显示。任何一项红，退回上一节的手工用户级安装（保留为兜底文档）。

## 手工用户级安装（兜底路径）

`bash install.sh user` 把机器件装进 `~/.claude/`（5 agents、12 skills、协议正文 `pipeline/PROTOCOL.md`、statusline；settings.json 只增不改——statusLine/attribution 两键缺才写）。此后**任意项目零拷贝接入**：项目根运行 `claude --agent architect --model fable`，architect 启动自检发现未初始化，即走 `/pipeline-init` 的幂等清单——创建 `CLAUDE.local.md` 垫片（`@~/.claude/pipeline/PROTOCOL.md`）、**构建约定审讯**（探测 pom.xml/Cargo.toml/build.zig… 给推荐答案，你逐项拍板：语言/全量测试命令/任务选取机制/未实现桩）、`taskctl` 自播种 `tasks/` 并写排除守护。重复 init 的合法输出是"已初始化，无事可做"。

memory 叠加语义：`~/.claude/CLAUDE.md`（若有）与项目 CLAUDE.md、CLAUDE.local.md **拼接**生效——协议正文因此不放 `~/.claude/CLAUDE.md`（会灌进所有无关项目），而由项目垫片按需 import。用户级的固有成本要知情：agents/skills 的描述在**所有**项目的系统提示词常驻（约数百 token），`qa`/`dev` 等名字出现在每个项目的 agent 列表——惰性无害，但存在。项目级整套拷贝（`install.sh project <根>`）仍保留，适合想逐项目魔改协议本身的场景。

## 安装后目录结构（团队仓库实测）

沙盒场景：项目自有 `CLAUDE.md`（团队共享 context）、团队跟踪的 `.claude/settings.json` 与一个团队 skill。安装并跑一次 taskctl 后（`[T]` = git 跟踪·团队共享，`[x]` = `.git/info/exclude` 屏蔽·个人工装）：

```
├─ CLAUDE.md                       [T]  团队共享 context，一字未动
├─ CLAUDE.local.md                 [x]  装载垫片（@.claude/CLAUDE.md）
├─ pom.xml · src/**                [T]  项目本体（任务产出的代码与测试合并进这里，你签名提交）
├─ .claude/
│  ├─ settings.json                [T]  团队共享设置，照常跟踪
│  ├─ skills/team-conventions/     [T]  团队共享 skill，照常跟踪
│  ├─ CLAUDE.md                    [x]  流水线协议正文
│  ├─ settings.local.json          [x]  个人设置（statusline / 权限 / 归因关闭）
│  ├─ agents/（5 个）              [x]
│  └─ skills/（11 个）· pipeline/  [x]
└─ tasks/                          [x]  spec · task.html · notes · 评审
```

要点三条：**分界在文件级不在目录级**——ignore 规则不影响已跟踪文件，`.claude/` 整目录入 exclude 后团队资产纹丝不动、个人增量整体隐身；**五项机械验证全过**——团队跟踪清单逐字不变、`git status` 全净、`git add -A` 干跑无可加项（手滑免疫）、`check-ignore -v` 可指认每个屏蔽的出处行、队友 clone 零 harness 痕迹；**运行时 memory 三层叠加**——团队根 CLAUDE.md + 个人垫片 import 流水线协议，共享 context 与个人协议同时生效、互不知晓对方存在。

## 与你的原始设计的映射

| 你的条目 | 落点 |
|---|---|
| architect a. grill-me 对齐 | `/grill-me`（改编自 mattpocock/grilling，加"可落笔写 spec"完成判据 + **边界审讯**：依赖取舍/落位三连测/变化分布校准——判定程序做功课，判断权交用户） |
| architect b. deep module 接口与责任边界 | `/deep-module-design`：Ousterhout 词汇 + 正交/可组合切分判据 + **边界三分法**（必须知道 2.1 / 不需要知道 2.2 / 不得知道 2.5 禁知）+ **失败归属表**（面向甩锅的机械判责）+ 设计两次。禁知 ≠ 禁读：核心是**视同不知**的出处约束（无 spec 出处的知识不得参与决策，含权重里的先验），纪律在 CLAUDE.md，任务增量在 spec 2.5，实现提示走 `specs/<id>/architect/dev-hints.md` 通道 |
| architect c./d. 生成 spec、维护状态与优先级 | `/task-spec` + `taskctl`；行序即优先级，`add --top/--after` 插队，`move` 调序 |
| architect e./f. 余量 ≥20% 才唤醒 QA/dev 并更新列表 | `/token-budget` 门禁（exit 0 才派发）+ `taskctl set … in-progress` |
| architect g. 余量 <20% 停发、等 refresh | 门禁 exit 1 → 停发新任务并播报 `resets_at` 重置时间 |
| QA a–f | `qa.md` 流程 1–8：进树（architect 派发前建好并钉基线）→**落骨架**→红测试→acceptance.sh→qa-reviewer 闭环→提交 |
| dev a–f | `dev.md` 流程 1–6：进树→实现至绿→dev-reviewer 闭环→交付绿分支（合并与清树在 architect 验收门）|
| qa-reviewer / dev-reviewer | 只读嵌套子代理 + `/review-test-cases`、`/review-code` 准绳，输出 [BLOCKING]/[SUGGEST] |
| 任务管理目录结构 | 与你给的完全一致；task.html 表头 `taskId/Test/Dev/Task` 原样保留 |
| 每个 agent 各自的 skill | 子代理 frontmatter 的 `skills:` 字段**整篇预载**各自纪律（见矩阵） |

## 八个有意的偏离（设计决策，可谈）

1. **QA 不把红测试合进基线分支。** 你写的 QA"提交合并"落成：提交并推进 `task/<id>` 分支、开工前把基线吸入分支；由 architect 在验收门 `--no-ff` 合回（见第 7、8 条）。换来**基线常绿**这个不变量——否则 `taskctl verify` 在主检出上没有意义。
2. **"找 architect 要任务"落成派发制。** task.html 单写者是判责地基，qa/dev 自取会引入多写者。pull 语义由 `taskctl next test|dev` 机械保留（选取规则可审计），"要"的动作发生在 architect 派发词里。真 pull 语义已随 teams 一并否决（见文末决策记录）；pull 的可审计替身就是 `taskctl next`。
3. **"剩余 token"取订阅额度窗口语义。** 你说"待 token refresh"，对应 Claude Code statusline 提供的 `rate_limits` 5h/7d 窗口（含 `resets_at`）。门禁取 5h 与 7d 余量的**较小值**对阈值（默认 20%），另设 architect 上下文余量阈（默认 15%）——上下文耗尽同样会杀死调度会话。API 计费账号没有 rate_limits，门禁自动 UNKNOWN 降级（可自行改脚本接 ccusage 之类）。
4. **新增 acceptance.sh 作为唯一机械验收入口。** 你的"可机械判定"被具体化为：一条命令、退出码即判定、qa 交付、dev 与 architect 两处跑同一脚本结论一致。`taskctl verify <id>` 就是它的封装。
5. **Java 先测先行的编译问题 → 接口骨架前置。** 测试先于实现，在 Java 里意味着编译都过不了。解法内建于流程：spec 2.1 要求**可编译级完整**的接口签名（architect 交付），qa 第一步把它落成抛 `UnsupportedOperationException` 的骨架——于是"红"恒指**运行期红**，编译失败被定义为 qa 侧契约违规，责任清晰。

6. **评审闭环进了状态门。** 你的原始设计里 reviewer 只"提建议"；这里把"建议已处置"变成了机械可判定事实：`taskctl set … done` 内建 review-check——对应 reviewer 的最新 `review-N.md` 必须无 `[BLOCKING]`、含逐字的「结论：无阻塞项」结论行、轮数 ≤2，否则状态推不动。评审仍由 qa/dev 在热上下文内环闭合（修复便宜），但**闭环与否的判定权收归门禁**——被审者可以干活，不能给自己签收。`--force` 是唯一逃生门，需在 notes 留痕。
7. **合并权在验收门。** dev 交付绿分支即止；`--no-ff` 合并、合并后**全量测试**（所有任务的测试，防跨任务回归）、红则 revert、清树，全部由 architect 在门内执行。基线常绿从"事后检测"升级为"门口机械预防"，不可逆步骤与状态推进权收归同一角色。评审文件的防篡改留痕可选：在 `tasks/` 内自建私有 git（harness 不入团队库，见决策记录）。冲突解决权**不**随之上移：architect 不写代码的不变量保持绝对——冲突时它出具跨任务意图简报（两份 spec 都是它写的，这是它独有的合法知识），由 dev 在树内合成解法、重新过验收。

8. **基线分支相对化 + worktree 生命周期归 architect。** harness 不预设 main：基线 = architect 派发那一刻的当前分支，钉于 `tasks/specs/<id>/base-branch`；建树在派发前由 architect 完成（消除"qa 运行时才建树、你中途切了分支"的基线竞态），验收门合回的也是这条基线，且门口机械核对当前分支 == 钉定基线。合并进 develop/main 等共享分支是团队 CI/CD 的辖区——门内绿是你对自己分支的承诺，CI 绿才是团队对共享分支的承诺。

## 跑一轮是什么样

```
你:        做一个进程内令牌桶限流器
architect: (grill-me 逐题对齐 → deep-module 设计 → taskctl add "令牌桶限流器" → 钉基线并建树)
           已注册 0001，spec 见 tasks/specs/0001.html。预算 OK，派发 qa。
qa(后台):  进 architect 建好的 .worktrees/0001 → 落骨架 → 写 @Tag("task-0001") 测试 → acceptance.sh 红态
           → 唤起 qa-reviewer → 处理 2 条 BLOCKING → 提交 → 交报告(含 AC↔测试映射、红态证据)
architect: 报告齐备 → taskctl set 0001 test done（内建校验 qa-reviewer 评审闭环）→ 预算 OK → 派发 dev。
dev(后台): merge 基线 → 逐条 AC 变绿 → dev-reviewer 闭环 → 再绿 → 交付绿分支（不合并）→ 交报告
architect: 验收门：verify --checkout 绿 → --no-ff 合并 → 全量测试绿 → set 0001 dev done（内建评审闭环校验）→ 清树 → 汇报全绿。
```

任何角色发现 spec 有误：停手、写 notes、上报仲裁（CLAUDE.md「越界即停」）。architect 改判会记入 spec 变更记录——判责链不断。

## 角色 × 技能矩阵

| 技能 | architect | qa | dev | qa-rev | dev-rev | 来源 |
|---|---|---|---|---|---|---|
| grill-me | 调用 | | | | | 改编 mattpocock/grilling |
| deep-module-design | 调用 | | | | 预载 | 改编 codebase-design + DESIGN-IT-TWICE，扩展失败归属表 |
| task-spec | 调用 | | | | | 自研（对齐 to-spec 思路） |
| task-registry (taskctl) | 调用 | 只读参考 | 只读参考 | | | 自研 |
| worktree-flow | | 预载 | 预载 | | | 冲突纪律借 resolving-merge-conflicts |
| mechanical-acceptance | | 预载 | | 预载 | | 三反模式精编自 tdd |
| agent-notes | | 预载 | 预载 | | | 自研 |
| review-test-cases | | | | 预载 | | 自研 |
| review-code | | | | | 预载 | 改编 code-review 两轴 + Java 坏味道裁剪 |
| coding-standards | | | 预载 | | 预载 | 自研：冷/热分区优先级（热区性能仅次于正确性，认定需出处）、现代特性、代码英文（含机械 grep 检查） |
| pipeline-init | 调用 | | | | | 自研：幂等项目初始化——装载垫片、构建约定审讯（事实自查/决策拍板）、taskctl 自播种复用 |
| token-budget | 调用 | | | | | 自研（statusline rate_limits 数据源） |

"预载" = 子代理 frontmatter `skills:` 字段在启动时注入全文；"调用" = 按描述触发或 `/名字` 显式调用。上游仓库 MIT 许可，改编处已在各 SKILL.md 尾注标明。

## 移植到其他语言

机械层（taskctl、task.html、门禁、预算、评审闭环）**语言无关**——一切判定收敛于 `acceptance.sh` 的退出码，脚本即语言接缝。移植面共五处，全部有单点定制位：

1. **CLAUDE.md 构建约定块**：语言基线、全量测试命令、任务测试选取机制、未实现桩（其余文件只引用此块，不重复语言细节）。
2. **acceptance.sh 内容**：换成 `cargo test task_<id>` / `pytest -m task_<id>` / `cabal test --test-options="--pattern task-<id>"` 等——脚本契约（exit 0 ⟺ 全过、幂等、无交互）不变。
3. **coding-standards 的语言特性节**：整节替换为目标语言实例，优先级与冷热分区不变。
4. **settings.local.json permissions**：`Bash(mvn *)` 换成目标构建工具。
5. **示例 spec**（`_example.html`）是 Java 示范，仅供参照，不必移植。

红态规则的通用表述：构建必须过（编译型语言的编译、动态语言的加载/导入），红必须红在运行期断言或未实现桩。

## 本地降级模式（配额耗尽时全员切本地 LLM）

一条命令切换：`PIPELINE_LOCAL_MODEL=qwen3-coder:30b bash ~/.claude/pipeline/pipeline-local.sh`。原理：全员切换不需要进程分离（BASE_URL 本就是进程级，正好整体跟随）；启动器每次从 `~/.claude` **机械派生**本地 profile `~/.claude-pipeline-local`（agents 的 `model:` 行替换为本地模型、reviewer 可指定小模型、settings 注入本地必需项），经 `CLAUDE_CONFIG_DIR` 启动——派生产物不手工维护，主 profile 零污染、切回订阅即原状。

自动处理的三件事：frontmatter 的 `fable`/`opus` 若原样发给本地端点会 404——已按角色替换并兜底设置层级映射 env；attribution header 会使本地 KV cache 每请求作废（慢约 90%）——已在派生 settings 里关闭；预算门禁在本地无 rate_limits 会恒 UNKNOWN 并降并发——`PIPELINE_PROVIDER=local` 使其短路为 OK。**机械层全部照常**：taskctl、状态门禁、review-check、acceptance 退出码不认模型，verify 对本地产出与对 Fable 产出同一把尺。

### 决策表：什么信号，做什么

| 触发信号（从 check 输出 / 会话内提示可辨） | 判定 | 操作 |
|---|---|---|
| LOW，**5h** 余量触发（7d 尚余） | 最多等 5 小时 | **等**。停发新任务，在跑的收尾；几小时的窗口不值得一次上下文切换 |
| LOW，**7d** 周上限触发（重置以天计） | 本地降级的主场景 | 跑机械判据：`taskctl next dev` **有产出**（存在 spec+红测试就绪的任务）→ 切本地消化 dev 车道；exit 3（无 dev-ready）→ 等重置，别让本地模型去做 grilling/spec |
| **Fable 50% 池**撞顶（会话内提示，不在 budget.json 里） | 不是流水线级事件 | **不切本地**。主会话 `/model opus`，dev-reviewer 临时降 `opus`——只影响两个 Fable 角色，其余照常 |
| LOW，**上下文**余量触发（额度尚余） | 不是配额问题 | **不切本地**。在跑任务收尾 → 重启 architect 会话（状态在 tasks/，无损）→ 重派 in-progress |
| UNKNOWN（statusline 未装 / API 计费 / 数据过期） | 数据问题 | 修 statusline 或接受降级为单子代理并发；与本地降级无关 |
| **会话中途硬断**（消息直接被拒，非门禁拦截） | 配额耗尽于任务中途 | 子代理已死但无损：工作树、提交、notes 都在盘上。按下表切本地或等重置，重启后按 task.html 的 in-progress 行重派，幂等流程自动续上 |

### 切换序列

**订阅 → 本地**：① 确认本地端点在服务、模型已拉取、上下文 ≥64K（`OLLAMA_CONTEXT_LENGTH=65536`）；② 退出订阅会话；③ `PIPELINE_LOCAL_MODEL=<模型> bash ~/.claude/pipeline/pipeline-local.sh`；④ architect 启动自检 → `taskctl list` → 重派 in-progress 与 dev-ready；⑤ 只消化 dev 车道，本地模型反复 verify 不过或撞 maxTurns 的任务：置回 in-progress、记 notes、留给订阅。

**本地 → 订阅**（重置时间到）：① 让在跑的本地子代理收尾或直接放弃（幂等，重派即续）；② 退出，`claude --agent architect --model fable`；③ 门禁恢复 OK 照常调度；④ 可选的质量回填：本地期间合并的任务（qa/dev notes 里应有 local 标注）挑重要的用订阅侧 reviewer 复检一轮 diff——本地 reviewer 放行过的东西，值得一次强校验器的事后抽查。

通用纪律：切换后最弱环节从 dev 反转为 architect/qa 的判断力，本地模式优先消化 dev 车道；`maxTurns` 兜底防工具死循环；两个方向的切换都只是"重启会话 + 重派"——tasks/ + git 即全部状态。

### 运维纪律（能力现实）

切到本地后，最弱环节从 dev 反转为 architect/qa 的判断力：本地模式**优先消化 dev 车道**（spec 与红测试已就绪的任务，弱模型被机械验收兜底）；新需求的 grilling、spec、仲裁尽量留给重置后的订阅模型。给本地端点配 `maxTurns` 兜底（tool_choice 可能被忽略），上下文给足 64K+。

### 情境操作表（信号 → 诊断 → 操作）

| 信号 | 诊断 | 操作 |
|---|---|---|
| LOW，5h 重置在数小时内 | 5h 窗口耗尽 | 默认等重置；`taskctl next dev` 有产出且急，才切本地 |
| LOW，7d 见底、重置在数天后 | 周上限耗尽 | 主场景：有 Test=done 待 dev 的存货 → 切本地消化 dev 车道；只剩待 grilling 的 → 等 |
| LOW 但额度正常、上下文 <15% | architect 会话膨胀 | **不切本地**：收尾→退出→重开订阅会话（状态在 tasks/，无损） |
| Fable 不可用/自动降级 | Fable 50% 池顶，总池未尽 | `/model opus` 继续；dev-reviewer 临时降 opus |
| 门禁恒 UNKNOWN | statusline 未装/刚启动/API 计费 | 装 statusline；不装则接受单子代理并发 |
| 决定切本地 | — | 预检：模型在位、上下文≥64K、端点通 → `PIPELINE_LOCAL_MODEL=… pipeline-local.sh`；in-flight 丢失按 in-progress 行重派 |
| 本地运行中订阅重置 | — | 推到验收门或直接停 → 重开订阅会话；可选：对本地期间的合并区间补一轮订阅级 review |
| 本地 dev 不收敛 | tool_choice 被忽略 | maxTurns 兜底超时，verify 打回重派 |

贯穿原则：LOW 先分辨触发池（5h/7d/上下文，处方各不同）；切本地的机械前置判据是 `taskctl next dev` 的退出码；方向切换永远是重启会话而非迁移状态——状态从不住在会话里。

## 决策记录：agent teams（已否决）

**结论：qa/dev 恒为 architect 的 subagent，不采用 agent teams。** 依据固化如下，防止未来重新纠结：

1. **Token 经济（决定性）**：官方文档自认 teams 协调开销大、令牌消耗明显多于单会话。结构原因：teammate 是常驻会话，上下文跨任务单调增长——正是我们量化过的 cache-read 放大最贵的形态；subagent 阅后即焚，45-90K 上下文封顶即弃，每任务成本有硬上界。
2. **skills 预载失效**：teammate 不应用 agent 定义里的 `skills`/`mcpServers` 字段——"每角色各配纪律"的设计失效，纪律得靠消息注入，更贵且更不可靠。
3. **实验特性**：flag 门控、`/resume` 不恢复队友、行为随版本漂移。
4. **与禁知结构冲突**：干过任务 A 的常驻 dev *记得* A，做 B 时"视同不知"从结构保证退化为纪律负担。子代理的阅后即焚是 clean-room 的机械实现——每个任务拿到的 dev 从未见过其他任务。

真 pull 语义（队友自认领）的可审计替身就是 `taskctl next`：选取规则机械、单写者不破。SendMessage 是 teams 门控工具，本设计不依赖任何会话续接——续做一律重派，幂等流程（树在则复用、notes 在则接上）保证重派无损。

## 决策记录：harness 是个人工装，不入团队库

**结论：在团队仓库中，`.claude/**` 与 `tasks/**` 属于 committer 个人，permanently untracked（经 `.git/info/exclude`）。**

依据：**最终 committer 是唯一责任主体，Claude 不是**——不能被追责的实体不该出现在责任链上。由此推出三件事：

1. **工具自备，产出自签**：harness 与你的编辑器配置同类，是产出提交的私人生产资料。用不用 Claude、用什么模型矩阵、评审几轮，都是 committer 的私事；团队评判的是你签名提交的产物（代码 + 测试，经团队自己的 PR/CI 流程），不是你的生产过程。
2. **不制造可甩锅的共享物**：harness 入库会诞生"流水线的锅"这种借口实体。个人工装下，提交质量的归因唯一：你选了你的工具，你签了你的产出。
3. **归因唯一化**：`.claude/settings.local.json` 已置 `attribution: {commit: "", pr: ""}`——提交里不出现 Co-Authored-By: Claude 与 Generated with 尾注，git 历史里只有人。

交付物 / 工装的分界线：`src/**`（含测试——它们随任务分支合并入库）签名给团队；`tasks/**`（spec、notes、review）与 `.claude/**` 留给自己。**合同的可执行部分（测试）进团队库，合同的谈判记录（spec/评审）留在个人车间。**

目录布局的配套决定：`tasks/` **留在项目根、不挪进 `.claude/`**。三个理由：它是 harness 的人面（spec 要读、task.html 要在浏览器开、notes 要翻），dot 目录会隐身且 `rg` 默认跳过 hidden；".claude/ 不入库"的前提不可靠——团队有意提交 `.claude/`（共享 commands/skills）正是官方设计意图，塞进去反而更易被卷入提交；`.claude/` 是 Claude Code 的保留命名空间，与工具未来的目录圈占相撞比与项目相撞更糟。误提交风险由 taskctl 的排除自守护机械消除（拥有状态的工具保证状态不入库）。

定价过的代价：评审文件防篡改从 git 留痕降级为可选私有 git（`cd tasks && git init`，一行）；跨成员 spec 互不可见，任务级正交性的跨人协调回到人类层（PR、设计评审）——它本来也该在那。个人仓库不受此约束（见安装节的两种模式）。

## 调参位

- **模型矩阵**（frontmatter 已配）：architect=`fable`、qa=`opus`、dev=`opus`、qa-reviewer=`opus`、dev-reviewer=`fable`。理由：spec 与仲裁是最高杠杆点，Fable 花在 architect；dev 线保留"便宜生成器 + 昂贵校验器"的不对称（dev-reviewer 是全流水线最便宜的会话，升 Fable 边际成本最低、收益最高）。注意 Fable 在 Max 订阅上以约 2 倍权重计入共享池且封顶周限额的 50%——撞顶只影响 Fable 角色，届时把 architect/dev-reviewer 临时降为 `opus` 即可（改 frontmatter 或 `/model`）。别名会随新版本漂移，要钉死就换成 `/model` 列表里的完整模型串。**矩阵是默认值不是定值**：Agent 调用支持 per-invocation 模型覆盖（解析优先级：`CLAUDE_CODE_SUBAGENT_MODEL` env > 调用参数 > frontmatter > 主会话），architect 按三判据动态选模——难度降档（简单 dev 任务派 sonnet，机械层兜底）、水位降档（余量 <40% 降一档延长跑道）、失败升档（重派比上次高一档）——形成 fable→opus→sonnet→本地 的梯度降级连续体。注意 `CLAUDE_CODE_SUBAGENT_MODEL` 优先级最高会碾平一切 per-agent 区分，勿全局设置。
- **动态模型梯度**：architect 派发时可传逐次 model 参数（仅 sonnet/opus/haiku 枚举，fable 与本地模型传不了——前者靠 frontmatter，后者必须整进程切换，见本地降级模式）。策略：充足带按矩阵；紧张带 dev 降 sonnet（Sonnet 5 与 Opus 5 价差已收窄至 1.67×，降档省约四成而非旧时代的五倍——只降 dev 划算，降 qa 不划算）；verify 打回的降档任务重派时升回 opus。**勿设 CLAUDE_CODE_SUBAGENT_MODEL**（上游 bug：会吞掉逐次参数）。
- **并发**：architect 硬编码 1 qa + 1 dev。加并发前先想清楚合并串行化（多 dev 同时回并基线需要合并队列）。
- **阈值**：`PIPELINE_MIN_QUOTA_PCT`（20）、`PIPELINE_MIN_CONTEXT_PCT`（15）、`PIPELINE_BUDGET_MAX_AGE`（900s）。
- **评审轮数**：上限 2 已由 taskctl 机械强制（`MAX_REVIEW_ROUNDS`）；agent 文件里的"至多两轮"只是同一契约的提示语。
- **验收命令形态**：示例按 Maven + JUnit5 `@Tag`；换构建体系只需改 `_template.html` 第 3 节示意与 `_example/acceptance.sh`。

## 已知坑

- 子代理里 `cd` 不跨命令持久——所有树内操作 `git -C` 或 `cd … && …`（CLAUDE.md 已立铁律，仍是最常见事故源）。
- 子代理续做 = **重派**：SendMessage 是 teams 门控工具，默认配置下不存在（上游 issue #35240），本设计不依赖它——qa/dev 流程幂等，重派的新实例从 spec/notes/工作树接续。
- 验收门第①步的门前检查：主检出应干净——`tasks/` 与 `.claude/` 不入库后天然干净，脏了说明有角色越界动了代码区。
- 恢复会话：任务状态全部在 `tasks/` 与 git 里，architect 会话挂了直接 `claude --agent architect` 重开即可续跑；在跑一半的子代理不会自动恢复，按 task.html 的 in-progress 行重派即可（qa/dev 流程均为幂等设计：树在则复用、骨架在则跳过）。
- `tasks/task.html.lock` 是 taskctl 的锁文件，勿提交（已在 .gitignore）。
- 项目根已有同名 `tasks/` 目录的仓库存在命名冲突：harness 的 `tasks/` 路径写死在协议文件与 taskctl 中，需全局替换后使用（已知限制）。
- 禁知的本体是"视同不知"的出处纪律，**无法用访问控制实现**——要禁的知识多半在权重里。机械抓手在产物侧：qa 断言必须旁注 spec 出处（写不出即删）、dev notes 必含 spec 沉默处的「自由选择清单」、reviewer 做可推导性检查（spec 推不出的结构/常量/语义 = 违反证据）。`disallowedTools` 按路径禁 Read 只能硬化辅助性的禁读卫生（挡增量污染），别指望它承载禁知本体。
