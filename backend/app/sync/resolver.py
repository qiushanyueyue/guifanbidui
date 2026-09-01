"""Centralized source-priority and conflict resolution."""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.enums import StandardStatus, VerificationLevel, normalize_status
from app.models.models import StandardHistoryModel, StandardModel, StandardSourceModel
from app.repositories.standard_repo import StandardRepo

OFFICIAL_SOURCES = {"samr", "mohurd", "openstd"}
SOURCE_PRIORITY = {"mohurd": 0, "samr": 0, "openstd": 1, "soujianzhu": 2, "csres": 3}


def _usable_sources(sources: list[StandardSourceModel]) -> list[StandardSourceModel]:
    return [
        source
        for source in sources
        if source.parse_status == "ok" and normalize_status(source.source_status) != StandardStatus.UNKNOWN
    ]


def _source_sort_key(source: StandardSourceModel) -> tuple[int, str, int]:
    return SOURCE_PRIORITY.get(source.source_name, 99), source.source_name, source.id


def resolve_status(sources: list[StandardSourceModel], existing_status: str | None = None) -> dict[str, object]:
    """Resolve one canonical status without treating a failed source as current."""

    usable = _usable_sources(sources)
    if not usable:
        existing = normalize_status(existing_status)
        return {
            "status": existing if existing != StandardStatus.UNKNOWN else StandardStatus.UNKNOWN,
            "verification_level": VerificationLevel.UNVERIFIED,
            "source_conflict": False,
            "conflict_details": None,
            "canonical_source": None,
            "canonical_url": None,
        }

    official = [source for source in usable if source.source_name in OFFICIAL_SOURCES]
    selected_pool = official or usable
    selected_pool.sort(key=_source_sort_key)
    status_values = {normalize_status(source.source_status) for source in selected_pool}
    all_status_values = {normalize_status(source.source_status) for source in usable}
    selected = selected_pool[0]
    # A clear official conclusion is final. Third-party disagreement is kept
    # in source evidence but does not downgrade the public business status.
    conflict = len(status_values) > 1
    third_party_only = not official
    same_level_conflict = len(status_values) > 1 and (
        third_party_only
        or len({SOURCE_PRIORITY.get(item.source_name, 99) for item in selected_pool}) == 1
    )
    if conflict:
        verification = VerificationLevel.CONFLICT
    elif official:
        verification = VerificationLevel.OFFICIAL if len(official) == 1 else VerificationLevel.CROSS_VERIFIED
    elif len(selected_pool) > 1:
        verification = VerificationLevel.CROSS_VERIFIED
    else:
        verification = VerificationLevel.SINGLE_SOURCE
    details = None
    if len(all_status_values) > 1:
        details = json.dumps(
            {
                source.source_name: normalize_status(source.source_status).value
                for source in sorted(usable, key=_source_sort_key)
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    return {
        "status": StandardStatus.CONFLICT if same_level_conflict else normalize_status(selected.source_status),
        "verification_level": verification,
        "source_conflict": bool(conflict),
        "conflict_details": details,
        "canonical_source": selected.source_name,
        "canonical_url": selected.source_url,
        "selected_source": selected,
    }


def _record_change(db: Session, standard: StandardModel, field: str, before: object, after: object, source: str | None) -> None:
    if before == after:
        return
    db.add(
        StandardHistoryModel(
            standard_id=standard.id,
            changed_at=datetime.utcnow(),
            field_name=field,
            old_value=None if before is None else str(before),
            new_value=None if after is None else str(after),
            source=source,
        )
    )


def resolve_canonical_standard(db: Session, standard: StandardModel | int) -> StandardModel:
    """Apply source precedence to a standard and append field-level history."""

    if isinstance(standard, int):
        resolved = StandardRepo.get_by_id(db, standard)
        if resolved is None:
            raise ValueError(f"standard id {standard} does not exist")
        standard = resolved
    sources = StandardRepo.sources_for(db, standard.id)
    decision = resolve_status(sources, standard.status)
    selected = decision.get("selected_source")
    selected_source_name = selected.source_name if selected is not None else None
    updates = {
        "status": decision["status"].value,
        "verification_level": decision["verification_level"].value,
        "source_conflict": decision["source_conflict"],
        "conflict_details": decision["conflict_details"],
        "canonical_source": decision["canonical_source"],
        "canonical_url": decision["canonical_url"],
    }
    if selected is not None:
        updates.update(
            {
                "publish_date": selected.publish_date,
                "implement_date": selected.implement_date,
                "abolish_date": selected.abolish_date,
                "replaces": selected.replaces,
                "replaced_by": selected.replaced_by,
                "issuing_authority": standard.issuing_authority or None,
                "source_updated_at": selected.source_updated_at,
            }
        )
    now = datetime.utcnow()
    for field, value in updates.items():
        before = getattr(standard, field)
        if value is not None or field in {"status", "verification_level", "source_conflict", "conflict_details", "canonical_source", "canonical_url"}:
            _record_change(db, standard, field, before, value, selected_source_name)
            setattr(standard, field, value)
    standard.last_verified_at = now
    standard.record_updated_at = now
    standard.updated_at = now
    standard.last_updated = now
    db.flush()
    return standard
