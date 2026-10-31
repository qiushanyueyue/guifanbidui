# 项目记忆历史

> append-only：只能追加新条目；发现旧事实错误时追加更正，不重写或删除旧条目。禁止记录 Secret、认证过程和完整用户文档。

## 2026-08-25 — 第三方状态依据与 unknown 优先核实

- event_id: `2026-08-25-third-party-status-and-unknown-priority`
- status: `tested`
- scope: 搜建筑/工标网状态证据、V2 unknown 分批核实、来源解析与自动化路由。
- result:
  - 接受搜建筑或工标网身份匹配且明确显示的状态作为 `single_source` 运行判定依据；另一来源确认身份且不冲突时可形成 `cross_verified`。
  - 仅收录、真人验证、来源失败或状态缺失仍保持 unknown；第三方冲突仍保持 conflict，正式引用仍回到发布机构原文。
  - 搜建筑解析器开始保存页面明确状态；日/周任务优先处理当前 unknown，月度任务继续复查全部候选。
  - 本地抽样核实10个 unknown 编号，6个取得工标网精确记录、4个解析失败；V2质量门禁通过，本地 current 由213增至214、unknown由1507降至1506。其余5个成功结果属于独立修订版，未把原始无版次身份强行改成现行。
  - 结果页来源按钮缩为桌面84×36并统一视觉，移动端保留44px点击高度；双空字段提取项在查询和展示前过滤。
- evidence: 第三方状态与冲突目标测试、Soujianzhu fixture 解析测试、V2 自动化合同测试。
- remaining_risk: 搜建筑实时页面当前触发真人验证，无法以无交互 HTTP 批量取得状态；AGY CLI 在项目映射修复后仍无诊断退出，前端由主代理完成；代码与工作流尚未推送或生产实测，1507 条生产 unknown 尚未因此改变。

## 2026-08-25 — V2 数据库、真实解析、界面与生产验收

- event_id: `2026-08-25-v2-production-acceptance`
- status: `production_verified`
- scope: 数据清洗、查新判定、真实文本解析、响应式界面、DeepSeek零结果兜底、生产部署。
- result:
  - 数据库发布为1738条；213 current、18 abolished、1507 unknown、0 conflict。
  - Excel目录补充候选和规范性文件，无法核验的记录保持 unknown。
  - 修复 `G B`、跨行版次串联、`22G101-1`、同行连续条目；真实说明33/33。
  - 空结果区、移动端溢出、导出弹窗和搜建筑/工标网96×44按钮完成浏览器验收。
  - DeepSeek V4 Flash配置为服务端可选兜底；本地有任何结果时不调用远程。
  - GitHub仓库为Public，远端main与功能分支同步至`4556b15`，Vercel生产Ready。
- evidence:
  - `100 passed` backend、`11 passed` frontend、`50/50` golden。
  - 公网 `/api/health`、`/api/stats`、`/api/extract`、`/api/v1/verify`。
  - Playwright 1440×900、390×844 实际流程。
- supersedes:
  - `PROJECT_HANDOFF.md` 与 `PROJECT_SUMMARY.md` 中“普通查询实时爬取、Gemini增强、SQLite生产缓存”等旧描述。
- remaining_risk: 1507条unknown与少数Excel候选仍需更多来源，第三方结果不是官方结论。

## 2026-08-25 — 建立仓库级纲领与分层记忆系统

- event_id: `2026-08-25-project-memory-system`
- status: `tested`
- scope: 新对话入口、项目纲领、当前事实、追加历史、ADR、隐私边界与自动校验。
- result:
  - 新对话以 `AGENTS.md` 为强制入口，按需读取纲领、根记忆、当前快照、ADR和历史。
  - 耐久变更必须同步 `CURRENT.md`、追加 `HISTORY.md`、刷新 `MEMORY.md`；长期取舍使用 ADR。
  - 校验器检查必需文件、标题、本地链接、时间证据标记和常见秘密模式。
  - 已纳入本地提交 `854c74d`，保留用户原有脏工作树；未经授权不推送或触发生产部署。
- evidence: `python scripts/check_project_memory.py`、记忆合同测试 3 项、后端全量 103 项、前端 11 项、ESLint、Vite build、`git diff --check`。
- supersedes: 仅依赖会话上下文、过时交接文档或平台隐式记忆的方式。
- remaining_risk: 记忆不是实时数据源；新对话仍必须根据 `as_of` 和证据重新核验会漂移的事实。

