---
name: mechanical-acceptance
description: 机械可判定验收的定义、acceptance.sh 脚本契约、红态规则与测试质量纪律。qa 落骨架、写验收测试、写 acceptance.sh 时使用。
---

# 机械可判定验收

**定义**：一条无交互命令，退出码即判定——exit 0 ⟺ 通过。不需要任何人读输出下结论。凡是要"看一眼确认"的验收条件都不合格，打回 spec 重写。

## acceptance.sh 契约

路径 `tasks/specs/<id>/acceptance.sh`，由 qa 交付，是该任务唯一验收入口：

```bash
#!/usr/bin/env bash
set -euo pipefail
CHECKOUT="${1:?用法: acceptance.sh <checkout-dir>}"
cd "$CHECKOUT"
mvn -q test -Dgroups=task-<id>
```

- 幂等、无交互、不依赖调用者 cwd、对检出目录之外只读。
- dev 在工作树上跑它，architect 合并后在主检出上跑它（`taskctl verify`）——同一脚本两处判定，结论必须一致。
- 一个任务的全部 AC 收敛为一条命令。这要求语言生态提供**按任务选取测试**的机制（构建约定（项目垫片 CLAUDE.local.md）所记）：Java = JUnit5 `@Tag` + `-Dgroups`；Rust = `cargo test task_<id>`（测试名前缀）；pytest = `-m task_<id>`；Haskell tasty = `--pattern`；通用兜底 = 按文件/目录命名圈定。选取机制是 acceptance.sh 的内部细节——脚本即语言接缝。

## 红态规则（qa 交付时的合格线）

- **构建必须过，红必须红在运行期**：断言失败或未实现桩（Java 的 `UnsupportedOperationException`、Rust 的 `todo!()`、Haskell 的 `error`、Python 的 `NotImplementedError` 等，见 构建约定（项目垫片 CLAUDE.local.md））。构建失败（编译型语言的编译、动态语言的加载/导入）不是红态，是骨架没落对——按 spec 2.1 修骨架，不是改 spec、更不是先写实现。
- 红的位置要正确：每条 AC 的测试红在它自己断言的行为上。一个 AC 因为前置 AC 挂掉而连坐变红，说明测试之间有隐藏依赖，拆开。

## 测试质量（每条测试逐一自检）

- **测在接口上**：只经 spec 2.1 的公开接口驱动与观察。测私有成员、mock 内部协作者、绕道数据库侧门验证——都是实现耦合，重构一动测试就碎。判据：改实现不改行为，测试不该红。
- **期望值来自独立真源**：spec 的字面例、手算值、失败归属表的固定关键词。用被测代码同款算法现推期望值是套套逻辑——它构造性地永真，永远抓不到 bug。独立真源即禁知的特例：期望值旁注出处（spec 节号 / AC 编号 / 手算过程），出处注释是 reviewer 的查验对象。
- **失败归属逐行成测**：spec 2.3 的每一行至少一个测试，断言异常类型与机械判定依据（如消息含参数名），让判责本身被验收。
- **一条 AC 一组测试**，命名读起来像 spec 复述（`refillSemantics`、`failureAttribution`）。不为想象中的行为囤测试——spec 没写的行为没有测试资格。

<!-- 测试质量纪律精编自 mattpocock/skills 的 tdd（MIT）：实现耦合、套套逻辑、水平切片三反模式。 -->
