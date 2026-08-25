#!/usr/bin/env python3
"""Audit the supplied Excel catalogue against the reviewed V2 seed."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.excel_catalog_audit import (  # noqa: E402
    audit_catalog,
    classify_unparseable_documents,
    write_audit_report,
)


EXCEL_SUPPLEMENT_DELTA = {
    "baseline_canonical": 1716,
    "current_canonical": 1738,
    "added_canonical": 22,
    "components": {
        "unique_excel_missing": 20,
        "name_conflict_supplement": ["GB/T 37127-2018"],
        "version_conflict_candidate": ["GB 50046-2018"],
    },
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--catalog",
        default="/Volumes/yue/Download/规范目录库20251011.xlsx",
        help="read-only Excel catalogue path",
    )
    parser.add_argument("--seed", default=str(ROOT / "data" / "standards_v2_seed.json"))
    parser.add_argument(
        "--output",
        default=str(ROOT / "artifacts" / "excel_catalog_audit_20251011.json"),
    )
    args = parser.parse_args()
    report = audit_catalog(args.catalog, seed_path=args.seed)
    normative_report = classify_unparseable_documents(args.catalog, seed_path=args.seed)
    output = write_audit_report(
        report,
        args.output,
        metadata={
            "supplement_delta": EXCEL_SUPPLEMENT_DELTA,
            "normative_document_audit": normative_report.to_dict(),
        },
    )
    payload = report.to_dict()
    payload.pop("rows", None)
    payload["output"] = str(output)
    payload["missing_codes"] = sorted(
        {row.normalized_code for row in report.missing_rows if row.normalized_code}
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
