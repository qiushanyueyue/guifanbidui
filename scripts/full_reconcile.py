#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.db_init import init_db
from app.models.base import SessionLocal
from app.sync.orchestrator import run_sync


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=500)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    init_db()
    db = SessionLocal()
    try:
        runs = run_sync(db, mode="full_reconcile", limit=args.limit)
        print([{"source": run.source, "status": run.status, "found": run.found, "failed": run.failed} for run in runs])
        return 0 if all(run.status in {"success", "partial"} for run in runs) else 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
