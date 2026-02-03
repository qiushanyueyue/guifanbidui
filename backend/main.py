from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import sys
import os

# Add the current directory (backend) to sys.path so 'app' can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.base import engine, Base
from app.models import models

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(title="规范对比工具 API", version="0.1.0")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，生产环境需配置为具体前端地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "规范对比工具 API 已启动"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

# 注册路由
from app.api.endpoints import router as api_router
app.include_router(api_router, prefix="/api")

