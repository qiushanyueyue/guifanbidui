# 规范对比项目交接文档 (Project Handoff Summary)

> **历史文档警告（2026-08-25）**：本文原有架构、端口、数据库、Gemini/实时爬虫和生产描述可能已经过时，不是当前真相。新对话必须先阅读 [`AGENTS.md`](AGENTS.md)、[`docs/PROJECT_CHARTER.md`](docs/PROJECT_CHARTER.md)、[`MEMORY.md`](MEMORY.md) 和 [`docs/project-memory/CURRENT.md`](docs/project-memory/CURRENT.md)，并按其中证据重新验证；本文仅用于解释旧项目背景。

## 1. 项目概览 (Project Overview)
本项目是一个 **建筑设计规范自动合规性校验工具**。主要用于解决设计说明中引用的规范版本过时的问题。
核心功能是：输入一大段设计说明文本，系统自动提取其中的规范名称和编号，实时去工标网 (`csres.com`) 检索最新状态（现行/废止/被替代），并给出合规性报告。

## 2. 技术架构 (Architecture)

### 前端 (Frontend)
- **Stack**: React 18, TypeScript, Vite
- **UI Framework**: 自定义 CSS Modules (Vanilla JS/CSS), 追求 "Vibrant & Premium" 设计风格。
- **关键组件**:
  - `InputSection`: 文本输入与提取触发。
  - `ComparisonTable`: 展示提取结果与实时数据的对比表格。
  - `StandardDetailModal`: 模态框，展示规范详细信息（发布日期、实施日期、替代关系等）。
- **运行端口**: 3355

### 后端 (Backend)
- **Stack**: Python 3.10+, FastAPI
- **Database**: SQLite (SQLAlchemy ORM) - 用于缓存查询过的规范状态。
- **External Services**:
  - **Google Gemini AI**: 用于从非结构化文本中增强提取规范名称和编号。
  - **Csres Crawler**: 基于 `requests` + `BeautifulSoup` 的爬虫，实时抓取工标网数据。
- **运行端口**: 8012

### 数据流 (Data Flow)
1. **提取 (Extract)**: 用户文本 -> 正则/AI 提取 -> 规范编号列表 (e.g., "GB 50016-2014")。
2. **检索 (Search)**:
   - **L1 缓存**: 本地 Excel (`规范目录库20251011.xlsx`) 优先匹配。
   - **L2 缓存**: SQLite 数据库匹配已缓存的即时状态。
   - **L3 实时**: 爬虫访问 `csres.com` 搜索。
3. **校验 (Verify)**: 对比【提取版本】与【最新版本】的年份，计算匹配度 (Match Score)。

## 3. 当前开发进度 (Current Status)

### ✅ 已完成功能
- **基础骨架**: 前后端联调打通，CORS配置完成。
- **提取功能**: 支持 AI 提取与正则提取双模式。
- **详情弹窗**: 点击表格“查看”按钮，可弹出 `StandardDetailModal` 显示详细信息。
- **Excel 挂载**:后端已集成 Excel 文件加载器作为一级缓存。

### ⚠️ 待优化/修复问题 (Critical Issues)
1. **匹配逻辑不严谨**:
   - 目前搜索结果包含模糊匹配（例如搜 "GB 50016" 可能会列出 "GB 50016-2014" 和其他无关标准）。
   - **需求**: 必须实现 **100% 精确匹配** 逻辑。只有当 编号 和 年份 完全一致时，Match Score 才是 100%。需过滤掉爬虫返回的无关干扰项。
2. **爬虫健壮性**:
   - `csres.com` 的 HTML 结构解析偶尔失效，导致 `Status` 字段为空或包含错误文本（如提取到了部门名称）。
   - 需增强 `app/services/crawler.py` 的解析容错能力。
3. **前端体验**:
   - 偶发白屏或布局错位（已修复大部分，需持续关注）。
   - 图标需求：需使用透明背景的 Logo/Favicon。

## 4. 后续开发计划 (Next Steps)

### Priority 0: 核心逻辑修正
- [ ] **精确匹配算法**: 在 `backend/app/api/endpoints.py` 或 `crawler.py` 中增加后处理逻辑。如果用户搜 "GB 50016-2014"，结果列表必须严格过滤或排序，确保首位是完全匹配项。
- [ ] **状态清洗**: 优化爬虫正则，确保 status 字段只可能是 ["现行", "废止", "即将实施", "被替代"] 之一。

### Priority 1: UI/UX 提升
- [ ] **Real-time Feedback**: 点击 "View" 时确保是实时请求最新数据（目前已大致实现，需测试稳定性）。
- [ ] **Loading 状态**: 搜索和详情加载时需要更明显的 Loading 动画。

## 5. 常用命令 (Commands)

**启动后端**:
```bash
cd backend
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8012 --reload
```

**启动前端**:
```bash
cd frontend
npm run dev
```

**环境配置**:
确保 `backend/.env` 中包含 `GEMINI_API_KEY`。
