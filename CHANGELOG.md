# Changelog
## 0.9.4
- Both plugins now ship `defaultEnabled: false` (Claude Code ≥2.1.154): installing no longer enables them everywhere. Enable per project with `claude plugin enable <name>@zz-claude-marketplace --scope local`. Existing installs are unaffected (an explicit `enabledPlugins: true` written at install time still wins over `defaultEnabled`).

## 0.9.3
- architect/dev/dev-reviewer now use the user's and project's own installed skills: dev-reviewer gains the Skill tool (it previously could not see any non-preloaded skills); all three roles get a discipline for applying installed convention/library skills — project conventions outrank generic style, the spec outranks everything; architect names applicable skills in dev dispatch prompts. Both dev-pipeline and dev-pipeline-cn.

## 0.9.2
- Renamed the original (Chinese) plugin to **dev-pipeline-cn**; **dev-pipeline** is now the English translation of the same pipeline. Existing installs of `dev-pipeline@zz-claude-marketplace` will switch to the English version on marketplace update — install `dev-pipeline-cn` to stay on the Chinese one. Enable only one of the two (same agent names).

## 0.9.1
- architect 新增「收报即收摊」通则：处理完 qa/dev 完成报告后随手 TaskStop 已交接的空闲子代理，重派一律唤起新实例。

## 0.9.0（未跑过真实任务的初始版）
- 五角色 + 12 skills + taskctl 机械层完整；语言无关；用户级/项目级双态收敛为 plugin 分发。
- 已知欠账：事件账本未建；评审死锁路径未协议化；全套未经真实任务检验——先跑三个任务再加任何东西。
