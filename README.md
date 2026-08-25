# 规范查新数据库

建筑、市政和结构工程规范的版本查新工具：用户输入设计说明后，本地解析规范编号，在持久化规范元数据库中查询状态、版本、来源和最近核验时间。普通查询只访问数据库，不现场抓取第三方网站。

## 技术栈

- 前端：React + TypeScript + Vite
- API：FastAPI + SQLAlchemy
- 生产数据库：PostgreSQL（推荐 Vercel + Neon）
- 本地开发：SQLite
- 同步：GitHub Actions；Vercel Cron 仅做轻量健康检查

## 本地运行

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd ..
PYTHONPATH=backend python scripts/import_legacy_excel.py
PYTHONPATH=backend uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8012
```

前端另开终端：

```bash
cd frontend
npm install
npm run dev
```

本地默认数据库是仓库根目录的 `standards.db`，可用 `SQLITE_DATABASE_PATH` 覆盖。Excel 只用于一次性导入，不能作为 API 运行时兜底。

## 生产配置

Vercel 必须设置：

```text
DATABASE_URL=postgresql://...        # Neon PostgreSQL 连接串
ALLOWED_ORIGINS=https://your-domain.example
CRON_SECRET=<runtime secret>
ENABLE_REMOTE_EXTRACTION=false
```

GitHub Secrets 至少设置 `DATABASE_URL`；不要把连接串、API key 或 `CRON_SECRET` 写入源码或 workflow YAML。缺少生产 `DATABASE_URL` 时服务会以 degraded health 启动并明确告警，不会使用 `/tmp` SQLite 冒充持久数据库。

已有数据库先执行：

```bash
PYTHONPATH=backend python scripts/migrate_db.py
PYTHONPATH=backend python scripts/import_legacy_excel.py --path backend/standards_data.xlsx
```

## API

兼容接口：`POST /api/extract`、`POST /api/search`、`POST /api/detail`、`GET /api/stats`。

稳定接口：

- `GET /api/standards/search?q=...`
- `GET /api/standards/{id}`、`/sources`、`/history`
- `GET /api/standards/code/{code}`
- `GET /api/sync/status`
- `GET /api/health`
- `POST /api/v1/verify`（只接收规范名称/编号，不接收设计说明、图纸或内部资料）
- `POST /api/export`（导出包含判定、建议引用和双源链接的 Excel）

WorkBuddy 可直接调用公网只读入口 `POST https://guifan.108923.xyz/api/v1/verify`。请求示例和可复制提示词见 [`docs/workbuddy.md`](docs/workbuddy.md)。普通调用只查数据库，不会触发现场爬取。

状态值固定为 `current`、`upcoming`、`abolished`、`replaced`、`partially_amended`、`unknown`、`conflict`，前端再映射为中文标签。无法核验时是 `unknown/待核验`，不会默认显示现行。

## 数据与同步

`standards_v2` 保存规范身份、版本和最终决策，并预留 `mandatory_clause_status` 以区分整本规范状态与强制性条文/条文级变化；`standard_v2_sources` 保存搜建筑和工标网证据 URL；`standard_v2_relations` 保存替代、修订关系；`sync_runs` 保存每次同步的计数和失败原因。第三方来源冲突会保留并标记 `conflict`，来源失败不会转换成现行。

来源适配器位于 `backend/app/sources/`。CSRES 和搜建筑已提供带限速、重试、超时、编码检测、结构校验和 fixture 解析器的适配器；官方平台适配器要求通过环境变量提供公开元数据端点，未配置或页面结构不明确时会记录失败而不编造数据。

GitHub Actions：

- `standards-daily.yml`：增量同步
- `standards-weekly.yml`：分批核验（默认每次最多 600 条）
- 两者均支持 `workflow_dispatch`

Vercel Cron 调用受 `CRON_SECRET` 保护的 `/api/cron/health` 或 `/api/cron/status`，不在 Function 内运行全量爬虫。

## 测试

```bash
PYTHONPATH=backend pytest -q
cd frontend && npm run build && npm run lint
```

测试覆盖编号标准化、OCR 上下文、局部修订、来源冲突、来源不可用、Excel unknown 导入和 CSRES/搜建筑 fixture 回归。
