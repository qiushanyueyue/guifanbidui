#!/usr/bin/env python3
"""Publish staged evidence and write the machine-readable V2 quality report."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.models.base import SessionLocal  # noqa: E402
from app.models.models import (  # noqa: E402
    NormativeDocumentModel,
    QuarantinedStandardModel,
    StagingStandardModel,
    StandardV2Model,
    StandardV2RelationModel,
)
from app.services.data_quality import validate_relation_edges  # noqa: E402
from app.sync.v2_pipeline import publish_staging  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ROOT / "artifacts" / "data_quality_report.json"))
    parser.add_argument("--retry-quarantine", action="store_true")
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with SessionLocal() as db:
        if args.retry_quarantine:
            issues = (
                db.query(QuarantinedStandardModel)
                .filter(QuarantinedStandardModel.resolved_at.is_(None))
                .all()
            )
            for issue in issues:
                issue.resolved_at = datetime.now(timezone.utc).replace(tzinfo=None)
                if issue.staging_id:
                    staging = db.get(StagingStandardModel, issue.staging_id)
                    if staging is not None and staging.parse_status == "quarantined":
                        staging.parse_status = "pending"
                        staging.parse_error = None
            db.commit()
        result = publish_staging(db)
        status_counts = dict(
            db.query(StandardV2Model.status, func.count(StandardV2Model.id))
            .group_by(StandardV2Model.status)
            .all()
        )
        verification_counts = dict(
            db.query(StandardV2Model.verification_level, func.count(StandardV2Model.id))
            .group_by(StandardV2Model.verification_level)
            .all()
        )
        quality_counts = dict(
            db.query(StandardV2Model.data_quality_status, func.count(StandardV2Model.id))
            .group_by(StandardV2Model.data_quality_status)
            .all()
        )
        relation_rows = db.query(StandardV2RelationModel).all()
        edges = list(
            {
                (
                    row.target_standard_id if row.relation_type == "replaces" else row.source_standard_id,
                    row.source_standard_id if row.relation_type == "replaces" else row.target_standard_id,
                )
                for row in relation_rows
                if row.relation_type in {"replaces", "replaced_by"}
            }
        )
        known_ids = {row[0] for row in db.query(StandardV2Model.id).all()}
        relation_quality = validate_relation_edges(edges, known_ids=known_ids)
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_raw": db.query(StagingStandardModel).count(),
            "total_canonical": db.query(StandardV2Model).count(),
            "normative_documents": db.query(NormativeDocumentModel).count(),
            "inserted": result.published,
            "updated": max(0, db.query(StandardV2Model).count() - result.published),
            "duplicates_merged": max(
                0,
                db.query(StagingStandardModel).filter(StagingStandardModel.parse_status.in_(["pending", "ok"])).count()
                - db.query(StandardV2Model).count()
                - db.query(NormativeDocumentModel).count(),
            ),
            "legacy_only": 0,
            "single_source": verification_counts.get("single_source", 0),
            "cross_verified": verification_counts.get("cross_verified", 0),
            "unknown": status_counts.get("unknown", 0),
            "conflicts": status_counts.get("conflict", 0),
            "suspect": quality_counts.get("needs_review", 0),
            "quarantined": db.query(QuarantinedStandardModel).filter(QuarantinedStandardModel.resolved_at.is_(None)).count(),
            "invalid_relation": len(relation_quality.self_relations) + len(relation_quality.cycles) + len(relation_quality.missing_targets),
            "broken_url": 0,
            "parse_failed": db.query(StagingStandardModel).filter(StagingStandardModel.parse_status.in_(["failed", "not_found"])).count(),
            "relations": len(relation_rows),
            "publishable": relation_quality.is_publishable,
        }
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if relation_quality.is_publishable else 2


if __name__ == "__main__":
    raise SystemExit(main())
