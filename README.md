# 规范对比工具 (Standard Comparison Tool)

一个建筑设计规范提取与查新工具，旨在帮助设计师快速校验设计说明中的规范引用是否符合最新现行标准。

![截图预览](screenshot_new.png)

## 主要功能 (Features)

*   **智能提取**: 使用正则表达式从设计说明文本中自动提取规范及其编号。
*   **实时查新**: 对接工标网 (CSRES) 和本地数据库 (收录1768+条规范，支持模糊匹配搜建筑链接)，实时检测规范现行状态。
*   **差异对比**: 自动比对设计说明中的版本与最新版本，高亮显示过期规范。
*   **一键导出**: 支持将查新结果导出 Excel。

## 技术栈 (Tech Stack)

*   **前端**: React, TypeScript, Vite
*   **后端**: Python, FastAPI
*   **数据库**: SQLite (本地缓存), SQLAlchemy


## 本地运行 (Development)

### 后端 (Backend)

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python run_server.py
```

服务运行在: `http://localhost:8012`

### 前端 (Frontend)

```bash
cd frontend
npm install
npm run dev
```

前端运行在: `http://localhost:5173`




