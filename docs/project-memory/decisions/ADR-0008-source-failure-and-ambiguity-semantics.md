# ADR-0008：查新区分来源失败、确实没有与多候选

- status: `accepted`
- date: `2026-11-11`
- owners: 项目维护者与代码代理
- refines: [`ADR-0006`](ADR-0006-live-lookup-budget-and-negative-cache.md) 的负缓存与预算

## 背景

2026-11-10 的下游问题清单（图纸随手查 88 条引用无结论）证实：查询时发现把所有来源错误（验证页、限流、解析失败）静默吞掉，与“查完了没有”一样记成 `miss` 并负缓存 24 小时；编号不写年份时按编号匹配全部落空；只给名称时会把库里旧版本的“已废止”报给引用。CSRES 搜索结果混入图书（ISBN）行时，解析器整页报错，真实规范也被丢掉。

## 决定

- 来源结果分为：`found`、`miss`（所有被查询的来源都正常回答且没有）、`source_unavailable`（有来源失败）、`budget_exhausted`（预算耗尽）、`ambiguous`（编号缺年份，来源列出同一系列多个年份）。未配置的适配器（`SourceNotConfigured`）和不存在的详情页（`NotFound`）不算来源失败。
- 负缓存按结果分级：`miss`、`ambiguous` 用 `LIVE_LOOKUP_RETRY_HOURS`（默认 24 小时）；`source_unavailable`、`budget_exhausted` 用 `LIVE_LOOKUP_FAILURE_RETRY_MINUTES`（默认 30 分钟）。清理阈值取两者较大值。
- 对外：来源失败返回 `match_type=source_unavailable`；多候选返回 `ambiguous` 并给 `candidates`（本地）或在 `message` 列出来源编号；均不返回 `not_found`，顶层 `status=unknown`。
- 编号缺年份：本地按前缀+序号（GB/GB-T 互为别名）匹配，唯一时采用并返回 `code_incomplete`；多个时返回 `ambiguous`，给了名称且名称唯一确定时采用该条。来源发现同理，只接受唯一年份。
- 只给名称或编号缺年份时，命中已停用且没有替代信息的记录，返回 `version_unconfirmed`，不得判为已废止；有替代信息时仍报替代。`code_mismatch` 与 `version_unconfirmed` 的顶层 `status` 为 `unknown`，`result.status` 只描述被匹配记录本身。
- 名称回退取最多 5 条，按标准去重；有多个且无编号可区分时返回 `ambiguous`。
- 查询时预算默认由 8 秒调为 15 秒，前端请求超时由 20 秒调为 30 秒。
- CSRES 搜索表中编号无法解析的行（如图书 ISBN）跳过；没有任何有效行时仍报结构变化。

## 替代方案

- 来源失败完全不缓存：被封 IP 时每个请求都会立即重新访问来源，放大请求；采用 30 分钟短窗口。
- 编号缺年份时取最新年份：库或来源结果可能不全（实测 CSRES 首页只列出 GB 9286-1988），会把旧版当成引用版本，不采用。

## 后果

- 下游需要处理 `source_unavailable`、`ambiguous`、`code_incomplete`、`version_unconfirmed` 四个新值；契约见 `docs/workbuddy.md`。
- 生产中 2026-11-11 前写入的 `miss` 记录可能其实是来源失败，最多 24 小时后自然过期。

## 复核条件

- 来源长期失败（`source_unavailable` 比例高）时，评估是否需要可用的第二来源，而不是延长窗口。
