"""ASGI application factory shared by local and Vercel entrypoints."""

from __future__ import annotations

import logging
import os
import time
from collections import defaultdict, deque

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.endpoints import router
from app.db_init import init_db

logger = logging.getLogger(__name__)


class InMemoryRateLimitMiddleware:
    """Small process-local guard; deployment-level throttling remains upstream."""

    def __init__(self, app, limit: int = 120, window_seconds: int = 60):
        self.app = app
        self.limit = max(1, limit)
        self.window_seconds = max(1, window_seconds)
        self.events: dict[str, deque[float]] = defaultdict(deque)

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        # Health and cron checks should remain observable even under user load.
        if path.endswith("/health") or path.endswith("/cron/health"):
            await self.app(scope, receive, send)
            return
        client = scope.get("client")
        key = client[0] if client else "unknown"
        now = time.monotonic()
        events = self.events[key]
        while events and now - events[0] > self.window_seconds:
            events.popleft()
        if len(events) >= self.limit:
            response = JSONResponse({"detail": "rate limit exceeded"}, status_code=429)
            await response(scope, receive, send)
            return
        events.append(now)
        await self.app(scope, receive, send)


def _allowed_origins() -> list[str]:
    configured = os.getenv("ALLOWED_ORIGINS", "").strip()
    if configured:
        return [item.strip() for item in configured.split(",") if item.strip()]
    if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        return []
    return ["http://localhost:5173", "http://127.0.0.1:5173"]


init_db()
app = FastAPI(title="规范查新数据库 API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)
app.add_middleware(
    InMemoryRateLimitMiddleware,
    limit=int(os.getenv("RATE_LIMIT_PER_MINUTE", "120")),
    window_seconds=60,
)
app.include_router(router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "规范查新数据库 API 已启动"}


@app.get("/health")
async def root_health():
    # Keep the original /health URL while exposing the richer /api/health
    # contract to callers.  Avoid making a second HTTP request internally.
    from app.api.endpoints import _health_payload
    from app.models.base import SessionLocal

    db = SessionLocal()
    try:
        return _health_payload(db)
    finally:
        db.close()
