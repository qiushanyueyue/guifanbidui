"""Freshness-aware live verification for the primary lookup flow."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.enums import StandardStatus, VerificationLevel
from app.models.models import StandardModel, StandardV2Model, StandardV2SourceModel
from app.repositories.standard_repo import StandardRepo
from app.services.standard_normalizer import normalize_standard_code, normalized_name, parse_standard_code
from app.sources import SourceError, SourceRecord
from app.sync.orchestrator import _upsert_source_row, build_source
from app.sync.resolver import resolve_canonical_standard
from app.sync.v2_pipeline import stage_record

OFFICIAL_ORDER = ("mohurd", "samr", "openstd")
THIRD_PARTY_ORDER = ("csres", "soujianzhu")


@dataclass(frozen=True)
class LiveVerification:
    status: StandardStatus
    verification_level: VerificationLevel
    records: tuple[SourceRecord, ...]
    source_conflict: bool = False


def freshness_days() -> int:
    try:
        return max(1, int(os.getenv("STANDARD_CACHE_FRESH_DAYS", "30")))
    except ValueError:
        return 30


def live_refresh_enabled() -> bool:
    configured = os.getenv("ENABLE_LIVE_STANDARD_REFRESH")
    if configured is not None:
        return configured.strip().lower() in {"1", "true", "yes", "on"}
    # Production has a persistent database. Local/test SQLite stays offline
    # unless explicitly enabled, avoiding surprising network calls in tests.
    return bool(os.getenv("DATABASE_URL", "").strip())


def cache_is_fresh(standard: object, *, now: datetime | None = None) -> bool:
    status = StandardStatus(str(getattr(standard, "status", "unknown") or "unknown"))
    verified_at = getattr(standard, "last_verified_at", None)
    if status in {StandardStatus.UNKNOWN, StandardStatus.CONFLICT} or verified_at is None:
        return False
    reference = now or datetime.now(UTC).replace(tzinfo=None)
    if getattr(verified_at, "tzinfo", None) is not None:
        verified_at = verified_at.replace(tzinfo=None)
    return verified_at >= reference - timedelta(days=freshness_days())


def _matches(record: SourceRecord, standard: object) -> bool:
    if record.status == StandardStatus.UNKNOWN:
        return False
    expected_code = normalize_standard_code(getattr(standard, "normalized_code", None) or getattr(standard, "code", None))
    if record.normalized_code != expected_code:
        return False
    expected_name = normalized_name(getattr(standard, "normalized_name", None) or getattr(standard, "name", None))
    observed_name = normalized_name(record.name)
    return not expected_name or (bool(observed_name) and expected_name == observed_name)


def _fetch_one(source_name: str, standard: object, source_urls: dict[str, str], factory) -> SourceRecord | None:
    adapter = factory(source_name)
    try:
        url = source_urls.get(source_name)
        records = [adapter.fetch_detail(url)] if url else adapter.search(str(getattr(standard, "code", "")))
    except (SourceError, NotImplementedError):
        return None
    for record in records:
        if record is None:
            continue
        normalized = adapter.normalize(record)
        if _matches(normalized, standard):
            return normalized
    return None


def verify_live(
    standard: object,
    *,
    source_urls: dict[str, str] | None = None,
    factory=build_source,
) -> LiveVerification | None:
    urls = source_urls or {}
    for source_name in OFFICIAL_ORDER:
        record = _fetch_one(source_name, standard, urls, factory)
        if record is not None:
            return LiveVerification(record.status, VerificationLevel.OFFICIAL, (record,))

    records = tuple(
        record
        for source_name in THIRD_PARTY_ORDER
        if (record := _fetch_one(source_name, standard, urls, factory)) is not None
    )
    if not records:
        return None
    if len(records) == 1:
        return LiveVerification(records[0].status, VerificationLevel.SINGLE_SOURCE, records)
    statuses = {record.status for record in records}
    names = {normalized_name(record.name) for record in records}
    relations = {
        ((record.replaces or "").strip(), (record.replaced_by or "").strip())
        for record in records
    }
    if "" in names or len(names) != 1 or len(statuses) != 1 or len(relations) != 1:
        return LiveVerification(StandardStatus.CONFLICT, VerificationLevel.CONFLICT, records, True)
    return LiveVerification(next(iter(statuses)), VerificationLevel.CROSS_VERIFIED, records)


def _code_family(code: str | None) -> tuple[str, str, str | None]:
    parsed = parse_standard_code(code)
    if parsed is None:
        return "", "", None
    return parsed.prefix.replace("/T", ""), parsed.serial, parsed.year


def _discovery_match(record: SourceRecord, *, code: str | None, name: str | None) -> bool:
    if record.status == StandardStatus.UNKNOWN:
        return False
    wanted_code = normalize_standard_code(code)
    wanted_name = normalized_name(name)
    same_code = bool(wanted_code) and record.normalized_code == wanted_code
    wanted_family = _code_family(wanted_code)
    same_family = bool(wanted_family[0] and wanted_family[1]) and (
        _code_family(record.normalized_code) == wanted_family
    )
    same_name = bool(wanted_name) and normalized_name(record.name) == wanted_name
    if wanted_code:
        return (same_code or same_family) and (not wanted_name or same_name)
    return same_name


def _discover_one(
    source_name: str,
    *,
    code: str | None,
    name: str | None,
    factory,
) -> SourceRecord | None:
    adapter = factory(source_name)
    queries = tuple(dict.fromkeys(item for item in (code, name) if item and item.strip()))
    for query in queries:
        try:
            records = adapter.search(query)
        except (SourceError, NotImplementedError):
            continue
        normalized_records = [adapter.normalize(record) for record in records if record is not None]
        candidates = [
            record for record in normalized_records if _discovery_match(record, code=code, name=name)
        ]
        if candidates:
            candidates.sort(key=lambda record: record.normalized_code != normalize_standard_code(code))
            return candidates[0]
    return None


def discover_live(
    *,
    code: str | None,
    name: str | None,
    factory=build_source,
) -> LiveVerification | None:
    """Find a missing local record from bounded live metadata queries."""

    for source_name in OFFICIAL_ORDER:
        record = _discover_one(source_name, code=code, name=name, factory=factory)
        if record is not None:
            return LiveVerification(record.status, VerificationLevel.OFFICIAL, (record,))
    records = tuple(
        record
        for source_name in THIRD_PARTY_ORDER
        if (record := _discover_one(source_name, code=code, name=name, factory=factory)) is not None
    )
    if not records:
        return None
    if len(records) == 1:
        return LiveVerification(records[0].status, VerificationLevel.SINGLE_SOURCE, records)
    statuses = {record.status for record in records}
    names = {normalized_name(record.name) for record in records}
    relations = {
        ((record.replaces or "").strip(), (record.replaced_by or "").strip())
        for record in records
    }
    if "" in names or len(names) != 1 or len(statuses) != 1 or len(relations) != 1:
        return LiveVerification(StandardStatus.CONFLICT, VerificationLevel.CONFLICT, records, True)
    return LiveVerification(next(iter(statuses)), VerificationLevel.CROSS_VERIFIED, records)


def persist_discovered_standard(
    db: Session,
    outcome: LiveVerification,
    *,
    use_v2: bool,
) -> StandardModel | StandardV2Model | None:
    """Create the canonical row for a successful query-time discovery."""

    if not outcome.records:
        return None
    record = outcome.records[0]
    now = datetime.now(UTC).replace(tzinfo=None)
    if not use_v2:
        standard, _ = StandardRepo.upsert(
            db,
            code=record.normalized_code,
            name=record.name,
            edition=record.edition,
            revision_year=record.revision_year,
            amendment=record.amendment,
            status=outcome.status,
            publish_date=record.publish_date,
            implement_date=record.implement_date,
            abolish_date=record.abolish_date,
            replaces=record.replaces,
            replaced_by=record.replaced_by,
            issuing_authority=record.issuing_authority,
            canonical_source=record.source_name,
            canonical_url=record.source_url,
            soujianzhu_url=record.source_url if record.source_name == "soujianzhu" else None,
            verification_level=outcome.verification_level,
        )
        persist_live_verification(db, standard, outcome)
        return standard

    parsed = parse_standard_code(record.normalized_code)
    if parsed is None:
        return None
    standard = StandardV2Model(
        code=record.normalized_code,
        normalized_code=record.normalized_code,
        base_code=parsed.base_code,
        standard_prefix=parsed.prefix,
        standard_number=parsed.serial,
        standard_year=parsed.year,
        name=record.name,
        normalized_name=normalized_name(record.name),
        edition=record.edition,
        revision_year=record.revision_year,
        revision_status="amended" if record.edition or record.amendment else "original",
        amendment=record.amendment,
        status=outcome.status.value,
        mandatory_clause_status="unknown",
        publish_date=record.publish_date,
        implement_date=record.implement_date,
        abolish_date=record.abolish_date,
        issuing_authority=record.issuing_authority,
        verification_level=outcome.verification_level.value,
        source_conflict=outcome.source_conflict,
        data_quality_status="publishable",
        first_seen_at=now,
        last_seen_at=now,
        last_verified_at=now,
        published_at=now,
    )
    db.add(standard)
    db.flush()
    persist_live_verification(db, standard, outcome)
    return standard


def persist_live_verification(db: Session, standard: object, outcome: LiveVerification) -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    if isinstance(standard, StandardModel):
        for record in outcome.records:
            _upsert_source_row(db, standard.id, record, fetched_at=now)
        resolve_canonical_standard(db, standard)
        db.commit()
        db.refresh(standard)
        return
    if not isinstance(standard, StandardV2Model):
        return
    for record in outcome.records:
        staging, _ = stage_record(
            db,
            source_name=record.source_name,
            source_url=record.source_url,
            raw_code=record.normalized_code,
            raw_name=record.name,
            raw_edition=record.edition,
            raw_status=record.status.value,
            raw_text="query-time verification",
            raw_publish_date=record.publish_date,
            raw_implement_date=record.implement_date,
            raw_abolish_date=record.abolish_date,
            raw_relation_text="; ".join(filter(None, [record.replaces, record.replaced_by])) or None,
        )
        staging.parse_status = "ok"
        exists = db.query(StandardV2SourceModel).filter_by(standard_id=standard.id, staging_id=staging.id).first()
        if exists is None:
            db.add(StandardV2SourceModel(
                standard_id=standard.id,
                staging_id=staging.id,
                source_name=record.source_name,
                source_url=record.source_url,
                observed_status=record.status.value,
                fetched_at=now,
            ))
    standard.status = outcome.status.value
    standard.verification_level = outcome.verification_level.value
    standard.source_conflict = outcome.source_conflict
    standard.last_verified_at = now
    standard.last_seen_at = now
    db.commit()
    db.refresh(standard)
