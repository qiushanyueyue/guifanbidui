# 当前事实快照

- snapshot_id: `2026-08-25-production-v2`
- as_of: `2026-08-25T15:25:37+08:00`
- verification: `production_verified`
- scope: `qiushanyueyue/guifanbidui` 与 `https://guifan.108923.xyz`
- evidence_policy: 下列事实来自当日实际命令/API/浏览器验收；新对话必须重新核验会漂移的项目。

## 仓库与部署

- as_of: `2026-08-25T15:25:37+08:00`
- verification: `production_verified`
- evidence: GitHub CLI/API、Vercel 部署状态、公网 `/api/health`。

- GitHub 可见性：Public；证据：`gh repo view qiushanyueyue/guifanbidui --json visibility,isPrivate,url` 与匿名 GitHub API。
- 远端分支：`origin/main`、`origin/feat/standards-v2-rebuild` 均指向 `4556b15`；证据：`git ls-remote origin ...`。
- 生产域名：`https://guifan.108923.xyz`。
- Vercel 主线自动部署：Ready；当日部署 `guifanbidui-dywa7lp98-yys-projects-2b5b21c2.vercel.app`。
- 公网健康：`/api/health` 返回 `status=ok`、`database=ok`。

## 数据快照

- as_of: `2026-08-25T15:25:37+08:00`
- verification: `production_verified`
- evidence: 公网 `/api/stats`、Neon 查询与 `artifacts/` 审计报告。

- 规范总数：1738。
- 状态：213 `current`、18 `abolished`、1507 `unknown`、0 `conflict`。
- 数据库最近发布时间：`2026-08-25T05:22:39.690914Z`，前端按上海时区显示 `2026.08.25 13:22`。
- V2 关系：32；补充规范性文件：230。
- Excel `/Volumes/yue/Download/规范目录库20251011.xlsx` 已审计并补充候选；外部挂载路径本身不是运行时依赖。

证据：公网 `/api/stats`、Neon 查询、`artifacts/data_quality_report.json`、`artifacts/excel_catalog_audit_20251011.json`。

## 当前行为不变量

- as_of: `2026-08-25T15:25:37+08:00`
- verification: `tested`
- evidence: 后端契约/回归测试与当日公网抽样。

- 普通 `/api/search`、`/api/standards/search`、`/api/v1/verify` 只查询数据库。
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

- 1507 条 `unknown` 仍需核验，不能批量转换为现行。
- `RFJ 02-2009`、`DB/T 29-176-2016`、`DB 29-20-2017`、`GB 50046-2018` 需要更多来源证据。
- 官方来源适配器不是全部生产连通；实际未验证的来源必须继续标记未验证。
- 远程提取开启后，本地零结果会把触发兜底的整段原始输入发送给 DeepSeek；前端尚未给出明确的用户告知，生产开启前需补足。
- GitHub 工作流文件存在，但 `2026-08-25` 的 `gh run list` 为空；不能据此宣称定时任务已成功运行。
- 第三方页面结构会变化，适配器需要 fixture 与实际抽样共同验证。

## 下一次任务首先复核

1. `git status` 与远端分支提交。
2. 公网 `/api/health`、`/api/stats` 和目标用户流程。
3. 数据库数量、发布时间与自动同步最近运行。
4. 本任务相关来源的真实可用性。
