#!/usr/bin/env python3
"""Stage explicitly unverified Excel candidates for V2 review."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.models.base import SessionLocal  # noqa: E402
from app.services.excel_catalog_audit import CATALOG_SOURCE_NAME, audit_catalog  # noqa: E402
from app.sync.v2_pipeline import stage_record  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--catalog",
        default="/Volumes/yue/Download/规范目录库20251011.xlsx",
    )
    parser.add_argument("--seed", default=str(ROOT / "data" / "standards_v2_seed.json"))
    parser.add_argument(
        "--code",
        action="append",
        required=True,
        help="candidate code to stage as unknown; repeat for each code",
    )
    parser.add_argument(
        "--include-version-conflicts",
        action="store_true",
        help="also stage rows classified as version_conflict, still as unknown",
    )
    args = parser.parse_args()
    wanted = {str(value).strip().upper() for value in args.code}
    report = audit_catalog(args.catalog, seed_path=args.seed)
    allowed_classes = {"missing"}
    if args.include_version_conflicts:
        allowed_classes.add("version_conflict")
    selected = [
        row
        for row in report.rows
        if row.classification in allowed_classes
        and row.normalized_code
        and row.normalized_code.upper() in wanted
    ]
    if len({row.normalized_code for row in selected}) != len(wanted):
        missing = sorted(wanted - {row.normalized_code.upper() for row in selected})
        raise SystemExit(f"requested candidates not found in audit: {missing}")

    staged = 0
    with SessionLocal() as db:
        for row in selected:
            _, inserted = stage_record(
                db,
                source_name=CATALOG_SOURCE_NAME,
                source_url=None,
                source_record_id=f"{row.excel_sheet}:{row.excel_row}",
                raw_code=row.normalized_code,
                raw_name=row.name,
                raw_edition=row.edition,
                raw_status=None,
                raw_text=json.dumps(
                    {
                        "source_file": "规范目录库20251011.xlsx",
                        "sheet": row.excel_sheet,
                        "excel_row": row.excel_row,
                        "raw_value": row.raw_value,
                        "verification": "unknown; Excel catalog is not an authority",
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            )
            staged += int(inserted)
        db.commit()
    print({"selected_rows": len(selected), "inserted": staged, "source_name": CATALOG_SOURCE_NAME})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
