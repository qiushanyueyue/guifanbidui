"""Schema bootstrap helpers used by the ASGI entrypoint and CLI scripts."""

from __future__ import annotations

import logging

from sqlalchemy import inspect, text

from app.models.base import Base, engine
from app.models import models as _models  # noqa: F401 - register all tables

logger = logging.getLogger(__name__)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    if "sync_runs" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("sync_runs")}
        additions = {
            "mode": "VARCHAR(32) NOT NULL DEFAULT 'incremental'",
            "quarantined": "INTEGER NOT NULL DEFAULT 0",
        }
        with engine.begin() as connection:
            for name, definition in additions.items():
                if name not in columns:
                    connection.execute(text(f"ALTER TABLE sync_runs ADD COLUMN {name} {definition}"))
    logger.info("database schema ready")
