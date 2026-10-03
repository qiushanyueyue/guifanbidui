# 当前事实快照

- snapshot_id: `2026-10-03-first-batch-reliability`
- as_of: `2026-10-03T18:09:54+08:00`
- verification: `production_verified`
- scope: `qiushanyueyue/guifanbidui` 与 `https://guifan.108923.xyz`
- evidence_policy: 当前代码/测试和当日只读生产检查分开记录；新证据替代旧数量和部署快照，历史保留在 HISTORY.md。

## 仓库与部署

- as_of: `2026-10-03T18:09:54+08:00`
- verification: `production_verified`
- evidence: GitHub CLI/API、Vercel CLI inspect、公网 API。

- 第一批功能通过 [PR #1](https://github.com/qiushanyueyue/guifanbidui/pull/1) 合并，已验收功能提交为 `f393a6e`；后续仅验收文档提交以 main 为准。
- 功能生产部署 `dpl_4v9ve9x4itjAvLvg78RjV8fMBixf` 为 Ready，Git 元数据对应 `f393a6e`，域名 `guifan.108923.xyz` 已指向该部署。后续文档部署不改变功能。
- GitHub main 已保护：backend/frontend/postgres-smoke 必须通过且分支须最新，管理员也执行检查，禁止 force-push/删除；单人维护不要求额外审批人。已有同步工作流最近运行失败，CI 通过不表示生产同步成功。

## 数据快照

- as_of: `2026-10-03T18:09:54+08:00`
- verification: `production_verified`
- evidence: 公网 `/api/stats`、`/api/health` 与 GitHub run `37108632356` 的失败日志。

- 公开规范总数 1743；549 current、37 abolished、1157 unknown、0 conflict。
- 公网最近发布时间 `2026-10-03T08:09:18.070866Z`；顶层服务/数据库为 ok。
- 官方 samr/mohurd/openstd 及 soujianzhu 的批次健康为 never；新 health 将 csres 正确表示为 partial；旧 running 标签已被新证据取代。
- 2026-10-03 日批选取 25、失败 25，均记录 ParseError；随后 rebuild 的关系质量门报告 3 invalid_relation、3 reverse_chronology，退出 2。工作流失败不是仅由抓取监控引起。
- 本轮不进行生产数据治理、不清理关系、不重新触发生产同步；页面验收使用现有新鲜缓存。

## 当前行为不变量

- as_of: `2026-10-03T18:09:54+08:00`
- verification: `tested`
- evidence: 后端契约/回归测试与当日公网抽样。

- `/api/search` 与 `/api/standards/search` 继续以数据库查询为主；`/api/v1/verify` 已在生产持久数据库中对过期、异常或漏收记录执行有界联网复核。
- 本地解析支持无空格编号、全角括号、同行连续规范、版次、`RFJ`、`建标`、`DB/T` 与 `22G101-1`。
- DeepSeek 默认模型为 `deepseek-v4-flash`；仅在 `ENABLE_REMOTE_EXTRACTION=true`、服务端 Secret 存在且本地零提取时调用。
- 远程响应会过滤畸形编号；远程失败安全降级为空。
- WorkBuddy 只读接口不应接收图纸、完整设计说明或内部资料。

## 验证基线

- as_of: `2026-10-03T18:09:54+08:00`
- verification: `tested_local_and_github_ci`
- evidence: 后端 pytest、前端 node tests/ESLint/Vite build、隔离 SQLite 迁移/seed/golden。

- 本轮完整后端 147 项通过；154 个既有 datetime.utcnow 弃用警告。
- 前端 14 项、ESLint、Vite build 通过。
- 隔离 SQLite 迁移连续两次通过；仓库 seed 的黄金案例 50/50，禁用联网复核。
- 目录审计 8 项通过，测试使用归档 raw_value 重建临时 Excel。原 7 项 FileNotFoundError 来自过时个人路径，不是业务回归。
- GitHub PR CI `37115122521` 与 main CI `37115279046` 的 backend/frontend/postgres-smoke 全部通过；PostgreSQL 迁移两次及 seed 黄金案例实际通过。

## 2026-10-03 生产回归

- verification: `production_verified`
- evidence: Vercel deployment metadata、公网只读 API、实际浏览器提取并查新、部署限定 error/fatal 日志。

- 普通搜索 `GB 50010-2010` 和 `GB/T 50010-2010` 均返回同一条 GB/T 50010-2010（2024年版）；GB 50016-2014（2018年版）仍准确命中2018版；GB 50009-2012 返回无错误版次的原始版本。
- health 顶层 status/database=ok；data=degraded，unknown_rate=0.6638、latest_sync_failure_rate=1.0，reasons 包含 high_unknown_rate/unhealthy_latest_sync；服务与数据质量不再混淆。
- 页面输入 GB 50009/50010/50011 三条后，完全一致 1、属性修正 2、未找到 0；两条修正仍提示采用 GB/T 与2024年版，没有把 alias 冒充完全一致。
- 浏览器 error/warn 为0；功能部署限定的验收10分钟窗口无 error/fatal 日志，不能推广为长期无错误。

## 当前风险与未验证项

- as_of: `2026-10-03T18:09:54+08:00`
- verification: `mixed`
- evidence: 同步日志、公开状态数量、官方适配器代码。

- 1157 条 unknown 仍需来源治理，不能直接转为 current。
- 最近 CSRES 批次全失败和现有替代关系质量门异常尚未修复；新监控不会将它们伪装为健康。
- 官方适配器仍是解析框架；本轮不宣称 MOHURD/SAMR/OpenStd 已连通。
- `RFJ 02-2009`、`DB/T 29-176-2016`、`DB 29-20-2017`、`GB 50046-2018` 仍需更多来源证据。
- 既有 datetime.utcnow 弃用警告保留，未扩大本轮为时间 API 重构。

## 当前查新判定策略

- 主查询顺序及隐私边界维持 ADR-0003；普通搜索只读取数据库。
- 第一批新增共用 GB↔GB/T 身份查询，显式版次优先，引用属性修正继续由 matcher 负责。
- 数据健康、批次失败率、CI 隔离与阈值语义见 [ADR-0004](decisions/ADR-0004-sync-health-and-ci.md)。
- `/api/health` 原 status/database/last_sync/sources 字段保持，新 data 区分覆盖率和同步异常；不把服务可用等同于全库核验。

## 下一次任务首先复核

1. GitHub CI 与 main 当前提交、Vercel 域名对应部署。
2. 公网普通搜索的 GB/GB-T 与版次行为、data health。
3. 本次来源批次、替代关系异常与当前 unknown 数量。
