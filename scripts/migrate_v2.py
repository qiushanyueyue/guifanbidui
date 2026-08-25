#!/usr/bin/env python3
"""Idempotently add the V2 rebuild tables and additive sync-run columns."""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import inspect, text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.models.base import Base, engine  # noqa: E402
import app.models.models  # noqa: E402,F401


def main() -> None:
    Base.metadata.create_all(bind=engine)
    columns = {column["name"] for column in inspect(engine).get_columns("sync_runs")}
    additions = {
        "mode": "VARCHAR(32) NOT NULL DEFAULT 'incremental'",
        "quarantined": "INTEGER NOT NULL DEFAULT 0",
    }
    with engine.begin() as connection:
        for name, definition in additions.items():
            if name not in columns:
                connection.execute(text(f"ALTER TABLE sync_runs ADD COLUMN {name} {definition}"))
    normative_columns = {column["name"] for column in inspect(engine).get_columns("normative_documents")}
    if "document_kind" not in normative_columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE normative_documents ADD COLUMN document_kind VARCHAR(40) NOT NULL DEFAULT 'unknown'")
            )
    print("V2 schema ready")


if __name__ == "__main__":
    main()
