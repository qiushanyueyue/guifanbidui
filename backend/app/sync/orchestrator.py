"""Incremental/verification sync orchestration."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import ParseStatus, VerificationLevel
from app.models.models import StandardRelationModel, StandardSourceModel, SyncRunModel
from app.models.models import StandardModel
from app.repositories.standard_repo import StandardRepo
from app.services.standard_normalizer import extract_standard_codes
from app.sources import (
    CsresSource,
    MohurdSource,
    OpenStdSource,
    SoujianzhuSource,
    SourceError,
    SourceRecord,
    SourceUnavailable,
    SamrSource,
)
from app.sync.resolver import resolve_canonical_standard

logger = logging.getLogger(__name__)


SOURCE_FACTORIES = {
    "mohurd": MohurdSource,
    "samr": SamrSource,
    "openstd": OpenStdSource,
    "soujianzhu": SoujianzhuSource,
    "csres": CsresSource,
}


def available_source_names() -> list[str]:
    return list(SOURCE_FACTORIES)


def build_source(name: str):
    try:
        return SOURCE_FACTORIES[name]()
    except KeyError as exc:
        raise ValueError(f"unknown source: {name}") from exc


def _upsert_source_row(db: Session, standard_id: int, record: SourceRecord, *, fetched_at: datetime) -> tuple[StandardSourceModel, bool]:
    source_code = record.normalized_code or record.code
    source_row = (
        db.query(StandardSourceModel)
        .filter(StandardSourceModel.standard_id == standard_id)
        .filter(StandardSourceModel.source_name == record.source_name)
        .filter(StandardSourceModel.source_code == source_code)
        .first()
    )
    created = source_row is None
    if source_row is None:
        source_row = StandardSourceModel(
            standard_id=standard_id,
            source_name=record.source_name,
            source_code=source_code,
        )
        db.add(source_row)
    source_row.source_url = record.source_url
    source_row.source_name_text = record.name
    source_row.source_status = record.source_status.value if hasattr(record.source_status, "value") else str(record.source_status or "")
    source_row.publish_date = record.publish_date
    source_row.implement_date = record.implement_date
    source_row.abolish_date = record.abolish_date
    source_row.replaces = record.replaces
    source_row.replaced_by = record.replaced_by
    source_row.source_updated_at = record.source_updated_at
    source_row.fetched_at = fetched_at
    source_row.content_hash = record.content_hash
    source_row.parse_status = ParseStatus.OK.value
    source_row.parse_error = None
    source_row.raw_payload = json.dumps(record.raw_payload, ensure_ascii=False, sort_keys=True)
    db.flush()
    return source_row, created


def _sync_relations(db: Session, standard, record: SourceRecord, source_row: StandardSourceModel) -> None:
    relation_specs = []
    for code in extract_standard_codes(record.replaces or ""):
        relation_specs.append(("replaces", code.normalized))
    for code in extract_standard_codes(record.replaced_by or ""):
        relation_specs.append(("replaced_by", code.normalized))
    for relation_type, target_code in relation_specs:
        if target_code == standard.normalized_code:
            continue
        target = StandardRepo.get_by_code(db, target_code)
        if target is None:
            target, _ = StandardRepo.upsert(
                db,
                code=target_code,
                name="",
                status="unknown",
                verification_level=VerificationLevel.UNVERIFIED,
            )
        exists = (
            db.query(StandardRelationModel)
            .filter(StandardRelationModel.source_standard_id == standard.id)
            .filter(StandardRelationModel.target_standard_id == target.id)
            .filter(StandardRelationModel.relation_type == relation_type)
            .first()
        )
        if exists is None:
            db.add(
                StandardRelationModel(
                    source_standard_id=standard.id,
                    target_standard_id=target.id,
                    relation_type=relation_type,
                    evidence_source_id=source_row.id,
                )
            )


def sync_one_source(
    db: Session,
    source_name: str,
    *,
    mode: str = "incremental",
    limit: int = 100,
    adapter=None,
) -> SyncRunModel:
    """Run one source and persist a traceable result, including failures."""

    run = SyncRunModel(source=source_name, status="running", started_at=datetime.utcnow())
    db.add(run)
    db.commit()
    adapter = adapter or build_source(source_name)
    try:
        records = adapter.fetch_recent(limit=limit)
        run.found = len(records)
        touched: set[int] = set()
        for record in records:
            try:
                record = adapter.normalize(record)
                if not record.normalized_code:
                    raise ValueError("source record has no normalizable standard code")
                standard, created = StandardRepo.upsert(
                    db,
                    code=record.normalized_code,
                    name=record.name,
                    edition=record.edition,
                    revision_year=record.revision_year,
                    amendment=record.amendment,
                    status=record.status,
                    publish_date=record.publish_date,
                    implement_date=record.implement_date,
                    abolish_date=record.abolish_date,
                    replaces=record.replaces,
                    replaced_by=record.replaced_by,
                    issuing_authority=record.issuing_authority,
                    canonical_source=record.source_name,
                    canonical_url=record.source_url,
                    soujianzhu_url=record.source_url if record.source_name == "soujianzhu" else None,
                    verification_level=VerificationLevel.SINGLE_SOURCE,
                    source_updated_at=record.source_updated_at,
                )
                before = (
                    db.query(StandardSourceModel)
                    .filter(StandardSourceModel.standard_id == standard.id)
                    .filter(StandardSourceModel.source_name == record.source_name)
                    .filter(StandardSourceModel.source_code == record.normalized_code)
                    .first()
                )
                old_hash = before.content_hash if before else None
                source_row, _ = _upsert_source_row(db, standard.id, record, fetched_at=datetime.utcnow())
                _sync_relations(db, standard, record, source_row)
                if created:
                    run.inserted += 1
                elif old_hash == record.content_hash:
                    run.unchanged += 1
                else:
                    run.updated += 1
                touched.add(standard.id)
            except Exception as exc:
                run.failed += 1
                logger.warning(
                    "sync source=%s standard_code=%s parse_result=failed error=%s",
                    source_name,
                    getattr(record, "code", ""),
                    exc.__class__.__name__,
                )
        for standard_id in touched:
            resolve_canonical_standard(db, standard_id)
        run.status = "partial" if run.failed else "success"
        run.finished_at = datetime.utcnow()
        db.commit()
        return run
    except SourceError as exc:
        run.status = "failed"
        run.error_message = f"{exc.category}: {exc.__class__.__name__}"
        run.finished_at = datetime.utcnow()
        db.commit()
        logger.warning("sync source=%s failed category=%s", source_name, exc.category)
        return run
    except Exception as exc:
        run.status = "failed"
        run.error_message = f"unexpected: {exc.__class__.__name__}"
        run.finished_at = datetime.utcnow()
        db.commit()
        logger.exception("sync source=%s failed unexpectedly", source_name)
        return run


def run_sync(
    db: Session,
    *,
    source_names: Iterable[str] | None = None,
    mode: str = "incremental",
    limit: int = 100,
) -> list[SyncRunModel]:
    names = list(source_names or ("samr", "mohurd", "openstd", "soujianzhu", "csres"))
    return [sync_one_source(db, name, mode=mode, limit=limit) for name in names]


def verify_existing_standards(
    db: Session,
    *,
    source_name: str = "csres",
    limit: int = 600,
) -> SyncRunModel:
    """Re-check the oldest verified rows in a bounded batch."""

    run = SyncRunModel(source=source_name, status="running", started_at=datetime.utcnow())
    db.add(run)
    db.commit()
    adapter = build_source(source_name)
    standards = db.scalars(
        select(StandardModel)
        .where(StandardModel.status.in_(["current", "upcoming", "partially_amended"]))
        .order_by(StandardModel.last_verified_at.asc().nullsfirst())
        .limit(max(1, limit))
    ).all()
    run.found = len(standards)
    try:
        for standard in standards:
            url = standard.canonical_url or standard.url
            if not url:
                run.failed += 1
                continue
            try:
                record = adapter.fetch_detail(url)
                if record is None:
                    run.failed += 1
                    continue
                record = adapter.normalize(record)
                if not record.normalized_code:
                    run.failed += 1
                    continue
                source_row, _ = _upsert_source_row(db, standard.id, record, fetched_at=datetime.utcnow())
                _sync_relations(db, standard, record, source_row)
                resolve_canonical_standard(db, standard.id)
                run.updated += 1
            except Exception as exc:
                run.failed += 1
                logger.warning("verify source=%s code=%s error=%s", source_name, standard.code, exc.__class__.__name__)
        run.status = "partial" if run.failed else "success"
    except Exception as exc:
        run.status = "failed"
        run.error_message = f"unexpected: {exc.__class__.__name__}"
        logger.exception("verify source=%s failed", source_name)
    run.finished_at = datetime.utcnow()
    db.commit()
    return run
