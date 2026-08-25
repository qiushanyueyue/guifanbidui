#!/usr/bin/env python3
"""Verify a bounded batch without issuing thousands of requests at once."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.db_init import init_db
from app.models.base import SessionLocal
from app.sync.orchestrator import verify_existing_standards


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=600)
    parser.add_argument("--source", default="csres")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    init_db()
    db = SessionLocal()
    try:
        run = verify_existing_standards(db, source_name=args.source, limit=args.limit)
        print({"source": run.source, "selected": run.found, "checked": run.updated, "failed": run.failed, "status": run.status})
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
