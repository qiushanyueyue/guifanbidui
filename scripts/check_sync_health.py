#!/usr/bin/env python3
"""Read-only quality gate for a specific completed source sync batch."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.models.base import SessionLocal  # noqa: E402
from app.models.models import SyncRunModel  # noqa: E402


def failure_rate(found: int, failed: int) -> float:
    return failed / found if found > 0 else 0.0


def batch_is_healthy(run: SyncRunModel, max_failure_rate: float) -> bool:
    if run.finished_at is None or run.status not in {"success", "partial"}:
        return False
    if not 0 <= run.failed <= run.found:
        return False
    if run.found == 0:
        return run.status == "success" and run.failed == 0
    return run.failed < run.found and failure_rate(run.found, run.failed) <= max_failure_rate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="csres")
    batch = parser.add_mutually_exclusive_group(required=True)
    batch.add_argument("--run-id", type=int)
    batch.add_argument("--run-id-file", type=Path)
    parser.add_argument("--max-failure-rate", type=float, default=0.5)
    args = parser.parse_args()
    if not 0 <= args.max_failure_rate <= 1:
        parser.error("--max-failure-rate must be between 0 and 1")
    try:
        run_id = args.run_id if args.run_id is not None else int(args.run_id_file.read_text().strip())
    except (OSError, ValueError):
        parser.error("run ID file is missing or invalid")
    with SessionLocal() as db:
        run = db.query(SyncRunModel).filter(
            SyncRunModel.id == run_id, SyncRunModel.source == args.source,
        ).first()
        if run is None:
            print(f"sync batch not found: source={args.source} run_id={run_id}")
            return 1
        print({"source": run.source, "run_id": run.id, "status": run.status,
               "found": run.found, "failed": run.failed,
               "failure_rate": round(failure_rate(run.found, run.failed), 4),
               "max_failure_rate": args.max_failure_rate})
        return 0 if batch_is_healthy(run, args.max_failure_rate) else 1


if __name__ == "__main__":
    raise SystemExit(main())
