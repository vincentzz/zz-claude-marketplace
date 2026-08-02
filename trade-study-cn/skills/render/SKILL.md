---
name: render
description: 从 synthesis.md 派生三份交付物（synthesis.html、synthesis.pdf、deck.pptx）——单一来源、三种渲染、一套共享设计系统。analyst 收尾研究时，或用户在修改 synthesis 后要求重渲时使用。
---

# Render · 单一来源，三份派生交付物

`synthesis.md` 是唯一真源。HTML、PDF、PPTX 全部由它一次派生；任何一份都不直接编辑——内容修正进 synthesis.md，然后全部重渲。三份都落在 `studies/<id>/out/`。

## 第 0 步 · 承诺之前先查工具链

```bash
python3 -c "import pptx" 2>/dev/null && echo pptx-ok
[ -x "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ] && echo chrome-ok
command -v chromium >/dev/null && echo chromium-ok
python3 -c "import weasyprint" 2>/dev/null && echo weasyprint-ok
command -v soffice >/dev/null && echo soffice-ok
```

- **HTML** 零依赖——永远可渲染。
- **PDF** 按先到先用：Chrome/Chromium headless（`--headless=new --print-to-pdf=<abs path> <abs html path>`），其次 weasyprint，再次 `soffice --convert-to pdf`。
- **PPTX** 需要 python-pptx（`pip install python-pptx`）。

缺渲染器时，产出能渲染的部分，并把解锁其余部分的确切包名告诉用户——绝不产出占位文件，绝不宣称一份打不开的交付物。

## 设计系统（三份共享；交付物是被设计的，不是默认主题的）

- **色板**：ink `#1F2430`（正文、深色面）· paper `#FAF7F2`（背景）· accent `#C4552D`（推荐结论、章节标记）· muted `#8A8578`（说明文字、来源）。评级：`++` `#2E6E4E` · `+` `#7FA88F` · `0` `#B8B2A6` · `-` `#D99A4E` · `--` `#B3423A` · 否决 `#B3423A` on `#F7E6E4`。评级永不只靠颜色编码——字形（`++`…`--`）必须始终在场。
- **字体**：标题用几何无衬线（Avenir Next → Helvetica Neue → 系统无衬线），正文用易读衬线（Iowan Old Style → Georgia）。CJK 输出：两种角色都用 PingFang SC / Noto Sans CJK。留白慷慨；章节标题下一条细 accent 线；无剪贴画、无渐变、无图库照片。
- **推荐结论是视觉主角**：每份交付物顶部附近一个 accent 色 callout 块；其余一律安静的纸墨色。

## HTML（`out/synthesis.html`）

手写、完全自包含（内联 CSS、无外部请求）、顾及打印。结构映照 synthesis.md：推荐 callout → 否决表 → 矩阵 → 逐判据细节 → 敏感性 → 来源。矩阵渲染为真 `<table>` 带评级 chip（彩色胶囊+字形）；被否决的候选项列头加删除线并在其列内挂否决横幅。正文最大宽度约 46rem；`@media print` 设页边距并避免矩阵跨页断开。

## PDF（`out/synthesis.pdf`）

把 HTML 打印出来——一套样式来源，两种分页形态。核实它能打开且非平凡：有 `pdftotext` 就用，否则检查文件 >10KB 且以 `%PDF` 开头。

## PPTX（`out/deck.pptx`）

一份**决策简报**，不是文档倾倒——拿着它应该能在五分钟内把这个决策讲完。为本研究写一次性 python-pptx 脚本（放在 `out/make_deck.py`，重渲可复现），16:9，页面：

1. **标题页**——brief 的问题、研究 id、日期、accent 色的一行推荐。
2. **推荐页**——胜者、最强的单一理由、次选条件、逐字取自 synthesis.md 的敏感性提醒。
3. **矩阵页**——判据×候选项表带权重、彩色评级格（字形始终在场）、加权总分行、否决标记。
4. **每候选项一页**——裁定行、前 2–3 条证据支撑的优劣势 bullet（每条 ≤12 词）、硬约束旗标。
5. **方法页**——判据与权重（以及谁定的：用户）、深度姿态、每候选项来源数、证据文件路径。

页面文字从 synthesis.md 提炼，绝不整段粘贴；需要一整段才说得清的东西属于 PDF，deck 的职责是让读者去打开它。

## 最后一步 · 核验

逐件开检（HTML 能解析、PDF 魔数、`python3 -c "from pptx import Presentation; Presentation('out/deck.pptx')"`），然后报告三个路径，以及跳过了哪个渲染器、为什么。