## 2026-08-25 — 一致结果文案收敛

- event_id: `2026-08-25-exact-match-consistent-label`
- status: `tested`
- scope: 结果表批次汇总、业务判定与状态展示文案。
- result: `exact` 匹配统一显示“一致”，不再在同一条一致结果上显示“待核验”；数据库状态、核验级别和接口字段保持不变。
- evidence: 前端合同测试 13 项、ESLint、Vite build、`git diff --check`。
- remaining_risk: 尚未部署生产；生产界面仍需在部署后验收。

## 2026-08-25 — 明确结论与过期自动查新

- event_id: `2026-08-25-decisive-freshness-aware-verification`
- status: `tested`
- scope: 产品核心判定、官方/双第三方来源优先级、缓存新鲜期、查询时复核、修订引用与前端状态表达。
- result:
  - 第一核心价值改为明确判断规范是否可用，异常才显示“暂无法确认”，目标明确判断率不低于 95%。
  - `/api/v1/verify` 对生产持久数据库中的过期或异常记录按官方 → 工标网+搜建筑顺序有界复核；默认新鲜期 30 天，成功后写回来源证据缓存，失败则回退历史明确结论。
  - 官方明确状态直接定案；两第三方必须对身份、明确状态和替代关系一致才标记 `cross_verified`。
  - 规范状态与引用版本分离，版次和局部修订进入业务结论与推荐引用。
  - 前端一致记录显示“一致”，规范状态独立显示“现行/现行需修订/已废止/已被替代”。
- evidence: 后端 116 passed；前端 14 passed、ESLint、Vite build；本地浏览器 `GB 50016-2014` 缺版次及完整 2018 年版两条流程，控制台无错误。
- supersedes: ADR-0002 中普通查询数据库-only与正常记录保守展示 unknown 的部分；ADR-0003 成为当前决定。
- remaining_risk: 尚未部署生产或批量复核 1507 条生产 unknown；官方源机器解析仍未接通，搜建筑实时访问可能遇到真人验证，因此 ≥95% 目标尚未生产验收。

## 2026-09-01 — 漏收实时补查、单源明确结论与全文入口

- event_id: `2026-09-01-query-time-discovery-single-source-fulltext`
- status: `tested`
- scope: `/api/v1/verify` 本地漏收、单第三方来源判断、引用一致性、搜建筑跳转。
- result:
  - 查明生产工标网同步为 `partial`，既有脚本只复核库内候选，未完成工标网全目录采集；本地未收录记录此前会直接返回 `not_found`。
  - 本地未收录查询增加有界实时发现并写入 V2 缓存；`GB 50308-2017` 能发现正确的 `GB/T 50308-2017`，返回编号属性修正和现行状态。
  - 工标网或搜建筑任一来源完整匹配且明确显示状态即可形成 `single_source` 明确结论；双源一致升级 `cross_verified`。
  - 编号、名称完整匹配的引用显示“完全一致”，与规范状态字段分离；不再使用“待核验”作为正常匹配结论。
  - 搜建筑分页阅读链接统一为 `NormContent.aspx` 全文入口；真人验证由第三方站点控制，未绕过其验证机制。
- evidence: 生产 `/api/health`、`/api/stats`；工标网三条真实搜索；内存 V2 `/api/v1/verify` 流程；后端 120 项、前端 14 项、ESLint、Vite build 与本地浏览器两条用例。
- supersedes: `2026-08-25-exact-match-consistent-label` 的“一致”文案，以及 ADR-0003 中第三方必须双源才可给出明确状态的部分。
- remaining_risk: 修改尚未推送或部署生产；搜建筑真人验证无法保证不出现；部署后公网流程仍待验收。

## 2026-09-01 — 明确查新策略生产部署与幂等修复

- event_id: `2026-09-01-production-deploy-idempotent-discovery`
- status: `production_verified`
- scope: Vercel 生产部署、公网 API/浏览器验收、查询时发现幂等性与重复记录处置。
- result:
  - 提交 `3676dc3` 部署到现有 Vercel 项目后，截图三条流程已在 `guifan.108923.xyz` 实测通过。
  - 公网首次补查将 `GB 50308-2017` 明确识别为现行 `GB/T 50308-2017`；另外两条显示“完全一致/现行”，搜建筑链接为 `NormContent.aspx`。
  - 验收发现无名称输入可能重复写入发现记录；提交 `a8ac4f9` 增加按规范化发现编号复用记录，并再次成功部署。
  - 精确确认重复 ID `5506/5507` 后，将较早的 `5506` 标记为 `quarantined`，未物理删除；连续两次仅编号查询后总数稳定为 1741，公开搜索只返回一条。
