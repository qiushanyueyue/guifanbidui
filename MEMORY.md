# 项目记忆索引

> `last_updated: 2026-10-31`
> 本文件是跨对话的紧凑入口，不替代实时核验。启动顺序见 [`AGENTS.md`](AGENTS.md)。

## 当前一句话

这是一个以明确判断规范是否可用为第一核心价值的建筑工程规范查新工具；主查询采用新鲜缓存 → 官方源 → 工标网/搜建筑精确匹配（双源一致升级交叉核验）→ 历史数据库 → 用户反馈，异常才显示“暂无法确认”；生产入口为 [guifan.108923.xyz](https://guifan.108923.xyz)。

## 当前关键事实

- 生产与数据快照：见 [`docs/project-memory/CURRENT.md`](docs/project-memory/CURRENT.md)，快照日期 `2026-10-31`。
- CSRES 来源修复已通过 PR #3 合并，功能提交 `0b2f924` 在 Vercel Ready，正式域名和公开 API 回归通过；PR/分支/main 三组 CI 全绿。自然生产同步与实际关系重建仍待核验，后续文档提交不改变功能。
- 2026-10-31只读生产复核：1809条；1240 current、386 unknown、0 conflict。服务和数据库正常，但 `data=degraded`；CSRES 最近批次成功，其他来源仍为 never，不得称数据管线完全健康。
- 第一批后端147项、前端14项、lint/build，隔离 SQLite/PostgreSQL 迁移与黄金案例通过；GitHub 三组 CI 全部通过，main 要求三项检查，管理员也执行。CSRES 修复后本地后端176项通过；本轮 CI/部署证据见 CURRENT。
- 已部署 data health、run-id 批次质量门、隔离 SQLite/PostgreSQL CI；只允许 GB↔GB/T 搜索别名，显式版次优先。语义见 [ADR-0004](docs/project-memory/decisions/ADR-0004-sync-health-and-ci.md)。
- CSRES 作为主要覆盖/状态来源、搜建筑辅助、官方公告补充权威变更，见 [ADR-0005](docs/project-memory/decisions/ADR-0005-csres-coverage-and-verification-rotation.md)。本轮修复空结果误报、中文查询编码、全字段表头映射与详情身份校验；日/周 unknown 用独立编号游标轮转，避免队首饥饿。历史证据重放不刷新核验时间，成功重新抓取才刷新。源码/真实抽查通过不等于下一次生产批次已验收。
- 批量查新已实现最多4条并发，保留逐行结果与错误隔离；前端17项测试/lint/build和本地五条流程通过，9次新鲜缓存API抽测25091ms→8360ms。PR #5已合并，功能de2001c已在Vercel Ready并通过正式页面验收；CI/上线证据见CURRENT，抽样速度不代表过期联网复核。
- 2026-10-24 PR #7/#8 均已合并，最终 main 为 `6e535f9`，Vercel 生产部署成功且正式域名已验收。verify 联网共享默认8秒预算、查询时不重试；`live_lookup_attempts` 负缓存24小时内不重复联网且不刷新核验时间；前端20秒超时并丢弃过期轮次结果，并补齐匹配身份、接口加固、搜索页优先和仓库清理。见 [ADR-0006](docs/project-memory/decisions/ADR-0006-live-lookup-budget-and-negative-cache.md)。
- 2026-10-31 PR #10 的功能提交为 `20e94da`，Vercel `dpl_6SGVU6u8BaxNBipY4hAVU8Bbehhr` 为 Production/READY，正式域名验收时已指向该部署。来源结果仅在持久化成功后记录 `found`，持久化失败不写负缓存；写入时清理过期尝试行，并为 `attempted_at` 补索引。后端204项、main CI、正式 API 和重复查新实测通过。后续 PR #11 是仅文档提交，可继续推进 `main` 和 Vercel 部署 ID，但不改变运行代码。
- 版次不得早于规范编号年份；同序号、同年份的 `GB`↔`GB/T` 及“规范”→“标准”作为引用身份演进命中并返回修正建议。
- `/api/v1/verify` 对生产持久数据库中超过默认 30 天或异常的记录自动有界联网复核；其余列表搜索仍以数据库为主。
- 官方明确状态直接定案为 `official`；官方不可用时，工标网或搜建筑单源完整匹配且明确状态形成 `single_source`，两站一致升级为 `cross_verified`。编号、名称完整匹配的引用单独显示“完全一致”，不再被未知状态降为“待核验”。
- DeepSeek V4 Flash 是显式开启的服务端兜底：仅当本地零提取时才发送该段输入；不得用于涉密或完整内部文档。

## 不可忘记的风险

- 生产的发布质量门仍是先提交后校验；本地修复（ADR-0007，未部署）上线后，2条异常关系修复前定时发布会被阻塞。
- 2026-10-24 安全审查：公开 GitHub 历史仍含一处早期硬编码的 DeepSeek 风格密钥候选。当前树与本次 PR 未检出，但不能视为未泄露；应按真实凭据处理，立即轮换，并以受控流程清理所有分支历史。GitHub Secret Scanning 当前关闭。
- 查询时复核已部署为 CSRES 搜索页优先（详情页12–20秒、搜索页约3秒），搜索页不含替代关系，替代关系仍靠定时同步详情页刷新；搜建筑当前返回真人验证页，按自动化取证不可用处理且不得绕过。人工可在浏览器处理验证，但当前服务端查询不会复用该人工会话。
- 生产仍有386条`unknown`，`data=degraded`；漏收补查、单源明确结论及“完全一致”已部署，正常规范明确判断率 ≥95% 仍需继续批量验收。
- 已部署版本仍有8秒联网预算为软上限的已知风险；负缓存误记与尝试表过期清理已随 PR #10 部署。
- `RFJ 02-2009`、`DB/T 29-176-2016`、`DB 29-20-2017`、`GB 50046-2018` 仍需更多来源核验。
- 搜建筑和工标网属于第三方证据，正式引用应回到发布机构原文。
- 正常 CSRES 未命中仍需其他来源补证，不得转为 current。官方适配器和新规范列表发现仍未接通；三条历史反向关系已证实为跨分号的强条废止通知误解析，parser已修复，生产派生边待下一次发布重建核验。
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
