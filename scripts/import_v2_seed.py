#!/usr/bin/env python3
"""Idempotently publish the reviewed V2 metadata seed to the configured DB."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.db_init import init_db  # noqa: E402
from app.models.base import SessionLocal  # noqa: E402
from app.models.models import (  # noqa: E402
    NormativeDocumentModel,
    StandardV2Model,
    StandardV2RelationModel,
    StandardV2SourceModel,
)
from app.sync.v2_pipeline import stage_record  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", default=str(ROOT / "data" / "standards_v2_seed.json"))
    args = parser.parse_args()
    payload = json.loads(Path(args.seed).read_text(encoding="utf-8"))
    if payload.get("schema_version") != 2:
        raise SystemExit("unsupported seed schema")
    init_db()
    with SessionLocal() as db:
        # Replace only derived V2 publication tables. Legacy tables and raw
        # staging evidence remain intact for rollback and audit.
        db.query(StandardV2RelationModel).delete()
        db.query(StandardV2SourceModel).delete()
        db.query(StandardV2Model).delete()
        db.query(NormativeDocumentModel).delete()
        db.flush()
        by_key: dict[str, StandardV2Model] = {}
        for item in payload["standards"]:
            sources = item.pop("sources")
            key = item.pop("key")
            standard = StandardV2Model(**item)
            db.add(standard)
            db.flush()
            by_key[key] = standard
            seen_staging_ids: set[int] = set()
            for source in sources:
                fetched_at = datetime.fromisoformat(source["fetched_at"]) if source.get("fetched_at") else None
                staged, _ = stage_record(
                    db,
                    source_name=source["source_name"],
                    source_url=source.get("source_url"),
                    raw_code=standard.code,
                    raw_name=standard.name,
                    raw_edition=standard.edition,
                    raw_status=source.get("observed_status"),
                    raw_text="published V2 metadata seed",
                )
                if fetched_at:
                    staged.fetched_at = fetched_at
                if staged.id in seen_staging_ids:
                    continue
                seen_staging_ids.add(staged.id)
                db.add(StandardV2SourceModel(
                    standard_id=standard.id,
                    staging_id=staged.id,
                    source_name=source["source_name"],
                    source_url=source.get("source_url"),
                    observed_status=source.get("observed_status"),
                    fetched_at=fetched_at,
                ))
        for item in payload["relations"]:
            db.add(StandardV2RelationModel(
                source_standard_id=by_key[item["source_key"]].id,
                target_standard_id=by_key[item["target_key"]].id,
                relation_type=item["relation_type"],
                raw_relation_text=item.get("raw_relation_text"),
            ))
        for item in payload["normative_documents"]:
            db.add(NormativeDocumentModel(**item))
        db.commit()
        print({"standards": len(by_key), "relations": len(payload["relations"]), "normative_documents": len(payload["normative_documents"])})


if __name__ == "__main__":
    main()