- evidence: GitHub Vercel success；公网 `/api/health`、`/api/stats`、三条 `/api/v1/verify`；生产浏览器 DOM 与控制台；Neon 只读定位及条件更新返回值；后端 121 项、前端 14 项、ESLint、Vite build。
- supersedes: `2026-09-01-query-time-discovery-single-source-fulltext` 的“尚未部署”状态。
- remaining_risk: 搜建筑仍会按其风控跳转真人验证，无法由本站保证消失；生产仍有 1347 条 unknown，≥95% 明确判断率尚未整体达成。

## 2026-09-06 — 常用规范身份演进与不可能版次修复

- event_id: `2026-09-06-common-standard-identity-and-edition-fix`
- status: `production_verified`
- scope: 版次解析、V2 发布/读取、`GB`↔`GB/T` 身份命中、生产数据纠正与 Vercel 部署。
- result:
  - 不再把替代关系中旧规范的版次挂到当前规范；修订年早于编号年的记录不参与公开查询。
  - 同序号、同年份的 `GB`↔`GB/T` 类型变更可命中已有当前记录，名称从“规范”改为“标准”时给出完整推荐引用。
  - 生产三条同根因脏记录已标记 `quarantined`而未删除；保留记录经工标网重新查新后均为现行。
  - 提交 `ae0d538` 已部署原 Vercel 项目和 `guifan.108923.xyz`，真实页面的三条截图用例均达到预期。
- evidence: 住建部 2024 年第 61/62 号公告；工标网真实返回；Neon 条件更新；后端 126 passed；前端 14 passed、ESLint、Vite build；Vercel Ready；公网 API 和页面表格验收。
- remaining_risk: 实际 Excel 已移到 `/Volumes/yue/Download/文档/`，仓库个别本地集成测试仍硬编码旧路径；本次通过测试插件指向实际文件完成 126 项验证，未改动该测试基础设施。

## 2026-09-06 — 查新证据并发写入幂等修复

- event_id: `2026-09-06-live-evidence-staging-race-fix`
- status: `production_verified`
- scope: staging 证据写入的并发唯一键冲突处理、公网部署与错误日志观测。
- result: `stage_record` 在保存点内执行写入；另一请求同时创建相同证据时回退保存点并复用已有行，不回滚外层查新事务。提交 `ef323fe` 已部署；两请求并发查询均返回现行结论，部署后错误日志窗口为空。
- evidence: 后端 127 passed；Vercel 生产 Ready；公网并发 POST 验收；`vercel logs --environment production --level error --since 2026-09-06T22:59:09+08:00 --json` 无输出。
- remaining_risk: 历史 1 小时错误日志中保留了本次修复前的并发记录；新部署后观测窗口已清洁。

## 追加模板

```markdown
## YYYY-MM-DD — 简短事件名

- event_id: `唯一标识`
- status: implemented | tested | production_verified | partial | rolled_back
- scope: ...
- result: ...
- evidence: ...
- supersedes: 可选
- remaining_risk: ...
```


## 2026-10-03 第一批查询一致性、健康指标与 CI（本地验收）

- as_of: `2026-10-03T18:00:07+08:00`
- verification: `tested_local; production_readonly_verified`
- changes: 普通搜索与 get_by_code 共用 GB/GB-T/版次逻辑；新增兼容 data health 和原因；同步任务发布后按本次 run-id 检查，发布失败仍检查；新增隔离数据库 CI，目录测试改用归档原始行重放。
- evidence: 完整后端 147 项通过，前端 14 项/lint/build，SQLite 两次迁移与黄金案例 50/50；生产 1743/549/37/1157。
- invalidated: 旧 CURRENT 的 1738/374/28/1336 数量、记忆未推送及工作流未运行描述不再代表当前状态。日批 run 37108632356 已实际运行并失败：25/25 ParseError，rebuild 的关系质量门退出 2；不能用“工作流绿色”概括该现场。
- remaining: 第一批 GitHub CI、发布与生产回归待完成；来源解析与现有关系数据异常另行治理。本轮保留无关脏工作树。
- decision: [ADR-0004](decisions/ADR-0004-sync-health-and-ci.md)。


