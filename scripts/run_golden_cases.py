#!/usr/bin/env python3
"""Run the 50-case regression corpus against the local database/API logic."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("STANDARDS_DATASET", "v2")

from app.api.endpoints import verify_standard  # noqa: E402
from app.models.base import SessionLocal  # noqa: E402
from app.models.schemas import VerifyRequest  # noqa: E402


def main() -> int:
    corpus = json.loads((ROOT / "tests" / "benchmark" / "golden_cases.json").read_text(encoding="utf-8"))
    results = []
    with SessionLocal() as db:
        for case in corpus:
            response = verify_standard(VerifyRequest(code=case["code"], name=case["name"]), db)
            actual = response.match_type
            results.append({**case, "actual_match_type": actual, "passed": actual == case["expected_match_type"]})
    report = {
        "total": len(results),
        "passed": sum(item["passed"] for item in results),
        "failed": sum(not item["passed"] for item in results),
        "results": results,
    }
    output = ROOT / "artifacts" / "golden_cases_report.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("total", "passed", "failed")}, ensure_ascii=False))
    if report["failed"]:
        for item in results:
            if not item["passed"]:
                print(item["id"], item["expected_match_type"], item["actual_match_type"])
    return int(report["failed"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
