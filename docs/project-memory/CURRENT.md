# 当前事实快照

- snapshot_id: `2026-09-01-production-and-local-fix`
- as_of: `2026-09-01T21:40:17+08:00`
- verification: `production_verified`
- scope: `qiushanyueyue/guifanbidui` 与 `https://guifan.108923.xyz`
- evidence_policy: 下列事实来自当日实际命令/API/浏览器验收；新对话必须重新核验会漂移的项目。

## 仓库与部署

- as_of: `2026-09-01T21:40:17+08:00`
- verification: `production_verified`
- evidence: GitHub CLI/API、Vercel 部署状态、公网 `/api/health`。

- GitHub 可见性：Public；证据：`gh repo view qiushanyueyue/guifanbidui --json visibility,isPrivate,url` 与匿名 GitHub API。
- 明确查新功能生产提交为 `a8ac4f9`；远端功能分支仍为 `4556b15`，当前 HEAD/主线需实时复核。
- 生产域名：`https://guifan.108923.xyz`。
- Vercel 主线自动部署：Ready；当日部署 `guifanbidui-dywa7lp98-yys-projects-2b5b21c2.vercel.app`。
- 公网健康：`/api/health` 返回 `status=ok`、`database=ok`。
- Vercel 对提交 `a8ac4f9` 返回 `Deployment has completed`；现有项目和域名未更换。

## 数据快照

- as_of: `2026-09-01T21:40:17+08:00`
- verification: `production_verified`
- evidence: 公网 `/api/stats`、Neon 查询与 `artifacts/` 审计报告。

- 规范总数：1741。
- 状态：367 `current`、27 `abolished`、1347 `unknown`、0 `conflict`。
- 数据库最近发布时间：`2026-09-01T13:37:59.240571Z`。
- 公网来源健康：`samr/mohurd/openstd/soujianzhu=never`、`csres=partial`；这证明工标网仅做了部分核实，并未完成全库遍历。
- V2 关系：32；补充规范性文件：230。
- Excel `/Volumes/yue/Download/规范目录库20251011.xlsx` 已审计并补充候选；外部挂载路径本身不是运行时依赖。

证据：公网 `/api/stats`、`/api/health`、历史 Neon 查询、`artifacts/data_quality_report.json`、`artifacts/excel_catalog_audit_20251011.json`。

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

- as_of: `2026-08-25T15:25:37+08:00`
- verification: `tested`
- evidence: pytest、Vitest、ESLint、Vite build、黄金案例与浏览器实测。

- 后端：103 passed（含 3 项记忆合同测试）；127 个既有弃用警告。
- 前端：11 passed；ESLint 和 Vite build 通过。
- 黄金案例：50/50。
- 用户真实规范说明：33/33 条提取。
- 公网示例：7 条中 3 完全一致、2 需修改、1 废止、1 未找到。
- 浏览器：1440×900 与 390×844 无 body 横向溢出；来源按钮 96×44；导出弹窗可访问；控制台无错误。

## 当前风险与未验证项

- as_of: `2026-08-25T15:25:37+08:00`
- verification: `mixed`；每项按文字中的“未验证/需要”继续保守处理。
- evidence: 数据状态统计、适配器实测、GitHub Actions 查询与前端代码审查。

- 1347 条 `unknown` 仍需核验，不能无身份匹配和来源状态证据地批量转换为现行。
- `RFJ 02-2009`、`DB/T 29-176-2016`、`DB 29-20-2017`、`GB 50046-2018` 需要更多来源证据。
- 官方来源适配器不是全部生产连通；实际未验证的来源必须继续标记未验证。
- 远程提取开启后，本地零结果会把触发兜底的整段原始输入发送给 DeepSeek；前端尚未给出明确的用户告知，生产开启前需补足。
- GitHub 工作流文件存在，但 `2026-08-25` 的 `gh run list` 为空；不能据此宣称定时任务已成功运行。
- 记忆系统已本地提交、未推送；同一工作区的新对话可恢复，公网 GitHub 干净克隆暂不可恢复。
- 第三方页面结构会变化，适配器需要 fixture 与实际抽样共同验证。

## 当前查新判定策略

- as_of: `2026-09-01T17:43:30+08:00`
- verification: `tested_local`
- evidence: `tests/test_live_verification.py`、`tests/test_resolver.py`、`tests/test_v2_pipeline.py` 与 ADR-0003。