## 2026-10-03 首次 GitHub CI 环境差异修正

- verification: `ci_failure_reproduced_and_fixed_local`
- evidence: GitHub runs 37115002064/37115023519 的 backend collection 报 scripts 模块不存在；frontend 和 postgres-smoke 已通过。
- changes: CI 使用 `python -m pytest`，与本地已验证入口一致，让仓库根目录加入模块路径；不跳过测试、不增加运行依赖。
- remaining: 新提交实际 CI 待重新验证。


## 2026-10-03 第一批 GitHub 与 Vercel 生产验收

- as_of: `2026-10-03T18:09:54+08:00`
- verification: `production_verified`
- changes: PR #1 合并为 f393a6e；main 启用 backend/frontend/postgres-smoke 三项必过检查、严格最新分支和管理员约束。Vercel Git 自动发布，现有域名及 region 未换。
- evidence: GitHub PR CI 37115122521/main CI 37115279046 全部通过；生产功能部署 dpl_4v9ve9x4itjAvLvg78RjV8fMBixf=Ready 且 Git 元数据对应 f393a6e。普通搜索双向GB查询和2018版、health、stats实际通过；页面三条查新1完全一致/2属性修正/0未找到，浏览器无 error/warn；部署限定10分钟窗口无error/fatal日志。
- invalidated: 发布前“代码尚未推送/CI待验证/生产无data字段/main未保护”等阶段描述不再代表当前状态；首次CI失败通过python -m pytest修正后已实际全绿。
- remaining: CSRES 25/25 ParseError、已有3条替代关系质量异常、1157 unknown和官方适配器未接通仍存在。未为证明监控而触发生产同步，不将监控上线称为来源故障修复。后续验收文档提交不改变本次功能。

## 2026-10-03 CSRES 解析与来源复核轮转（本地/公开源验收）

- as_of: `2026-10-03T18:33:48+08:00`
- verification: `tested_local_and_live_source_reads`
- changes: 中文 keyword 用 gb18030 字节编码，正常空页不再误报 ParseError，所有搜索字段按表头映射，详情必须与搜索实际命中编号一致；日/周 unknown 使用独立稳定编号游标，失败也推进，月度与显式核验进度隔离。CSRES 保持主覆盖和明确状态来源，搜建筑辅助，官方公告补充权威事件。
- evidence: 侧边 GPT 两轮讨论与根因反馈；[7项公开源直连抽查](../../artifacts/csres_source_probe_20261003.json) 全通过；真实元数据 fixture；完整后端164项通过。原数据质量报告和其他用户已有文件未修改。
- invalidated: “25/25 ParseError说明CSRES整站解析接口失效”的推断不成立；建标143和GB51400样本为正常零结果。中文请求修复后建标143仍无命中。其他23条不据此强推同一根因。
- decision: [ADR-0005](decisions/ADR-0005-csres-coverage-and-verification-rotation.md)。
- remaining: 本轮GitHub CI/部署尚待验证；下一自然生产批次和历史关系原文治理未验收；官方适配器和新规范目录发现未接通。

## 2026-10-03 历史证据新鲜度修正与残余边界回归

- as_of: `2026-10-03T18:45:23+08:00`
- verification: `tested_local`
- changes: 实际代码发现 publish_staging 把重建时间当核验时间；改用明确状态来源的真实观察时间，双源新鲜度取较早观察、官方只取官方证据。成功重新抓取相同内容与在线核验同步暂存/来源时间，历史重放或未命中不刷新。
- evidence: 完整后端169项通过；新增未命中/失败保留历史状态与时间、双源旧证据、成功相同内容刷新、在线核验后重建不回退；详情串记录不泄漏日期/关系；自动工作流共享concurrency回归。
- remaining: 生产下一次自然批次和原关系质量异常仍未验收。

## 2026-10-03 三条生产关系原文逐条核实与解析修复

- as_of: `2026-10-03T18:52:58+08:00`
- verification: `production_readonly_and_live_source_verified; tested_local`
- changes: 对跨分号的完整强条废止通知先作整体处理，再解析真正替代关系；修复JGJ255/JGJ116/CJJ140误指向较新通用规范的三条边，保留JGJ116替代1998版的真实关系及强条部分废止状态。
- evidence: 三条当前CSRES公开详情与原生产保存证据一致；[原文抽查](../../artifacts/csres_relation_probe_20261003.json)全通过；[既有关系图只读重算](../../artifacts/csres_relation_reparse_20261003.json)三条假边消除，反向年代问题归零；完整后端176项通过。
- invalidated: 前阶段“关系原文尚未核实”已被实时只读与公开源证据取代；未将代码修复冒充生产派生边已更新。
- remaining: 生产下次自然发布实际重建及来源批次分布尚待核验；官方公告和新规范发现未接通。

