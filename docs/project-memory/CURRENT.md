# 当前事实快照

- snapshot_id: `2026-10-03-first-batch-reliability`
- as_of: `2026-10-03T18:00:07+08:00`
- verification: `mixed`
- scope: `qiushanyueyue/guifanbidui` 与 `https://guifan.108923.xyz`
- evidence_policy: 当前代码/测试和当日只读生产检查分开记录；新证据替代旧数量和部署快照，历史保留在 HISTORY.md。

## 仓库与部署

- as_of: `2026-10-03T18:00:07+08:00`
- verification: `production_verified_before_release`
- evidence: GitHub CLI/API、Vercel CLI inspect、公网 API。

- 默认分支 main 当前远端为 `fe05a8a`；本任务分支为 `codex/first-batch-reliability`，第一批代码尚待 GitHub CI 和生产部署。
- Vercel 当前生产部署 `dpl_3696yR8JCBeBrmhiMW3rRKe6ZMsM` 为 Ready，现有域名未变。
- GitHub main 保护当前为 false；已有同步工作流最近运行失败，不能将存在工作流表述为同步成功。

## 数据快照

- as_of: `2026-10-03T18:00:07+08:00`
- verification: `production_verified`
- evidence: 公网 `/api/stats`、`/api/health` 与 GitHub run `37108632356` 的失败日志。

- 公开规范总数 1743；549 current、37 abolished、1157 unknown、0 conflict。
- 公网最近发布时间 `2026-10-03T08:09:18.070866Z`；顶层服务/数据库为 ok。
- 官方 samr/mohurd/openstd 及 soujianzhu 的批次健康为 never；旧 health 将 csres 表示为 running，不能作为当前正在同步的证据。
- 2026-10-03 日批选取 25、失败 25，均记录 ParseError；随后 rebuild 的关系质量门报告 3 invalid_relation、3 reverse_chronology，退出 2。工作流失败不是仅由抓取监控引起。
- 本轮不写生产数据、不清理关系或重新执行生产同步。

## 当前行为不变量

- as_of: `2026-08-25T15:25:37+08:00`
- verification: `tested`
- evidence: 后端契约/回归测试与当日公网抽样。

- `/api/search` 与 `/api/standards/search` 继续以数据库查询为主；`/api/v1/verify` 已在生产持久数据库中对过期、异常或漏收记录执行有界联网复核。
- 本地解析支持无空格编号、全角括号、同行连续规范、版次、`RFJ`、`建标`、`DB/T` 与 `22G101-1`。
- DeepSeek 默认模型为 `deepseek-v4-flash`；仅在 `ENABLE_REMOTE_EXTRACTION=true`、服务端 Secret 存在且本地零提取时调用。
- 远程响应会过滤畸形编号；远程失败安全降级为空。
- WorkBuddy 只读接口不应接收图纸、完整设计说明或内部资料。

## 验证基线

- as_of: `2026-10-03T18:00:07+08:00`
- verification: `tested_local`
- evidence: 后端 pytest、前端 node tests/ESLint/Vite build、隔离 SQLite 迁移/seed/golden。

- 本轮完整后端 147 项通过；154 个既有 datetime.utcnow 弃用警告。
- 前端 14 项、ESLint、Vite build 通过。
- 隔离 SQLite 迁移连续两次通过；仓库 seed 的黄金案例 50/50，禁用联网复核。
- 目录审计 8 项通过，测试使用归档 raw_value 重建临时 Excel。原 7 项 FileNotFoundError 来自过时个人路径，不是业务回归。
- PostgreSQL CI、GitHub 发布和新生产接口尚待验证。

## 当前风险与未验证项

- as_of: `2026-10-03T18:00:07+08:00`
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
