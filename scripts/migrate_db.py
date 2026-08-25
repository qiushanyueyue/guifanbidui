#!/usr/bin/env python3
"""Apply additive schema changes and normalize legacy standard rows.

The command is explicit so production migrations are reviewed before they
run.  New installations can use ``create_all``; existing installations use
this script before deploying the new API.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import CheckConstraint, Column, MetaData, Table, inspect, text
from sqlalchemy.schema import CreateTable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.db_init import init_db
from app.models.base import SessionLocal, engine
from app.models.enums import StandardStatus, VerificationLevel, normalize_status
from app.models.models import StandardModel
from app.services.standard_normalizer import normalize_standard_code, normalized_name


LEGACY_COLUMNS = {
    "normalized_code": "VARCHAR(120)",
    "normalized_name": "VARCHAR(500)",
    "edition": "VARCHAR(80)",
    "revision_year": "VARCHAR(4)",
    "amendment": "VARCHAR(200)",
    "standard_type": "VARCHAR(80)",
    "publish_date": "VARCHAR(40)",
    "implement_date": "VARCHAR(40)",
    "abolish_date": "VARCHAR(40)",
    "replaces": "TEXT",
    "replaced_by": "TEXT",
    "article_status": "TEXT",
    "mandatory_clause_status": "TEXT",
    "issuing_authority": "VARCHAR(300)",
    "canonical_source": "VARCHAR(80)",
    "canonical_url": "VARCHAR(1000)",
    "soujianzhu_url": "VARCHAR(1000)",
    "source_conflict": "BOOLEAN DEFAULT FALSE",
    "conflict_details": "TEXT",
    "verification_level": "VARCHAR(32) DEFAULT 'unverified'",
    "first_seen_at": "TIMESTAMP",
    "last_seen_at": "TIMESTAMP",
    "last_verified_at": "TIMESTAMP",
    "source_updated_at": "VARCHAR(80)",
    "record_updated_at": "TIMESTAMP",
    "updated_at": "TIMESTAMP",
}


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    inspector = inspect(engine)
    existing = {column["name"] for column in inspector.get_columns("standards")} if "standards" in inspector.get_table_names() else set()
    missing = [(name, sql_type) for name, sql_type in LEGACY_COLUMNS.items() if name not in existing]
    if missing:
        with engine.begin() as connection:
            for name, sql_type in missing:
                connection.execute(text(f"ALTER TABLE standards ADD COLUMN {name} {sql_type}"))
    if engine.dialect.name == "sqlite" and _has_unique_code_index():
        _rebuild_sqlite_standards()
    elif engine.dialect.name == "postgresql":
        _drop_postgres_code_unique()
    init_db()
    db = SessionLocal()
    try:
        for standard in db.query(StandardModel).all():
            standard.normalized_code = normalize_standard_code(standard.code)
            standard.normalized_name = normalized_name(standard.name)
            standard.status = normalize_status(standard.status).value
            if not standard.verification_level:
                standard.verification_level = VerificationLevel.UNVERIFIED.value
            standard.updated_at = standard.updated_at or standard.last_updated or datetime.utcnow()
            standard.record_updated_at = standard.record_updated_at or standard.last_updated or standard.updated_at
            standard.year = standard.revision_year or standard.year
            standard.issuing_authority = standard.issuing_authority or standard.publishing_department
            standard.implement_date = standard.implement_date or standard.implementation_date
            standard.canonical_url = standard.canonical_url or standard.url
        db.commit()
    finally:
        db.close()
    logging.info("migration complete; added %s columns", len(missing))
    return 0


def _has_unique_code_index() -> bool:
    with engine.connect() as connection:
        rows = connection.execute(text("PRAGMA index_list('standards')")).fetchall()
        for row in rows:
            # SQLite returns (seq, name, unique, origin, partial).
            if len(row) >= 3 and bool(row[2]):
                name = str(row[1])
                columns = connection.execute(text(f"PRAGMA index_info('{name.replace(chr(39), chr(39) * 2)}')")).fetchall()
                if [str(item[2]) for item in columns] == ["code"]:
                    return True
    return False


def _rebuild_sqlite_standards() -> None:
    """Remove the legacy code UNIQUE constraint while preserving rows."""

    metadata = MetaData()
    columns = []
    for column in StandardModel.__table__.columns:
        columns.append(
            Column(
                column.name,
                column.type,
                primary_key=column.primary_key,
                nullable=column.nullable,
                server_default=column.server_default,
            )
        )
    constraints = [
        CheckConstraint("status IN ('current','upcoming','abolished','replaced','partially_amended','unknown','conflict')", name="ck_standards_status"),
        CheckConstraint("verification_level IN ('official','cross_verified','single_source','unverified','conflict')", name="ck_standards_verification_level"),
    ]
    temporary = Table("standards_migration", metadata, *columns, *constraints)
    with engine.begin() as connection:
        connection.execute(text("PRAGMA foreign_keys=OFF"))
        connection.execute(CreateTable(temporary))
        old_columns = {row[1] for row in connection.execute(text("PRAGMA table_info('standards')")).fetchall()}
        new_columns = [column.name for column in columns if column.name in old_columns]
        quoted = ", ".join(f'"{name}"' for name in new_columns)
        connection.execute(text(f'INSERT INTO "standards_migration" ({quoted}) SELECT {quoted} FROM "standards"'))
        connection.execute(text('DROP TABLE "standards"'))
        connection.execute(text('ALTER TABLE "standards_migration" RENAME TO "standards"'))
        connection.execute(text("PRAGMA foreign_keys=ON"))
    logging.info("rebuilt SQLite standards table without a code UNIQUE constraint")


def _drop_postgres_code_unique() -> None:
    inspector = inspect(engine)
    for constraint in inspector.get_unique_constraints("standards"):
        if constraint.get("column_names") == ["code"] and constraint.get("name"):
            quoted = engine.dialect.identifier_preparer.quote(constraint["name"])
            with engine.begin() as connection:
                connection.execute(text(f"ALTER TABLE standards DROP CONSTRAINT {quoted}"))
            logging.info("removed PostgreSQL legacy unique constraint on standards.code")


if __name__ == "__main__":
    raise SystemExit(main())
