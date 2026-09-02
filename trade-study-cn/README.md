# Trade Study · 三角色选型评估流水线

面向决策的方案/技术栈结构化比较：**analyst** 作主会话，负责审讯、综合与交付物；每个候选项一个 **scout**，并行且隔离地调研；**challenger** 在出货前攻击结果。交付物：`synthesis.html` + `synthesis.pdf` + `deck.pptx`，全部派生自单一 `synthesis.md`。

```
                 ┌───────────────────────────────────────────────┐
 用户 ↔ analyst  │ /grill-me → brief.md → 派发 → synthesis.md    │  主会话（profile 入口 agent）
                 │ /study-brief · /render                        │
                 └───────┬───────────────────────────┬───────────┘
                  派发（后台，并行）             派发（后台，综合稿后）
            ┌────────────▼────────────┐      ┌───────▼─────────────────┐
            │    scout × N 个候选项    │      │        challenger       │
            │  一实例一候选项，        │      │  机械 / 证据 / 对抗     │
            │  对其他家失明           │      │  三遍评审               │
            │  → evidence/<option>.md │      │  → [BLOCKING]/[SUGGEST] │
            └─────────────────────────┘      └─────────────────────────┘
```

## 靠什么撑住

分析没有可以从红变绿的 ground truth，本流水线用**结构性对抗**替代机械验收：

- **溯源链**（`/evidence-discipline`）：synthesis 里每条断言追溯到证据文件；证据文件里每条断言带来源+检索日期，或显式 `[INFERENCE]` 标注。先验一律视为未知。
- **结构性反锚定**：scout 之间永不互看报告——对称深度由隔离保证，不靠纪律。（两条规则都移植自 dev-pipeline 的禁知纪律。）
- **数字归用户**：判据权重、否决项、场景分布是用户决策，analyst 可提议但绝不发明——用户是自身使用分布的最佳可用先知。
- **对抗性收尾**（`/review-synthesis`）：challenger 重算加权算术、核查矩阵每格非空、猎捕无源断言、为次选者构建诚实论证。至多两轮；研究只在 `Conclusion: no blocking items` 上闭合。

打分是**序数+权重**：矩阵格取 `--`/`-`/`0`/`+`/`++`（映射 −2…+2），用户权重产出排名——一个站得住的排序，没有 7.3 比 7.1 的假精度。被否决的候选项无论得分一律出局。

## 研究目录

```
studies/<id>/
├─ brief.md                  决策上下文：候选项、判据×权重、否决项、场景、深度
├─ evidence/<option>.md      每候选项一份，只由其 scout 写
├─ synthesis.md              唯一真源
├─ challenger/review-N.md    对抗轮次（≤2）
└─ out/                      synthesis.html · synthesis.pdf · deck.pptx（+ make_deck.py）
```

交付物跟随 brief 所用的语言。PDF 渲染需要 PATH 上有 Chrome/Chromium、weasyprint 或 LibreOffice；PPTX 需要 `python-pptx`——`/render` 先检查再承诺，缺什么会告诉你装什么。

## 安装与绑定

```bash
claude plugin install trade-study-cn@zz-claude-marketplace
cd <你的项目>
claude            # 普通会话
> /use-profile trade-study-cn
# 退出重启：claude 即以 analyst 开局
```

出厂即 `defaultEnabled: false` 与 `entryAgent: analyst`——装而不生效；`/use-profile`（来自常驻的 profile-switcher）按项目绑定。英文变体 **trade-study** 以同一条流水线交付全英文文案——两者只启用其一（agent 同名）。

模型：analyst `fable`、scout `sonnet`、challenger `opus`，写在各 agent 的 frontmatter 里，是层级名。模型集合不同的机器上，用 `ANTHROPIC_DEFAULT_FABLE_MODEL` / `ANTHROPIC_DEFAULT_OPUS_MODEL` / `ANTHROPIC_DEFAULT_SONNET_MODEL` 重绑层级，或用 `CLAUDE_CODE_SUBAGENT_MODEL` 加 `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1`（Claude Code ≥ 2.1.257；analyst 主会话另加 `--model`）钉死所有子代理。单独设 `CLAUDE_CODE_SUBAGENT_MODEL` 自 2.1.251 起被 frontmatter 压过，在这里不起作用。

## 有意的薄

无任务队列、无 worktree、无状态机、除 challenger 外无门禁——3 个 agent、5 个技能。0.1.0 有意从最小起步；每次加东西都要有来自真实研究的证据。

## License

MIT