## 2026-10-03 CSRES 修复 GitHub 与 Vercel 代码上线验收

- as_of: `2026-10-03T19:01:58+08:00`
- verification: `production_code_verified; natural_sync_pending`
- changes: PR #3合并为0b2f924，Vercel Git自动部署dpl_B3ta7CYbB993EoKib1DkNYePv2Sn=Ready，正式域名指向本次功能提交；后续仅验收文档不改变功能。
- evidence: PR CI37117904991、分支CI37117903204、main CI37118159605三组检查全部通过；公开health/stats与GB/GB-T、显式2018版搜索回归通过，部署限定验收日志无error/fatal。完整后端176项及10项公开源核对已通过。
- invalidated: 上线前“最新CI与Vercel待验收”阶段描述已被上述实时证据取代；生产最近失败批次和三条旧派生关系尚未被新批次重建，仍不能称数据管线健康。
- remaining: 下一自然同步的分类分布、轮转推进和派生边重建待实测；官方公告、新规范发现未接通。不新增模型、不手工删除生产数据、不重跑批次、不覆盖用户无关改动。

## 2026-10-04 批量查新有界并发与速度抽测

- as_of: `2026-10-04T23:34:39+08:00`
- verification: `frontend_tested; local_browser_verified; live_api_performance_measured`
- changes: 修复页面逐条await导致后续请求等待，批量提取查新/重新查新改为最多4条并发，完成一条即填充对应行。来源、新鲜期与业务判定规则不变。
- evidence: 前端17项行为/原界面测试、lint/build通过；本地五条流程完成3完全一致/2属性修正/0未找到。正式API同一9次新鲜缓存查询串行25091ms、并发8360ms，结果签名一致，约3倍；这是调度/API抽测，不是全场景页面延迟保证。
- remaining: 本轮最新CI、上线与正式页面待验收；自然日批已运行但仍失败，后续来源治理单独处理。

## 2026-10-04 并发查新 GitHub/Vercel 与正式页面验收

- as_of: `2026-10-04T23:40:11+08:00`
- verification: `production_code_and_browser_verified`
- changes: PR #5合并为de2001c，Vercel Git自动部署dpl_Z2e9oHX4zbvQ8eMFv3cAK8QBRiWt=Ready，正式域名对应本次功能；仅验收文档不改变功能。
- evidence: PR/分支/main CI37213549069/37213528679/37213627088三组检查全绿；正式页面提取GB50009/50010/50011并查新得到1完全一致/2属性修正/0未找到，浏览器error/warn为0，部署限定验收10分钟窗口无error/fatal日志。9次缓存API样本25091ms→8360ms，不外推为全场景速度保证。
- invalidated: 本轮“CI与上线待验收”已被实际证据取代；旧10月3日25/25失败与1157unknown不再是当前快照。今日只读公开快照554current/1upcoming/37abolished/1151unknown，来源批次失败率0.76、任务仍failure。
- remaining: 过期联网核验耗时仍受外部来源影响；自然批次失败和关系图实际重建另行核验，本次不扩大治理范围。

## 2026-10-24 查询时联网复核总时限、负缓存与前端过期结果丢弃

- event_id: `2026-10-24-live-lookup-budget`
- status: tested
- scope: `/api/v1/verify` 查询时发现与复核、`HttpSource` 请求循环、新表 `live_lookup_attempts`、前端 `api.ts`/`App.tsx`/`checkStandards.ts`。
- result: 每次 verify 共享默认8秒总预算（`LIVE_LOOKUP_BUDGET_SECONDS`），查询时适配器不重试，预算耗尽不再发请求；同一编号/名称在 `LIVE_LOOKUP_RETRY_HOURS`（默认24小时）内不重复联网，负缓存不改 `last_verified_at` 与状态证据。前端统一20秒超时（导出60秒），新一轮提取/查新/清空会取消旧请求并丢弃迟到结果。决策见 [ADR-0006](decisions/ADR-0006-live-lookup-budget-and-negative-cache.md)。
- evidence: 后端全量184项通过（新增8项），隔离SQLite迁移两次、seed导入1738条、黄金案例50/50；前端18项测试、ESLint、Vite build通过。本地服务对真实CSRES：GB 50038-2005 unknown首次复核0.67s升为current/single_source，重复查询8ms；漏收编号 GB 59999-2021 首次0.96s记为miss，重复查询6ms未联网。本地浏览器提取三条规范流程正常，无控制台错误；本地缓存请求毫秒级完成，浏览器中未能观察到取消中途请求，该行为由代码与单测覆盖。
- remaining_risk: 未提交、未部署，生产未验证；预算耗尽的真实比例、交叉核验比例变化和生产函数时限待上线后观察。

