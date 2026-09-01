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
