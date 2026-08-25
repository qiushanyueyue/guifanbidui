#!/usr/bin/env python3
"""Import ``backend/standards_data.xlsx`` into the configured database."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.db_init import init_db
from app.models.base import SessionLocal
from app.services.excel_import import import_legacy_excel


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", default=None, help="legacy workbook path")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    init_db()
    db = SessionLocal()
    try:
        result = import_legacy_excel(db, args.path)
        print(result)
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
