---
name: review-synthesis
description: 对抗性评审 synthesis 的三遍准绳（机械/证据/对抗）。challenger 对照 brief 与证据目录评审 synthesis.md 时使用。
---

# 评审 Synthesis

三遍按序跑、分开报告，永不合并成一个总评分：一份 synthesis 可以机械完整却仍建在无源断言上，也可以证据干净却仍藏着一个脆弱的胜者——遍与遍一合并，一种失败模式就会遮住另一种。

## 机械遍（可判定，无判断）

- **空格子**：判据×候选项任一格无评级，或被否决的候选项未在矩阵中如此标注。[BLOCKING]
- **算术断裂**：按声明评级（`--`/`-`/`0`/`+`/`++` → −2…+2）与 brief 权重重算每个加权总分；任何不符，或排名句与总分矛盾。[BLOCKING]
- **否决裁定缺失**：brief 任一否决项缺少显式的逐候选项 pass/fail，或候选项已撞死否决项却仍按活着排名。[BLOCKING]
- **无主评级**：矩阵格没有对应论证小节，或论证没引用任何证据文件。[BLOCKING]
- **范围漂移**：synthesis 里出现 brief 没有的判据、权重或候选项，或 brief 里有的凭空消失。[BLOCKING]——brief 是承诺；重新谈判发生在用户那里，不发生在 synthesis 里。

## 证据遍（对照溯源链）

- **无源事实**：承重断言（推荐结论赖以成立的）没有可追溯进证据文件的引用。[BLOCKING]
- **洗白的推断**：证据里标 [INFERENCE] 的断言在 synthesis 里以纯事实面目出现。[BLOCKING]
- **拉伸引用**：证据文件说的比 synthesis 断言的少（证据："作者的 M1 上启动约 200ms"；synthesis："同类最快启动"）。承重时 [BLOCKING]，否则 [SUGGEST]。
- **抽查失败**：WebFetch 最强的两三条引用；来源没说链条声称它说的话，即 [BLOCKING]。
- **未声明缺口**：某候选项的证据小节在某判据下声明了 GAP，synthesis 却在那格自信打分。[BLOCKING]。（在声明缺口之上打分，只有 synthesis 说明这是暂定并给出原因时才允许。）

## 对抗遍（判断，用研究自己的数字论证）

- **次选者的最佳论证**：从证据文件诚实地构建它。若比 synthesis 承认的更强，点名 synthesis 低估了什么。[SUGGEST]；若该论证在 brief 自己的权重下真能赢，则 [BLOCKING]。
- **脆弱的胜者**：若一步变动（一个权重 ±1、一个评级挪一档）就翻转排名而敏感性小节没说，这个遗漏是 [BLOCKING]——用户即将把一次抛硬币当成裁决来拍板。
- **场景误读**：若 brief 的场景分布存在与 synthesis 假设不同的合理读法，写明替代读法及其会改动哪些评级。[SUGGEST]。

发现要引用精确位置（文件 § 标题）并写明解决方式。结尾恰好一行结论：`Conclusion: no blocking items` 或 `Conclusion: N blocking items`——analyst 的收尾就认这个字面串。不注水：机械遍干净是应然不是功劳，三条复述口味的 [SUGGEST] 不如一条重读场景的值钱。