## 2026-10-24 审查后续：匹配判定、接口安全、查询次数与仓库清理

- event_id: `2026-10-24-review-followups`
- status: tested
- scope: 匹配判定、前端查新兜底、限流、公开同步状态、LIKE 搜索、负缓存容错、V2 结果查询、联网结果合并、`datetime.utcnow` 替换与调试文件清理。基于未合并的 PR #7 分支。
- result: 匹配先核身份再给状态：编号族不同或仅名称输入但名称不同时，返回 `code_mismatch`/`name_mismatch`，不再把模糊命中的另一条规范的废止/替代状态报给引用。前端不再在 verify 未找到后用无判定的模糊搜索结果兜底（服务端 verify 已按名称查过）。公开 `/api/sync/status` 不再返回 `error_message`。搜索对 `%`、`_`、`\` 转义。Vercel 上限流按平台写入的 `x-real-ip`/`x-forwarded-for` 计数，其他环境忽略这两个头，空闲 IP 按窗口清理；限流仍是单实例内存级。`live_lookup_attempts` 表缺失时查询降级为不使用负缓存。数据集选择每请求只探测一次，替代关系改为单次 join。新增 `app/timeutil.utc_now` 替换全部 `datetime.utcnow`。删除17个无引用的调试/复现/截图文件，保留 `test_connection.html`（启动说明引用）和旧数据脚本。
- evidence: 后端全量194项通过且0条警告（此前205条）；隔离 SQLite 迁移两次、seed 1738条、黄金案例50/50；前端18项、ESLint、Vite build 通过。本地浏览器三条规范：GB 50016 完全一致（需2018年版）、GB 50010 属性修正为 GB/T、GB 50099-2011 配错名称返回名称错误。
- finding: 本地对 seed 记录的查询时复核三条均为 `budget_exhausted`。直测 CSRES 详情页单次12–20秒、搜索页约3秒；已存详情 URL 时复核走详情页，8秒预算内无法完成（旧代码重试4次同样失败）。搜建筑详情页返回“真人验证”页，被解析为无效记录后因身份不符被忽略。
- remaining_risk: 未提交、未部署。查询时是否改为搜索页优先、预算是否放宽，待产品决定；搜建筑验证页应识别为来源不可用（不得绕过）。健康检查 5% unknown 阈值未改。

## 2026-10-24 查询时复核改为搜索页优先，识别搜建筑验证页

- event_id: `2026-10-24-search-first-live-check`
- status: tested
- scope: `live_verification._fetch_one`、来源关系一致性判定（查询时合并与 `v2_pipeline._status_decision`）、搜建筑解析。
- result: 查询时先查搜索页，未匹配且有剩余预算才查详情页；定时同步仍用详情页。缺少关系文本不再算关系不一致，发布重建只比较各来源最近一条明确关系文本。搜建筑验证页按来源不可用处理，不绕过。ADR-0006 已补充。
- evidence: 后端全量201项通过（新增7项）。本地服务对真实 CSRES（同一批此前全部 `budget_exhausted` 的记录）：GB 50016-2014（2018年版）3.0s exact、GB 50010-2010 1.9s 修正为 GB/T、GB 50099-2011 1.4s exact，均为 `found`/single_source 且刷新核验时间；重复查询8ms。
- supersedes: 同日“审查后续”条目中“8秒预算内均为 budget_exhausted”的发现已由本次修复处理。
- remaining_risk: 未部署、生产未验证；搜索页没有替代关系，查询时复核不刷新替代关系；搜建筑在验证页期间不能提供证据，交叉核验仍然很少。

## 2026-10-24 Claude 修复审查与公开历史凭据风险

- event_id: `2026-10-24-claude-review-security-audit`
- status: reviewed
- scope: PR #7/#8 代码、GitHub/CI/Vercel 状态、正式域名、当前工作树、全部可达 Git blob 与提交消息。
- result: 两个 PR 已推送且 CI/Vercel preview 通过，均未合并；正式域名仍运行 `main` 的 `1f367a2`，公开 `/api/sync/status` 仍返回 `error_message`，因此新代码没有上线。当前代码与本次提交未检出密钥，但公共 Git 历史中的 `backend/ocr_standards.py` 仍保留一处硬编码 DeepSeek 风格密钥候选，必须按泄露处理。
- evidence: 后端 201 项、前端 18 项、ESLint、Vite build 通过；main 为 `1f367a2`，PR #7 为 `7cc9696`、PR #8 为 `fd51ead`，均 open/mergeable，CI 与 Vercel preview 成功；正式域名可访问且数据快照更新，但接口字段证明代码仍是旧版。736 个可达 Git blob 中仅上述历史候选命中；当前树无候选，GitHub Secret Scanning 关闭。
- finding: 负缓存持久化顺序有缺陷：来源返回结果但 `persist_live_verification` 抛错时，`attempt_outcome` 仍记录 `found`，后续查询在 24 小时内跳过联网而状态保持 unknown。另有预算非严格墙钟上限及负缓存表无过期清理两个残留风险。
- remaining: 先轮换可能暴露的凭据并受控清理公共 Git 历史；修复负缓存写入语义和表清理后再合并/部署 PR 堆栈。未执行外部账号修改、历史重写、合并或生产部署。

## 2026-10-24 PR #7/#8 合并与正式域名部署验收

- event_id: `2026-10-24-review-deployment`
- status: deployed_and_production_verified
- scope: PR #7/#8 合入、最终 main CI、Vercel 生产部署、正式域名 API 验收、当前版本公网敏感文件探测。
- changes: PR #7 合并为 `c6ae788ae44b4c9a5e8632a1d8c23eba8b660501`；PR #8 同步最新 main 后 8 项 CI/Vercel 检查全绿并合并，最终 main 为 `6e535f9defee4a476387b5eacbdb26595fa67e8b`。合并提交 Vercel 生产状态为 success，正式域名已运行新代码。
- evidence: 最终 main push CI `40108281983` 的 backend/frontend/postgres-smoke 全通过。正式域名 `/`、`/api/health`、`/api/stats`、`/api/sync/status`、`/api/v1/verify` 均返回 HTTP 200；首页 0.63s，health 3.18s，stats 1.66s，sync status 1.43s，verify 1.87s。`/api/sync/status` 不再包含 `error_message`，证明 PR #8 接口加固生效。
- production_snapshot: 总数 1779；1036 current、16 upcoming、137 abolished、590 unknown、0 conflict；status/database=ok，data=degraded、unknown_rate=0.3316、latest_sync_failure_rate=0.0；最近同步 id=62，csres success，found/inserted 25/25。
- verify_probe: `GB 50016-2014` 返回 canonical/name `GB 50016-2014`/`建筑设计防火规范`，status=current、match_type=revision_missing、confidence=0.95、verification_level=single_source，提示“规范现行，但引用需采用2018年版”，来源记录 5 条。
- security_probe: 正式域名对 `.env`、`.env.production`、`.git/config`、`backend/.env`、`backend/.env.local` 均返回 404；当前 `origin/main` 未检出常见密钥模式。公开 Git 历史中的旧 DeepSeek 风格密钥候选仍未被历史重写清除，不能把当前树清洁表述为历史已安全。
- supersedes: 同日审查条目中“两个 PR 均未合并、正式域名仍运行旧版、未执行生产部署”的阶段状态；同日数据快照的 1743/554/1151 已被本次 1779/1036/590 只读观察取代。
- remaining_risk: 已部署代码仍有负缓存误记 `found`、`live_lookup_attempts` 无过期清理、8 秒预算非严格墙钟上限三项残留；数据健康仍为 degraded；历史凭据需先在提供方轮换，再受控清理所有分支历史。

## 2026-10-24 负缓存持久化失败与过期清理修正

- event_id: `2026-10-24-negative-cache-consistency`
- status: tested_not_deployed
- scope: `/api/v1/verify` 查询时发现/复核的尝试记录顺序、`live_lookup_attempts` 过期清理、`attempted_at` 索引与迁移。
- result: 来源结果只有成功持久化后才记录 `found`；持久化异常或返回空结果时不写负缓存，下一请求仍可联网重试。每次写尝试记录时删除重试窗口外的旧行，避免公共输入使表无限增长。
- evidence: 后端全量 `204 passed`，新增测试覆盖复核持久化失败、发现持久化失败和过期行清理；隔离 SQLite 迁移连续执行两次通过；预建缺少索引的旧 `live_lookup_attempts` 表后再迁移两次，索引 `ix_live_lookup_attempts_attempted_at` 成功补齐。
- remaining_risk: 尚未推送或部署，生产仍保留旧行为；8 秒联网预算仍是软上限，不由本次改变。

## 2026-10-31 负缓存修正合并与生产部署验收

- event_id: `2026-10-31-negative-cache-deployed`
- status: deployed_and_production_verified
- scope: PR #10、`main`、Vercel Production 与正式域名；负缓存持久化顺序、过期清理、索引迁移及重复查询。
- changes: PR #10 合并为 `20e94da7091f005b05e53f6dc10c9f70bd399bf9`。来源结果只在持久化函数正常返回后记录 `found`；持久化异常或空结果不写尝试记录。每次写尝试同一事务删除重试窗口外行，`attempted_at` 索引由模型及 `migrate_v2.py` 对已有表补齐。
- evidence: main push CI `41154546399` 的 backend/frontend/postgres-smoke 全部通过；本地完整后端 `204 passed`；SQLite 新建及旧表升级各连续迁移两次保持幂等。Vercel 生产部署 `dpl_6SGVU6u8BaxNBipY4hAVU8Bbehhr` 为 `READY`，commit 为 `20e94da`，正式域名别名指向该部署。
- production: `/`、`/api/health`、`/api/stats`、`/api/sync/status` 均 HTTP 200；总数1809、1240 current、386 unknown、0 conflict，`data=degraded`，最近同步 id=68 success。`GB 50016-2014` 返回 current、2018年版、`revision_missing` 和正确引用建议，约1.89秒。全新不存在编号第一次约5.40秒，第二次约2.27秒，重复查询未再耗完联网预算。
- search-architecture note: 搜建筑真人验证页只使该自动化来源在当次不可用，不绕过人机验证，也不阻断数据库结果、其他来源检查或整体比对；人工仍可打开搜索页和规范全文链接处理验证。
- documentation_followup: PR #11 合并为 `main@1e79fdc`，main CI `41155007592` 与 Vercel 文档部署 `dpl_Fc9pGAgvjfByb5mpnvzwRyHFama5` 成功；仅为部署记录，不改变功能提交 `20e94da` 的运行代码。
- supersedes: 2026-10-24 条目中的 `tested_not_deployed` 阶段状态和生产旧版本描述。
- remaining_risk: 8秒联网预算仍是软上限；386条unknown及公开 `data=degraded` 仍需来源治理；公开 Git 历史旧凭据候选仍需先轮换再受控清理。

## 2026-10-31 发布质量门改为提交前生效

- event_id: `2026-10-31-transactional-publish-gate`
- status: tested
- scope: `scripts/rebuild_v2.py`、`publish_staging`。决策见 [ADR-0007](decisions/ADR-0007-transactional-publish-gate.md)。
- result: 门禁不通过时整体回滚并退出 2，隔离重试同事务回滚；报告新增 `publication` 与 `relation_issues`。
- evidence: 复查时每日任务 run 41027984277 报 invalid_relation=2、reverse_chronology=1，而代码先提交后校验。后端全量207项通过（新增3项）；SQLite 种子实际重建 publishable=true、committed，黄金案例50/50。
- remaining_risk: 未提交、未部署；本地无 PostgreSQL，未在 PostgreSQL 上实测回滚。上线后在2条异常关系修复前，定时发布会被阻塞，这2条的具体内容尚未知。

## 2026-10-31 发布质量门合并上线

- event_id: `2026-10-31-publish-gate-deployed`
- status: production_verified
- scope: [PR #13](https://github.com/qiushanyueyue/guifanbidui/pull/13)，合并提交 `e58a6dc60150b06645bdeedd81444af28a3b5458`。
- result: main CI 通过，Vercel 生产部署 success；定时任务从 main 取代码，下一次运行起使用新门禁。
- evidence: GitHub CI/部署状态；公网 health/stats/首页 200，总数1810、unknown 386。
- remaining_risk: 新门禁尚未经过一次真实定时运行；PostgreSQL 上的回滚未实测；2条异常关系内容待首次失败日志列出，修复前定时发布被阻塞。
