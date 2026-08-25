"""Rebuild pipeline from immutable staging evidence into publishable V2 rows."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.enums import StandardStatus, normalize_status
from app.models.models import (
    QuarantinedStandardModel,
    NormativeDocumentModel,
    StagingStandardModel,
    StandardV2Model,
    StandardV2RelationModel,
    StandardV2SourceModel,
)
from app.services.standard_normalizer import (
    clean_standard_name,
    normalized_name,
    parse_edition,
    parse_standard_code,
)
from app.sources.csres import has_mandatory_clause_repeal, parse_csres_replacement_text


@dataclass(frozen=True)
class PublishReport:
    total_raw: int
    published: int
    quarantined: int
    conflicts: int
    single_source: int
    cross_verified: int
    normative_documents: int


def _content_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def stage_record(
    db: Session,
    *,
    source_name: str,
    source_url: str | None,
    raw_code: str | None,
    raw_name: str | None,
    raw_edition: str | None = None,
    raw_status: str | None = None,
    raw_text: str | None = None,
    raw_publish_date: str | None = None,
    raw_implement_date: str | None = None,
    raw_abolish_date: str | None = None,
    raw_relation_text: str | None = None,
    source_record_id: str | None = None,
    sync_run_id: int | None = None,
) -> tuple[StagingStandardModel, bool]:
    """Append source evidence idempotently; never write the published table."""

    payload = {
        "source_name": source_name,
        "source_url": source_url,
        "raw_code": raw_code,
        "raw_name": raw_name,
        "raw_edition": raw_edition,
        "raw_status": raw_status,
        "raw_text": raw_text,
        "raw_publish_date": raw_publish_date,
        "raw_implement_date": raw_implement_date,
        "raw_abolish_date": raw_abolish_date,
        "raw_relation_text": raw_relation_text,
        "source_record_id": source_record_id,
    }
    digest = _content_hash(payload)
    existing = (
        db.query(StagingStandardModel)
        .filter(StagingStandardModel.source_name == source_name)
        .filter(StagingStandardModel.content_hash == digest)
        .first()
    )
    if existing is not None:
        return existing, False
    row = StagingStandardModel(
        **payload,
        sync_run_id=sync_run_id,
        content_hash=digest,
        parse_status="pending",
        fetched_at=datetime.utcnow(),
    )
    db.add(row)
    db.flush()
    return row, True


def _document_kind(name: str) -> str:
    if "通知" in name:
        return "notice"
    if "办法" in name:
        return "method"
    if "规定" in name:
        return "regulation"
    if "指南" in name or "导则" in name:
        return "guideline"
    return "standard"


def _status_decision(rows: list[StagingStandardModel]) -> tuple[str, str, bool, str | None]:
    usable = {
        row.source_name: normalize_status(row.raw_status).value
        for row in rows
        if normalize_status(row.raw_status) != StandardStatus.UNKNOWN
    }
    statuses = set(usable.values())
    if len(statuses) > 1:
        return "conflict", "conflict", True, json.dumps(usable, ensure_ascii=False, sort_keys=True)
    if not statuses:
        return "unknown", "unverified", False, None
    distinct_sources = {row.source_name for row in rows}
    verification = "cross_verified" if len(distinct_sources) > 1 else "single_source"
    return next(iter(statuses)), verification, False, None


def _code_aliases(code: str) -> set[str]:
    """Return conservative official-year aliases used by older catalogues."""

    aliases = {code}
    parsed = parse_standard_code(code)
    if parsed is None or parsed.year is None:
        return aliases
    if len(parsed.year) == 4 and parsed.year.startswith("19"):
        aliases.add(f"{parsed.prefix} {parsed.serial}-{parsed.year[2:]}")
    elif len(parsed.year) == 2:
        aliases.add(f"{parsed.prefix} {parsed.serial}-19{parsed.year}")
    return aliases


def _find_relation_target(db: Session, code: str) -> StandardV2Model | None:
    return (
        db.query(StandardV2Model)
        .filter(StandardV2Model.base_code.in_(_code_aliases(code)))
        .order_by(StandardV2Model.revision_year.desc().nullslast(), StandardV2Model.id)
        .first()
    )


def _quarantine(db: Session, row: StagingStandardModel, reason: str, detail: str) -> None:
    existing = (
        db.query(QuarantinedStandardModel)
        .filter(QuarantinedStandardModel.staging_id == row.id)
        .filter(QuarantinedStandardModel.reason_code == reason)
        .filter(QuarantinedStandardModel.resolved_at.is_(None))
        .first()
    )
    if existing is None:
        db.add(
            QuarantinedStandardModel(
                staging_id=row.id,
                reason_code=reason,
                reason_detail=detail,
            )
        )
    row.parse_status = "quarantined"
    row.parse_error = detail


def publish_staging(db: Session) -> PublishReport:
    """Normalize, deduplicate, reconcile, quarantine, then publish V2 candidates."""

    total_raw = db.query(StagingStandardModel).count()
    raw_rows = (
        db.query(StagingStandardModel)
        .filter(StagingStandardModel.parse_status.in_(["pending", "ok"]))
        .order_by(StagingStandardModel.id)
        .all()
    )
    documents_by_key = {
        (row.normalized_name, row.source_name): row
        for row in db.query(NormativeDocumentModel).all()
    }
    groups: dict[tuple[str, str | None], list[tuple[StagingStandardModel, Any, str, Any]]] = {}
    quarantined = 0
    normative_documents = 0
    for row in raw_rows:
        parsed = parse_standard_code(row.raw_code)
        if (parsed is None or parsed.year is None) and row.raw_text:
            try:
                raw_payload = json.loads(row.raw_text)
            except (TypeError, json.JSONDecodeError):
                raw_payload = {}
            title = raw_payload.get("title") if isinstance(raw_payload, dict) else None
            recovered = parse_standard_code(title)
            if recovered is not None and recovered.year is not None:
                parsed = recovered
                row.raw_code = recovered.normalized
        if parsed is None or parsed.year is None:
            name = clean_standard_name(row.raw_name)
            kind = _document_kind(name)
            if name and (kind != "standard" or not row.raw_code):
                document_key = (normalized_name(name), row.source_name)
                existing_document = documents_by_key.get(document_key)
                if existing_document is None:
                    existing_document = NormativeDocumentModel(
                        title=name,
                        normalized_name=normalized_name(name),
                        source_name=row.source_name,
                    )
                    db.add(existing_document)
                    documents_by_key[document_key] = existing_document
                    normative_documents += 1
                resolved_status = normalize_status(row.raw_status)
                existing_document.title = name
                existing_document.document_kind = kind if kind != "standard" else "unknown"
                existing_document.status = resolved_status.value
                existing_document.publish_date = row.raw_publish_date
                existing_document.implement_date = row.raw_implement_date
                existing_document.source_url = row.source_url
                existing_document.verification_level = (
                    "single_source" if resolved_status != StandardStatus.UNKNOWN else "unverified"
                )
                existing_document.raw_text = row.raw_text
                existing_document.last_verified_at = (
                    datetime.utcnow() if resolved_status != StandardStatus.UNKNOWN else None
                )
                row.parse_status = "ok"
                row.parse_error = None
                continue
            _quarantine(db, row, "invalid_code", "无法解析含年份的规范编号")
            quarantined += 1
            continue
        name = clean_standard_name(row.raw_name)
        if not name:
            _quarantine(db, row, "empty_name", "规范名称为空")
            quarantined += 1
            continue
        edition = parse_edition(" ".join(filter(None, [row.raw_edition, row.raw_name, row.raw_text])))
        explicit_edition = row.raw_edition or edition.edition
        groups.setdefault((parsed.normalized, explicit_edition), []).append((row, parsed, name, edition))
        row.parse_status = "ok"
        row.parse_error = None

    standards_by_identity = {
        (row.base_code, row.edition): row
        for row in db.query(StandardV2Model).all()
    }
    pending_evidence: list[tuple[StandardV2Model, StagingStandardModel]] = []
    published = conflicts = single_source = cross_verified = 0
    for (code, explicit_edition), entries in groups.items():
        rows = [entry[0] for entry in entries]
        names = {normalized_name(entry[2]): entry[2] for entry in entries}
        if len(names) > 1:
            for row in rows:
                _quarantine(db, row, "name_conflict", "同一编号和版本出现多个名称")
                quarantined += 1
            continue
        parsed = entries[0][1]
        name = next(iter(names.values()))
        # A previous pass may have classified the same source item as a
        # numberless document before its code was recovered from raw evidence.
        for source_name in {row.source_name for row in rows}:
            document_key = (normalized_name(name), source_name)
            stale_document = documents_by_key.pop(document_key, None)
            if stale_document is not None:
                db.delete(stale_document)
        edition = entries[0][3]
        revision_year = edition.revision_year
        if explicit_edition and revision_year is None:
            revision_year = parse_edition(explicit_edition).revision_year
        status, verification, source_conflict, conflict_details = _status_decision(rows)
        quality = "needs_review" if source_conflict else "publishable"
        identity = (code, explicit_edition)
        existing = standards_by_identity.get(identity)
        if existing is None:
            existing = StandardV2Model(base_code=code, edition=explicit_edition)
            db.add(existing)
            standards_by_identity[identity] = existing
            published += 1
        existing.code = code
        existing.normalized_code = code
        existing.standard_prefix = parsed.prefix
        existing.standard_number = parsed.serial
        existing.standard_year = parsed.year
        existing.name = name
        existing.normalized_name = normalized_name(name)
        existing.document_kind = _document_kind(name)
        existing.revision_year = revision_year
        existing.revision_status = "amended" if explicit_edition else "original"
        existing.status = status
        if any(row.raw_relation_text for row in rows):
            existing.mandatory_clause_status = "unknown"
        existing.publish_date = next((row.raw_publish_date for row in rows if row.raw_publish_date), None)
        existing.implement_date = next((row.raw_implement_date for row in rows if row.raw_implement_date), None)
        existing.abolish_date = next((row.raw_abolish_date for row in rows if row.raw_abolish_date), None)
        existing.verification_level = verification
        existing.source_conflict = source_conflict
        existing.conflict_details = conflict_details
        existing.data_quality_status = quality
        existing.first_seen_at = existing.first_seen_at or min(row.fetched_at for row in rows)
        existing.last_seen_at = max(row.fetched_at for row in rows)
        existing.last_verified_at = datetime.utcnow() if verification != "unverified" else None
        existing.published_at = datetime.utcnow() if quality == "publishable" else None
        for row in rows:
            pending_evidence.append((existing, row))
        conflicts += int(source_conflict)
        single_source += int(verification == "single_source")
        cross_verified += int(verification == "cross_verified")

    db.flush()
    evidence_keys = set(db.query(
        StandardV2SourceModel.standard_id,
        StandardV2SourceModel.staging_id,
    ).all())
    for standard, row in pending_evidence:
        evidence_key = (standard.id, row.id)
        if evidence_key in evidence_keys:
            continue
        evidence_keys.add(evidence_key)
        db.add(StandardV2SourceModel(
            standard_id=standard.id,
            staging_id=row.id,
            source_name=row.source_name,
            source_url=row.source_url,
            observed_status=row.raw_status,
            fetched_at=row.fetched_at,
        ))

    # Resolve directional replacement evidence only after every candidate is
    # present. Unresolved targets remain review evidence and never become
    # fabricated placeholder standards.
    # These rows are derived from staging evidence, so rebuild them instead of
    # retaining edges produced by an older parser. Seeded/manual relations have
    # no evidence_staging_id and are intentionally preserved.
    db.query(StandardV2RelationModel).filter(
        StandardV2RelationModel.evidence_staging_id.isnot(None)
    ).delete(synchronize_session=False)
    db.flush()
    standards_by_alias: dict[str, StandardV2Model] = {}
    for standard in standards_by_identity.values():
        for alias in _code_aliases(standard.base_code):
            current = standards_by_alias.get(alias)
            candidate_rank = (standard.revision_year or "", standard.id or 0)
            current_rank = (current.revision_year or "", current.id or 0) if current is not None else ("", -1)
            if current is None or candidate_rank > current_rank:
                standards_by_alias[alias] = standard
    relation_keys = set(db.query(
        StandardV2RelationModel.source_standard_id,
        StandardV2RelationModel.target_standard_id,
        StandardV2RelationModel.relation_type,
    ).all())
    relation_rows = [row for row in raw_rows if row.raw_relation_text]
    for evidence in relation_rows:
        source_code = parse_standard_code(evidence.raw_code)
        if source_code is None:
            continue
        source_standard = standards_by_alias.get(source_code.normalized)
        if source_standard is None:
            continue
        if has_mandatory_clause_repeal(evidence.raw_relation_text):
            source_standard.mandatory_clause_status = "partially_repealed"
        replaces, replaced_by = parse_csres_replacement_text(evidence.raw_relation_text)
        for relation_type, codes in (("replaces", replaces), ("replaced_by", replaced_by)):
            for target_code in codes:
                target_standard = next(
                    (standards_by_alias.get(alias) for alias in _code_aliases(target_code) if standards_by_alias.get(alias) is not None),
                    None,
                )
                if target_standard is None:
                    existing_issue = (
                        db.query(QuarantinedStandardModel)
                        .filter(QuarantinedStandardModel.staging_id == evidence.id)
                        .filter(QuarantinedStandardModel.reason_code == "unresolved_relation")
                        .filter(QuarantinedStandardModel.resolved_at.is_(None))
                        .first()
                    )
                    if existing_issue is None:
                        db.add(
                            QuarantinedStandardModel(
                                staging_id=evidence.id,
                                normalized_code=source_standard.base_code,
                                normalized_name=source_standard.normalized_name,
                                reason_code="unresolved_relation",
                                reason_detail=f"{relation_type}: {target_code}",
                            )
                        )
                    source_standard.data_quality_status = "needs_review"
                    continue
                if target_standard.id == source_standard.id:
                    source_standard.data_quality_status = "needs_review"
                    continue
                relation_key = (source_standard.id, target_standard.id, relation_type)
                if relation_key not in relation_keys:
                    relation_keys.add(relation_key)
                    db.add(
                        StandardV2RelationModel(
                            source_standard_id=source_standard.id,
                            target_standard_id=target_standard.id,
                            relation_type=relation_type,
                            raw_relation_text=evidence.raw_relation_text,
                            evidence_staging_id=evidence.id,
                        )
                    )
    db.commit()
    return PublishReport(
        total_raw=total_raw,
        published=published,
        quarantined=quarantined,
        conflicts=conflicts,
        single_source=single_source,
        cross_verified=cross_verified,
        normative_documents=normative_documents,
    )
