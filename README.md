# 规范查新数据库

建筑、市政和结构工程规范的版本查新工具：用户输入设计说明后，本地解析规范编号，系统输出明确的规范状态、引用版本、替代关系和推荐引用。查询优先使用新鲜数据库缓存；记录过期或异常时按来源优先级自动联网复核。

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
STANDARD_CACHE_FRESH_DAYS=30
ENABLE_LIVE_STANDARD_REFRESH=true
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

WorkBuddy 可直接调用公网入口 `POST https://guifan.108923.xyz/api/v1/verify`。请求示例和可复制提示词见 [`docs/workbuddy.md`](docs/workbuddy.md)。接口只接收规范名称和编号；新鲜缓存直接返回，过期或异常记录可触发有界联网复核。

状态值固定为 `current`、`upcoming`、`abolished`、`replaced`、`partially_amended`、`unknown`、`conflict`。前端优先显示“现行 / 现行，需采用最新修订 / 已废止 / 已被替代”；只有来源冲突、全部不可用、无法检索或替代矛盾时显示“暂无法确认”。

## 数据与同步

`standards_v2` 保存规范身份、版本和最终决策，并预留 `mandatory_clause_status` 以区分整本规范状态与强制性条文/条文级变化；`standard_v2_sources` 保存官方、搜建筑和工标网证据；`standard_v2_relations` 保存替代、修订关系；`sync_runs` 保存每次同步的计数和失败原因。官方明确状态直接定案；官方不可用时，工标网或搜建筑单源完整匹配且明确状态可形成 `single_source`，两站对身份、状态和替代关系一致时升级为 `cross_verified`。

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
