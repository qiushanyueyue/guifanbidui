# 项目记忆索引

> `last_updated: 2026-10-03`
> 本文件是跨对话的紧凑入口，不替代实时核验。启动顺序见 [`AGENTS.md`](AGENTS.md)。

## 当前一句话

这是一个以明确判断规范是否可用为第一核心价值的建筑工程规范查新工具；主查询采用新鲜缓存 → 官方源 → 工标网/搜建筑精确匹配（双源一致升级交叉核验）→ 历史数据库 → 用户反馈，异常才显示“暂无法确认”；生产入口为 [guifan.108923.xyz](https://guifan.108923.xyz)。

## 当前关键事实

- 生产与数据快照：见 [`docs/project-memory/CURRENT.md`](docs/project-memory/CURRENT.md)，快照日期 `2026-10-03`。
- 发布前生产提交为 `fe05a8a`；本任务第一批可靠性优化尚待 GitHub CI/Vercel 发布验收，实时阶段见 CURRENT.md。
- 2026-10-03 只读生产复核：1743 条；549 current、37 abolished、1157 unknown、0 conflict。最近 CSRES 25/25 ParseError，随后关系质量门失败；不得称数据管线健康。
- 本轮前端 14 项、lint/build 和隔离 SQLite 黄金案例 50/50 通过；完整后端基线与发布证据见 CURRENT.md。
- 新增 data health、run-id 批次质量门、隔离 SQLite/PostgreSQL CI；只允许 GB↔GB/T 搜索别名，显式版次优先。语义见 [ADR-0004](docs/project-memory/decisions/ADR-0004-sync-health-and-ci.md)。
- 版次不得早于规范编号年份；同序号、同年份的 `GB`↔`GB/T` 及“规范”→“标准”作为引用身份演进命中并返回修正建议。
- `/api/v1/verify` 对生产持久数据库中超过默认 30 天或异常的记录自动有界联网复核；其余列表搜索仍以数据库为主。
- 官方明确状态直接定案为 `official`；官方不可用时，工标网或搜建筑单源完整匹配且明确状态形成 `single_source`，两站一致升级为 `cross_verified`。编号、名称完整匹配的引用单独显示“完全一致”，不再被未知状态降为“待核验”。
- DeepSeek V4 Flash 是显式开启的服务端兜底：仅当本地零提取时才发送该段输入；不得用于涉密或完整内部文档。

## 不可忘记的风险

- 生产仍有 1157 条 `unknown`；漏收补查、单源明确结论及“完全一致”已部署，正常规范明确判断率 ≥95% 仍需继续批量验收。
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
