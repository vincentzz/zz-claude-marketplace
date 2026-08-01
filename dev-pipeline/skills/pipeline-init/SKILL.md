---
name: pipeline-init
description: 幂等地为当前项目初始化流水线（装载垫片、构建约定审讯、状态播种、环境自检）。architect 启动自检发现项目未初始化、或用户要求"给这个项目上流水线 / init pipeline"时使用。
---

# 项目初始化（幂等）

本 skill 把"项目接入流水线"收敛为一份机械检查清单：**每项存在即跳过，缺失才补，重复运行零副作用**。修复只做加法（新建文件、追加行），永不改写项目已有内容——项目自己的 CLAUDE.md、settings.json 一个字节不碰。

## 检查清单（按序执行）

1. **git 仓库**：项目根有 `.git/`？没有 → 停，问用户（流水线的一切判责都长在 git 上）。
2. **协议就位（含升级刷新）**：`~/.claude/pipeline/PROTOCOL.md` 存在且首行版本号 == 本 plugin 版本？
   缺失或版本落后 → 从 plugin 的 `pipeline/PROTOCOL.md` 拷贝并在首行注 `<!-- dev-pipeline vX.Y.Z -->`；
   statusline 脚本、pipeline-local.sh 同法同步到 `~/.claude/pipeline/`（垫片 import 稳定路径，不指 plugin 缓存——升级重装不断链）。
3. **装载垫片**：`CLAUDE.local.md` 含逐字一行 `@~/.claude/pipeline/PROTOCOL.md`？
   - 文件不存在 → 创建；存在但缺该行 → 追加（它是用户的个人文件，追加合法）。
4. **构建约定块**：垫片内含齐四项——语言基线、全量测试命令、任务测试选取机制、未实现桩？缺任一项 → 进入**构建约定审讯**（见下）。
5. **状态播种与排除守护**：跑一次 `taskctl list`——它自播种 `tasks/task.html`、自写 `.git/info/exclude`（既有机制，勿重复造轮子）。
6. **环境自检**：`~/.claude/settings.json` 含 statusLine 与 attribution 键？缺则按 `pipeline/settings.reference.json` **只增不改**地写入（既有键一律不动）。

## 构建约定审讯（grill 分工：事实自查，决策拍板）

先探测项目根的构建文件，据下表拟推荐答案，再**逐项摆给用户拍板**——一次一项、附一句理由，用户可以只回"是/改成 X"：

| 探测到 | 推荐：全量测试 | 推荐：任务选取 | 推荐：未实现桩 |
|---|---|---|---|
| pom.xml | `mvn -q test` | JUnit5 `@Tag("task-<id>")` + `-Dgroups` | 抛 `UnsupportedOperationException` |
| build.gradle(.kts) | `./gradlew test -q` | JUnit5 `@Tag` + `-DincludeTags` | 同上 |
| Cargo.toml | `cargo test -q` | 测试名前缀 `task_<id>` | `todo!()` |
| *.cabal / stack.yaml | `cabal test` / `stack test` | tasty `--pattern "task-<id>"` | `error "not implemented"` |
| build.zig | `zig build test` | 测试名前缀过滤 | `@panic("not implemented")` |
| rebar.config | `rebar3 eunit` | 模块/组命名圈定 | `error(not_implemented)` |
| package.json | 按 test runner 定 | vitest/jest `-t "task-<id>"` | `throw new Error(...)` |
| 多个/皆无 | 事实列给用户，全部人工拍板 | | |

拍板结果写入垫片的构建约定块。完成判据：四项齐全 + 向用户复述一遍取得确认 + `taskctl list` 跑通。

## 边界

不碰项目已有的任何被跟踪文件；对 `~/.claude/` 只做幂等加法（协议/脚本同步与 settings 缺键补写）；同一项目重复 init 的合法输出是"已初始化，无事可做"。
