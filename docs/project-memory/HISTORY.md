# 项目记忆历史

> append-only：只能追加新条目；发现旧事实错误时追加更正，不重写或删除旧条目。禁止记录 Secret、认证过程和完整用户文档。

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
- evidence: `python scripts/check_project_memory.py`、记忆合同测试 3 项、后端全量 103 项、前端 11 项、ESLint、Vite build、`git diff --check`。
- supersedes: 仅依赖会话上下文、过时交接文档或平台隐式记忆的方式。
- remaining_risk: 记忆不是实时数据源；新对话仍必须根据 `as_of` 和证据重新核验会漂移的事实。

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
