#!/usr/bin/env python3
"""Merge safe, unnumbered Excel documents into V2 normative_documents."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.excel_catalog_audit import (  # noqa: E402
    classify_unparseable_documents,
)
from app.services.standard_normalizer import normalized_name  # noqa: E402


def merge_normative_documents(
    payload: dict[str, Any],
    audit_report,
) -> list[dict[str, Any]]:
    """Append only staged Excel documents; leave ordinary standards untouched."""

    if payload.get("schema_version") != 2:
        raise ValueError("unsupported V2 seed schema")
    if not isinstance(payload.get("standards"), list):
        raise ValueError("V2 seed standards must be a list")
    documents = payload.setdefault("normative_documents", [])
    if not isinstance(documents, list):
        raise ValueError("V2 seed normative_documents must be a list")
    existing_names = {
        normalized_name(item.get("title") or item.get("normalized_name") or "")
        for item in documents
    }
    additions: list[dict[str, Any]] = []
    for item in audit_report.staged_documents:
        candidate = copy.deepcopy(item)
        key = normalized_name(candidate.get("title") or candidate.get("normalized_name") or "")
        if not key or key in existing_names:
            continue
        candidate["normalized_name"] = key
        candidate["status"] = "unknown"
        candidate["verification_level"] = "unverified"
        candidate["source_name"] = "excel_catalog_20251011"
        candidate["source_url"] = None
        documents.append(candidate)
        additions.append(candidate)
        existing_names.add(key)
    return additions


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--catalog",
        default="/Volumes/yue/Download/规范目录库20251011.xlsx",
    )
    parser.add_argument("--seed", default=str(ROOT / "data" / "standards_v2_seed.json"))
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    output = Path(args.output or args.seed)
    payload = json.loads(Path(args.seed).read_text(encoding="utf-8"))
    standards_before = json.dumps(payload.get("standards"), ensure_ascii=False, sort_keys=True)
    audit_report = classify_unparseable_documents(args.catalog, seed_path=args.seed)
    additions = merge_normative_documents(payload, audit_report)
    standards_after = json.dumps(payload.get("standards"), ensure_ascii=False, sort_keys=True)
    if standards_before != standards_after:
        raise RuntimeError("ordinary standards changed while merging normative documents")
    output.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(
        {
            "output": str(output),
            "existing_normative_document": audit_report.summary["existing_normative_document"],
            "staged_normative_document_rows": audit_report.summary["staged_normative_document"],
            "staged_normative_documents": len(additions),
            "manual_review": audit_report.summary["manual_review"],
            "standards": len(payload["standards"]),
            "normative_documents": len(payload["normative_documents"]),
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
