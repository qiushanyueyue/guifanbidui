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
    StagingStandardModel,
    StandardV2Model,
    StandardV2RelationModel,
    StandardV2SourceModel,
)
from app.sync.v2_pipeline import _content_hash  # noqa: E402


def import_seed_payload(db, payload: dict) -> dict[str, int]:
    """Replace reviewed V2 tables using a bounded number of database flushes."""

    db.query(StandardV2RelationModel).delete()
    db.query(StandardV2SourceModel).delete()
    db.query(StandardV2Model).delete()
    db.query(NormativeDocumentModel).delete()
    db.flush()

    by_key: dict[str, StandardV2Model] = {}
    source_specs: list[tuple[StandardV2Model, dict, str, datetime | None]] = []
    for raw_item in payload["standards"]:
        item = dict(raw_item)
        sources = list(item.pop("sources"))
        key = item.pop("key")
        standard = StandardV2Model(**item)
        db.add(standard)
        by_key[key] = standard
        for source in sources:
            fetched_at = datetime.fromisoformat(source["fetched_at"]) if source.get("fetched_at") else None
            staging_payload = {
                "source_name": source["source_name"],
                "source_url": source.get("source_url"),
                "raw_code": standard.code,
                "raw_name": standard.name,
                "raw_edition": standard.edition,
                "raw_status": source.get("observed_status"),
                "raw_text": "published V2 metadata seed",
                "raw_publish_date": None,
                "raw_implement_date": None,
                "raw_abolish_date": None,
                "raw_relation_text": None,
                "source_record_id": None,
            }
            source_specs.append((standard, source, _content_hash(staging_payload), fetched_at))
    db.flush()

    staging_by_key = {
        (row.source_name, row.content_hash): row
        for row in db.query(StagingStandardModel).all()
    }
    for standard, source, digest, fetched_at in source_specs:
        staging_key = (source["source_name"], digest)
        staged = staging_by_key.get(staging_key)
        if staged is None:
            staged = StagingStandardModel(
                source_name=source["source_name"],
                source_url=source.get("source_url"),
                raw_code=standard.code,
                raw_name=standard.name,
                raw_edition=standard.edition,
                raw_status=source.get("observed_status"),
                raw_text="published V2 metadata seed",
                content_hash=digest,
                fetched_at=fetched_at or datetime.utcnow(),
            )
            db.add(staged)
            staging_by_key[staging_key] = staged
        elif fetched_at is not None:
            staged.fetched_at = fetched_at
    db.flush()

    seen_evidence: set[tuple[int, int]] = set()
    for standard, source, digest, fetched_at in source_specs:
        staged = staging_by_key[(source["source_name"], digest)]
        evidence_key = (standard.id, staged.id)
        if evidence_key in seen_evidence:
            continue
        seen_evidence.add(evidence_key)
        db.add(StandardV2SourceModel(
            standard_id=standard.id,
            staging_id=staged.id,
            source_name=source["source_name"],
            source_url=source.get("source_url"),
            observed_status=source.get("observed_status"),
            fetched_at=fetched_at,
        ))
    db.add_all([
        StandardV2RelationModel(
            source_standard_id=by_key[item["source_key"]].id,
            target_standard_id=by_key[item["target_key"]].id,
            relation_type=item["relation_type"],
            raw_relation_text=item.get("raw_relation_text"),
        )
        for item in payload["relations"]
    ])
    db.add_all([NormativeDocumentModel(**item) for item in payload["normative_documents"]])
    db.commit()
    return {
        "standards": len(by_key),
        "relations": len(payload["relations"]),
        "normative_documents": len(payload["normative_documents"]),
    }


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
        print(import_seed_payload(db, payload))


if __name__ == "__main__":
    main()
