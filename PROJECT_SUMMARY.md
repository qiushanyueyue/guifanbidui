# 规范对比工具 (Specification Comparison Tool) - 项目概要

## 1. 项目简介
本项目是一个用于 **建筑设计规范自动提取与合规性校验** 的 Web 工具。
它能够从设计说明文本中识别规范编号（如 `GB 50016-2014`），并利用 Google Gemini AI 进行增强语义提取。然后通过 `csres.com` 校验规范的现行/废止状态，并将数据缓存至本地 SQLite 数据库。

## 2. 技术栈
- **Frontend**: React (Vite), TypeScript, CSS Modules (Vanilla)
- **Backend**: Python (FastAPI), SQLAlchemy (SQLite), Google Generative AI
- **Tools**: Axios, BeautifulSoup4, Pydantic

## 3. 项目结构
```
/Users/qiushanyueyue/Documents/work/规范对比/
├── backend/                  # 后端服务
│   ├── app/
│   │   ├── api/              # API 路由 (endpoints.py)
│   │   ├── models/           # 数据库模型 (models.py) & Pydantic Schemas (schemas.py)
│   │   ├── repositories/     # 数据库操作 (standard_repo.py)
│   │   └── services/         # 核心业务逻辑
│   │       ├── crawler.py    # 工标网爬虫
│   │       └── extractor.py  # 提取逻辑 (Gemini AI + 正则)
│   ├── main.py               # FastAPI 入口
│   ├── standards.db          # SQLite 数据库 (自动生成)
│   ├── requirements.txt      # Python 依赖
│   └── venv/                 # 虚拟环境
├── frontend/                 # 前端应用
│   ├── src/
│   │   ├── components/       # React 组件 (InputSection, ComparisonTable)
│   │   ├── api.ts            # API 客户端
│   │   ├── App.tsx           # 主应用页
│   │   └── main.tsx          # 入口文件
│   ├── vite.config.ts        # Vite 配置 (已配置 host:true)
│   └── package.json
```

## 4. 关键文件说明

### 后端
- **`backend/app/services/extractor.py`**: 核心提取逻辑。
  - **Gemini 模式**: 当 `.env` 中配置 `GEMINI_API_KEY` 时，优先使用 AI 提取。
  - **正则模式**: 作为降级方案，匹配 `《...》(GB ...)` 格式。
- **`backend/app/services/crawler.py`**: 负责请求 `csres.com` 搜索规范状态。
- **`backend/main.py`**: 配置了 CORS 允许跨域，并初始化数据库表。

### 前端
- **`frontend/vite.config.ts`**:
  - 端口固定为 `3355`。
  - 设置 `host: true` 允许局域网访问。
  - 强制包含 `.tsx` 文件解析。
- **`frontend/src/api.ts`**: 指向 `http://localhost:8012/api`。后端地址若变更需同步修改此处。

## 5. 启动与运行

### 后端 (Port: 8012)
```bash
cd backend
source venv/bin/activate
# 首次运行需安装依赖: pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8012 --reload
```
*环境变量*: 在 `backend/.env` 中设置 `GEMINI_API_KEY`。

### 前端 (Port: 3355)
```bash
cd frontend
# 首次运行需安装依赖: npm install
npm run dev -- --host 0.0.0.0 --port 3355
```
访问地址: `http://localhost:3355`

## 6. 常见问题排查 (Troubleshooting)

### Q1: 前端打开白屏？
- **检查端口**: 确保访问的是 `3355` (项目中配置的端口)。
- **Vite 缓存**: 尝试删除 `frontend/node_modules/.vite` 目录并重启。
- **浏览器缓存**: 尝试 `Ctrl+F5` 强制刷新。

### Q2: 无法提取规范？
- **API Key**: 检查后台日志，确认 `GEMINI_API_KEY` 是否有效。
- **网络**: 确认服务器能连接 Google API。
- **降级**: 若 AI 失败，系统会回退到正则，请确保文本包含标准的 `GB XXXXX-XXXX` 格式。

### Q3: 数据库在哪里？
- 数据存储在 `backend/standards.db` (SQLite 文件)。
- 可使用任何 SQLite 客户端查看数据。
