# 当前事实快照

- snapshot_id: `2026-10-03-csres-production-code-acceptance`
- as_of: `2026-10-03T19:01:58+08:00`
- verification: `production_code_verified; natural_sync_pending`
- scope: `qiushanyueyue/guifanbidui` 与 `https://guifan.108923.xyz`
- evidence_policy: 当前代码/测试和当日只读生产检查分开记录；新证据替代旧数量和部署快照，历史保留在 HISTORY.md。

## 仓库与部署

- as_of: `2026-10-03T19:01:58+08:00`
- verification: `production_code_verified`
- evidence: GitHub CLI/API、Vercel deployment metadata、公网只读 API。

- CSRES 修复通过 [PR #3](https://github.com/qiushanyueyue/guifanbidui/pull/3) 合并，已验收功能提交为 `0b2f924272a940514cd623ee729258367c2c9242`；后续验收文档提交不改变功能。
- 功能生产部署 `dpl_B3ta7CYbB993EoKib1DkNYePv2Sn` 为 Ready，Git 元数据对应上述 main 提交，域名 `guifan.108923.xyz` 已指向该部署。
- PR CI `37117904991`、分支 CI `37117903204` 和 main CI `37118159605` 的 backend/frontend/postgres-smoke 全部通过；前端测试、lint/build、隔离数据库迁移与黄金案例均实际执行。
- GitHub main 继续要求三项必过检查、严格最新分支和管理员约束，禁止 force-push/删除。CI 通过仍不表示下一自然生产同步成功。

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
- 最近生产 CSRES 批次全失败和现有替代关系质量门异常仍是修复前生产证据；本轮已修复抽样确认的零结果误报和中文请求编码，未宣称25条均为同一根因，也未重新触发生产批量同步。
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

## 2026-10-03 CSRES 来源与复核调度修复

- as_of: `2026-10-03T18:45:23+08:00`
- verification: `tested_local_and_live_source_reads`
- evidence: [公开来源7项直连抽查](../../artifacts/csres_source_probe_20261003.json)、真实元数据 fixture、来源/批次/轮转回归；部署与自然生产批次验收另行区分。

- GB 50009、GB 50010→GB/T 50010（2024年版）、GB 50016（2018年版）、废止的 GB 50010-2002、中文名称查询均取得正确搜索与详情；GB 51400-2020、建标143-2010明确零结果，不再 ParseError。仅公开元数据直连读取，不修改生产数据库。
- 建标 query 的 UTF-8 请求在 CSRES 被显示为乱码；gb18030 请求后中文正确，但抽查建标143仍未命中。响应的 GBK 解码在样本中正常，不混淆请求编码与响应解码。
- 全字段表头映射、完整身份最低门槛、正常空页/限流/验证页区分、搜索与详情身份一致性检查已实现；单源明确状态策略保持。
- 本轮完整后端176项通过，204个既有 datetime.utcnow 弃用警告（新增轮转测试增加调用次数）；未修改前端。
- 日/周 unknown-only 改为独立稳定编号游标轮转，失败也推进；月度进度独立，显式核验不移动自动游标。队列减少和末尾回绕有回归覆盖。
- CSRES 主覆盖、搜建筑辅助、官方公告权威事件补充见 [ADR-0005](decisions/ADR-0005-csres-coverage-and-verification-rotation.md)。新规范目录发现与官方适配器仍为后续工作；本轮不接入模型；三条关系原文已由当前公开CSRES页逐条证实并修复解析，生产边仍待下次发布重建。

- 证据时间修正：重建发布使用明确状态来源的真实观察时间，不再用重建时间伪造新鲜度；双源核验取两源各自最近观察中的较早时间，官方只取官方证据时间。成功重新抓取相同内容与在线复核才刷新观察时间，来源表随之同步；失败/未命中保留历史结论且不刷新核验时间。

## 2026-10-03 三条强条通知误解析关系

- as_of: `2026-10-03T18:52:58+08:00`
- verification: `production_readonly_and_live_source_verified; parser_and_pipeline_tested`
- evidence: [当前三条CSRES原文](../../artifacts/csres_relation_probe_20261003.json)、[已有生产关系图只读重算](../../artifacts/csres_relation_reparse_20261003.json)。
- 三条源规范为 JGJ 255-2012、JGJ 116-2009、CJJ 140-2010。CSRES原文以分号连接多个通用规范后共同引出“实施之日起，相关强制性条文废止”。旧parser先切分号，丢掉含“强制性”的后段，却把前段触发规范当作整本替代，产生3条反向年代边。当前公开源与生产保存原文一致。
- 已在切分号前移除完整条文通知；JGJ116的真正“替代JGJ116-1998”仍保留。3项原文解析和3项V2发布回归通过，强条状态仍为partially_repealed，未把规范整体改为废止。
- 只读重算已有生产派生关系图可移除三条假边，反向年代问题归零；这是既有图重算，不是完整生产发布验收。没有手工删除生产边、修改关系质量门或重跑批量同步。现有发布流程下次重建派生边时使用修复后的parser，实际发布结果待核验。

## 2026-10-03 CSRES 修复生产代码验收

- as_of: `2026-10-03T19:01:58+08:00`
- verification: `production_code_verified; natural_sync_pending`
- evidence: PR #3/main CI、生产 deployment metadata、公网 `/api/health`、`/api/stats`、三项普通搜索；部署限定 error/fatal 日志。
- 新部署公开服务 status/database=ok；数据仍为1743条、549 current、37 abolished、1157 unknown，data=degraded、最近失败率1.0。这是旧生产批次证据，未伪称本轮已恢复数据管线健康。
- GB 50010 与 GB/T 50010 普通搜索均命中相同2024年版；GB 50016显式2018版准确命中，未引发来源抓取或生产写入。
- 功能部署限定验收10分钟查询窗口没有 error/fatal 日志；不推广为长期无错误。
- 下一自然日批计划为2026-10-04北京时间10:17（GitHub调度可能延迟）；待核验真实抓取分类、队列推进、派生关系重建与质量门。没有手工删除旧关系、重跑同步或降低质量门。
- 7项公开来源搜索/详情和3条公开关系原文抽查通过，完整后端176项通过；抽样不证明全库完备。官方公告适配器和独立新规范发现仍未接通，本批无需大模型。
