#!/usr/bin/env python3
"""Export the publishable V2 metadata snapshot without copyrighted documents."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.models.base import SessionLocal  # noqa: E402
from app.models.models import (  # noqa: E402
    NormativeDocumentModel,
    StandardV2Model,
    StandardV2RelationModel,
    StandardV2SourceModel,
)


STANDARD_FIELDS = [
    "code", "normalized_code", "base_code", "standard_prefix", "standard_number", "standard_year",
    "name", "normalized_name", "document_kind", "edition", "revision_year", "revision_status", "amendment",
    "status", "mandatory_clause_status", "publish_date", "implement_date", "abolish_date", "issuing_authority",
    "verification_level", "source_conflict", "conflict_details", "data_quality_status",
]
DOCUMENT_FIELDS = [
    "title", "normalized_name", "document_number", "document_kind", "status", "publish_date", "implement_date",
    "source_name", "source_url", "verification_level",
]


def _key(row: StandardV2Model) -> str:
    return f"{row.base_code}|{row.edition or ''}"


def main() -> None:
    output = ROOT / "data" / "standards_v2_seed.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    with SessionLocal() as db:
        standards = []
        rows = db.query(StandardV2Model).filter(StandardV2Model.data_quality_status != "quarantined").order_by(StandardV2Model.id).all()
        by_id = {row.id: row for row in rows}
        for row in rows:
            item = {field: getattr(row, field) for field in STANDARD_FIELDS}
            item["key"] = _key(row)
            item["sources"] = [
                {
                    "source_name": source.source_name,
                    "source_url": source.source_url,
                    "observed_status": source.observed_status,
                    "fetched_at": source.fetched_at.isoformat() if source.fetched_at else None,
                }
                for source in db.query(StandardV2SourceModel).filter_by(standard_id=row.id).order_by(StandardV2SourceModel.id)
            ]
            standards.append(item)
        relations = [
            {
                "source_key": _key(by_id[row.source_standard_id]),
                "target_key": _key(by_id[row.target_standard_id]),
                "relation_type": row.relation_type,
                "raw_relation_text": row.raw_relation_text,
            }
            for row in db.query(StandardV2RelationModel).order_by(StandardV2RelationModel.id)
            if row.source_standard_id in by_id and row.target_standard_id in by_id
        ]
        documents = [
            {field: getattr(row, field) for field in DOCUMENT_FIELDS}
            for row in db.query(NormativeDocumentModel).order_by(NormativeDocumentModel.id)
        ]
    payload = {"schema_version": 2, "standards": standards, "relations": relations, "normative_documents": documents}
    output.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print({"standards": len(standards), "relations": len(relations), "normative_documents": len(documents), "output": str(output)})


if __name__ == "__main__":
    main()