- 主查询顺序为数据库新鲜缓存 → 权威官方源 → 工标网/搜建筑精确匹配 → 历史数据库 → 用户反馈；默认新鲜期 30 天。本地未收录的单条输入也进行有界来源发现并写入缓存。
- 官方明确状态直接定案为 `official`；工标网或搜建筑任一来源完整匹配且明确状态即可形成 `single_source` 明确结论，两站对身份、状态和替代关系一致时升级为 `cross_verified`。
- 引用一致性与规范状态分离：单一来源的编号、名称完整匹配即显示“完全一致”；来源缺少状态时，仅规范状态显示“暂无法确认”。
- 前端优先输出“现行 / 现行，需采用最新修订 / 已废止 / 已被替代”；来源冲突、全部不可用、无法检索或替代矛盾统一显示“暂无法确认”。
- 在线复核成功会追加 staging/source 证据并刷新 V2 状态缓存；失败时保留历史明确结论。
- 日/周核实任务优先选择当前 `unknown`，分批写入 staging 后通过 V2 质量门禁发布；月度任务继续轮询已有候选，避免已核实记录失去时效复查。现有任务仍不是工标网完整目录采集，漏收由查询时发现补足；该修改尚未推送或生产实测。
- 本地对 10 个 unknown 编号做工标网抽样：6 个取得精确记录、4 个解析失败；质量门禁通过，本地计数由 213 current / 1507 unknown 变为 214 current / 1506 unknown。5 个编号返回了独立修订版，原始无版次身份仍保守保留 unknown；后续批次会跳过已有已核实版次的编号，避免重复请求。

## 当前本地界面变更

- as_of: `2026-08-25T20:20:34+08:00`
- verification: `browser_verified_local`
- evidence: 本地 API/Vite 实际流程、浏览器 DOM/尺寸检查、前端测试、lint 与 build。

- 搜建筑与工标网来源按钮从 96×44 调整为桌面 84×36，统一 7px 圆角、字重、阴影与 hover/focus；移动端仍保留 44px 点击高度。
- 提取响应中名称和编号都为空白的项会在进入结果、计数和查询前过滤；本地输入含两个空行时只生成2条有效记录。
- “业务判定”和“规范状态”分列：完整匹配显示“完全一致”，规范状态独立显示“现行，需采用2018年版”等明确结论；异常才显示“暂无法确认”。
- 推荐引用同时包含版次和局部修订，例如 `《建筑设计防火规范》GB 50016-2014（2018年版+2024年局部修订）`。
- 本地浏览器实测 `GB 50016-2014` 缺版次时显示“修订版需更新 / 现行，需采用2018年版”，带 2018 年版时显示“一致”；控制台无 warning/error。
- Android: 仓库内未发现 Gradle 或 AndroidManifest 项目，本次没有可同步的 Android 端。
- AGY: 已按用户要求通过 AGY Skill 调用两次；项目映射修复后 AGY CLI 仍无诊断返回状态1，未修改文件，最终前端改动由主代理完成。

## 2026-09-01 漏收补查与来源链接修正

- as_of: `2026-09-01T21:40:17+08:00`
- verification: `production_verified`
- evidence: 工标网真实搜索、全量测试、GitHub/Vercel 状态、公网 API/浏览器流程与 Neon 条件更新。

- 工标网实时返回 `GB/T 50308-2017`、`GB 50911-2013`、`GB 50497-2019` 均为现行；本地漏收查询可将 `GB 50308-2017` 发现为 `GB/T 50308-2017`，返回“标准属性错误”并给出推荐编号。
- 已收录但状态未知的精确记录可由工标网单源明确为 `current/single_source`，业务判定显示“完全一致”。
- 搜建筑 `gfnr.aspx?id=...` 对外链接统一转换为 `NormContent.aspx?id=...` 全文阅读入口；搜建筑当前仍可能按 IP、会话或访问频率跳转真人验证，系统不绕过该安全控制。
- 本地完整验证基线为后端 121 项、前端 14 项、ESLint、Vite build；生产浏览器三条截图用例无控制台错误。
- 已部署 `guifan.108923.xyz` 并完成三条公网浏览器验收：2 条“完全一致/现行”、1 条 `GB`→`GB/T` 属性修正，未找到计数为 0。
- 首次公网验收发现仅编号查询可能重复写入发现记录；提交 `a8ac4f9` 增加按发现后规范编号复用已有 V2 记录。生产重复记录 ID `5506` 已可恢复地标记为 `quarantined`，保留 ID `5507`；两次连续查询后总数保持 1741、公开搜索仅返回 1 条。

## 下一次任务首先复核

1. `git status` 与远端分支提交。
2. 公网 `/api/health`、`/api/stats` 和目标用户流程。
3. 数据库数量、发布时间与自动同步最近运行。
4. 本任务相关来源的真实可用性。
