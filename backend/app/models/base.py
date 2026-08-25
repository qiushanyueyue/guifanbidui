"""Database configuration.

PostgreSQL is the only persistent production backend.  SQLite remains a
deliberately explicit local-development default; when a serverless
environment has no ``DATABASE_URL`` we use an in-memory connection only so
the process can expose a degraded health response instead of pretending that
``/tmp`` is durable storage.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

logger = logging.getLogger(__name__)

IS_SERVERLESS = bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))
_configured_url = os.getenv("DATABASE_URL", "").strip()

if _configured_url:
    # psycopg 3 is the supported PostgreSQL driver.  Accept the common URL
    # spellings supplied by Neon and other hosted PostgreSQL providers.
    if _configured_url.startswith("postgres://"):
        _configured_url = "postgresql+psycopg://" + _configured_url[len("postgres://") :]
    elif _configured_url.startswith("postgresql://"):
        _configured_url = "postgresql+psycopg://" + _configured_url[len("postgresql://") :]
    SQLALCHEMY_DATABASE_URL = _configured_url
    DATABASE_CONFIG_WARNING: str | None = None
elif IS_SERVERLESS:
    SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
    DATABASE_CONFIG_WARNING = "DATABASE_URL is required in production; using an ephemeral in-memory database"
    logger.warning(DATABASE_CONFIG_WARNING)
else:
    configured_sqlite_path = os.getenv("SQLITE_DATABASE_PATH", "").strip()
    sqlite_path = Path(configured_sqlite_path) if configured_sqlite_path else Path(__file__).resolve().parents[3] / "standards.db"
    if not sqlite_path.is_absolute():
        sqlite_path = Path.cwd() / sqlite_path
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{sqlite_path}"
    # Keep this clean for logs and avoid leaking local paths into API output.
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.strip()
    DATABASE_CONFIG_WARNING = None

_is_sqlite = SQLALCHEMY_DATABASE_URL.startswith("sqlite")
_is_memory_sqlite = SQLALCHEMY_DATABASE_URL in {"sqlite:///:memory:", "sqlite://"}
engine_kwargs: dict[str, object] = {"pool_pre_ping": True}
if _is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    if _is_memory_sqlite:
        engine_kwargs["poolclass"] = StaticPool

engine = create_engine(SQLALCHEMY_DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def database_is_configured() -> bool:
    return not bool(DATABASE_CONFIG_WARNING)
