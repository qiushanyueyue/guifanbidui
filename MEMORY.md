# 项目记忆索引

> `last_updated: 2026-08-25`
> 本文件是跨对话的紧凑入口，不替代实时核验。启动顺序见 [`AGENTS.md`](AGENTS.md)。

## 当前一句话

这是一个数据库优先、来源可追溯、无法核验即保持 `unknown` 的建筑工程规范查新工具；生产入口为 [guifan.108923.xyz](https://guifan.108923.xyz)。

## 当前关键事实

- 生产与数据快照：见 [`docs/project-memory/CURRENT.md`](docs/project-memory/CURRENT.md)，快照日期 `2026-08-25`。
- 当前远端主线：`origin/main` 与 `origin/feat/standards-v2-rebuild` 均为 `4556b15`（需在新任务中实时复核）。
- 已验证数据：1738 条；213 `current`、18 `abolished`、1507 `unknown`、0 `conflict`。
- 最近验证基线：后端 103 项（含 3 项记忆合同测试）、前端 11 项、黄金案例 50 项通过；桌面和 390×844 手机流程已实测。
- 普通搜索数据库-only；搜建筑与工标网证据随记录返回，不在普通请求中现场爬取。
- DeepSeek V4 Flash 是显式开启的服务端兜底：仅当本地零提取时才发送该段输入；不得用于涉密或完整内部文档。

## 不可忘记的风险

- 1507 条 `unknown` 不是现行结论。
- `RFJ 02-2009`、`DB/T 29-176-2016`、`DB 29-20-2017`、`GB 50046-2018` 仍需更多来源核验。
- 搜建筑和工标网属于第三方证据，正式引用应回到发布机构原文。
- `PROJECT_HANDOFF.md` 与 `PROJECT_SUMMARY.md` 含历史架构描述，不能覆盖当前纲领和事实快照。

## 按需检索

- 项目使命与不变量：[`docs/PROJECT_CHARTER.md`](docs/PROJECT_CHARTER.md)
- 当前运行事实与证据：[`docs/project-memory/CURRENT.md`](docs/project-memory/CURRENT.md)
- 历史变更：[`docs/project-memory/HISTORY.md`](docs/project-memory/HISTORY.md)
- 长期决策：[`docs/project-memory/decisions/`](docs/project-memory/decisions/)
- WorkBuddy 契约：[`docs/workbuddy.md`](docs/workbuddy.md)
- 数据质量证据：[`artifacts/`](artifacts/)

## 更新规则

耐久变更必须同步更新 `CURRENT.md`、追加 `HISTORY.md`，必要时新增 ADR，并刷新本摘要。禁止写入秘密、完整用户文档和未经证实的结论。最后运行：

```bash
python scripts/check_project_memory.py
```
