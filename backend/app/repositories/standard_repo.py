"""Database access for canonical standards and source records."""

from __future__ import annotations

from datetime import datetime
from difflib import SequenceMatcher
import re
from typing import Iterable

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.enums import StandardStatus, VerificationLevel, normalize_status
from app.models.models import StandardModel, StandardSourceModel
from app.services.standard_normalizer import normalize_standard_code, normalized_name, parse_edition


class StandardRepo:
    @staticmethod
    def get_by_id(db: Session, standard_id: int) -> StandardModel | None:
        return db.get(StandardModel, standard_id)

    @staticmethod
    def get_by_code(
        db: Session,
        code: str,
        *,
        edition: str | None = None,
    ) -> StandardModel | None:
        normalized = normalize_standard_code(code)
        query = db.query(StandardModel).filter(StandardModel.normalized_code == normalized)
        if edition is not None:
            query = query.filter(StandardModel.edition == edition)
        return query.order_by(StandardModel.last_verified_at.desc().nullslast(), StandardModel.id).first()

    @staticmethod
    def get_by_source_url(db: Session, source_url: str) -> StandardModel | None:
        if not source_url:
            return None
        return (
            db.query(StandardModel)
            .join(StandardSourceModel, StandardSourceModel.standard_id == StandardModel.id)
            .filter(StandardSourceModel.source_url == source_url)
            .first()
        )

    @staticmethod
    def get_by_identity(
        db: Session,
        normalized_code: str,
        edition: str | None,
        amendment: str | None,
    ) -> StandardModel | None:
        return (
            db.query(StandardModel)
            .filter(StandardModel.normalized_code == normalized_code)
            .filter(StandardModel.edition == edition)
            .filter(StandardModel.amendment == amendment)
            .first()
        )

    @staticmethod
    def search(db: Session, keyword: str, limit: int = 20) -> list[StandardModel]:
        """Search in PostgreSQL/SQLite only, ordered by explicit match priority."""

        normalized_code = normalize_standard_code(keyword)
        normalized_query_name = normalized_name(keyword)
        exact_code_query = (
            db.query(StandardModel)
            .filter(StandardModel.normalized_code == normalized_code)
        )
        edition_hint = parse_edition(keyword)
        if edition_hint.revision_year:
            edition_code = (
                exact_code_query.filter(
                    or_(
                        StandardModel.edition == edition_hint.edition,
                        StandardModel.revision_year == edition_hint.revision_year,
                    )
                )
                .order_by(StandardModel.last_verified_at.desc().nullslast(), StandardModel.id)
                .limit(limit)
                .all()
            )
            if edition_code:
                return edition_code
        exact_code = (
            exact_code_query
            .order_by(StandardModel.last_verified_at.desc().nullslast(), StandardModel.id)
            .limit(limit)
            .all()
        )
        if exact_code:
            return exact_code

        exact_name = (
            db.query(StandardModel)
            .filter(StandardModel.normalized_name == normalized_query_name)
            .order_by(StandardModel.last_verified_at.desc().nullslast(), StandardModel.id)
            .limit(limit)
            .all()
        )
        if exact_name:
            return exact_name

        year_match = re.search(r"(?<!\d)(20\d{2})(?!\d)", keyword)
        if year_match:
            requested_year = year_match.group(1)
            name_without_year = normalized_name(re.sub(r"(?<!\d)(20\d{2})(?!\d)", "", keyword))
            year_matches = (
                db.query(StandardModel)
                .filter(StandardModel.normalized_name == name_without_year)
                .filter(StandardModel.revision_year == requested_year)
                .order_by(StandardModel.last_verified_at.desc().nullslast(), StandardModel.id)
                .limit(limit)
                .all()
            )
            if year_matches:
                return year_matches

        # A database-side prefix/contains pass is bounded before calculating
        # similarity in Python.  Low similarity is deliberately not linked.
        candidates = (
            db.query(StandardModel)
            .filter(
                or_(
                    StandardModel.name.ilike(f"%{keyword.strip()}%"),
                    StandardModel.normalized_name.ilike(f"%{normalized_query_name}%"),
                )
            )
            .limit(max(limit * 5, 50))
            .all()
        )
        scored = [
            (SequenceMatcher(None, normalized_query_name, item.normalized_name).ratio(), item)
            for item in candidates
            if item.normalized_name
        ]
        scored = [item for item in scored if item[0] >= 0.86]
        scored.sort(key=lambda item: (-item[0], item[1].last_verified_at is None, item[1].id))
        return [item[1] for item in scored[:limit]]

    @staticmethod
    def upsert(
        db: Session,
        *,
        code: str,
        name: str = "",
        edition: str | None = None,
        revision_year: str | None = None,
        amendment: str | None = None,
        standard_type: str | None = None,
        status: StandardStatus | str = StandardStatus.UNKNOWN,
        publish_date: str | None = None,
        implement_date: str | None = None,
        abolish_date: str | None = None,
        replaces: str | None = None,
        replaced_by: str | None = None,
        article_status: str | None = None,
        mandatory_clause_status: str | None = None,
        issuing_authority: str | None = None,
        canonical_source: str | None = None,
        canonical_url: str | None = None,
        soujianzhu_url: str | None = None,
        verification_level: VerificationLevel | str = VerificationLevel.UNVERIFIED,
        source_updated_at: str | None = None,
        mark_verified: bool = False,
    ) -> tuple[StandardModel, bool]:
        canonical_code = normalize_standard_code(code)
        existing = StandardRepo.get_by_identity(db, canonical_code, edition, amendment)
        now = datetime.utcnow()
        normalized_status = normalize_status(status)
        if existing is None:
            existing = StandardModel(
                code=canonical_code or code.strip(),
                normalized_code=canonical_code or code.strip().upper(),
                name=name or "",
                normalized_name=normalized_name(name),
                edition=edition,
                revision_year=revision_year,
                amendment=amendment,
                standard_type=standard_type,
                status=normalized_status.value,
                publish_date=publish_date,
                implement_date=implement_date,
                abolish_date=abolish_date,
                replaces=replaces,
                replaced_by=replaced_by,
                article_status=article_status,
                mandatory_clause_status=mandatory_clause_status,
                issuing_authority=issuing_authority,
                canonical_source=canonical_source,
                canonical_url=canonical_url,
                soujianzhu_url=soujianzhu_url,
                verification_level=VerificationLevel(verification_level).value,
                first_seen_at=now,
                last_seen_at=now,
                source_updated_at=source_updated_at,
                record_updated_at=now,
                updated_at=now,
                year=revision_year,
                publishing_department=issuing_authority,
                implementation_date=implement_date,
                url=canonical_url,
                last_updated=now,
            )
            if mark_verified:
                existing.last_verified_at = now
            db.add(existing)
            db.flush()
            return existing, True

        existing.code = canonical_code or existing.code
        existing.normalized_code = canonical_code or existing.normalized_code
        if name:
            existing.name = name
            existing.normalized_name = normalized_name(name)
        for field, value in (
            ("edition", edition),
            ("revision_year", revision_year),
            ("amendment", amendment),
            ("standard_type", standard_type),
            ("publish_date", publish_date),
            ("implement_date", implement_date),
            ("abolish_date", abolish_date),
            ("replaces", replaces),
            ("replaced_by", replaced_by),
            ("article_status", article_status),
            ("mandatory_clause_status", mandatory_clause_status),
            ("issuing_authority", issuing_authority),
            ("canonical_source", canonical_source),
            ("canonical_url", canonical_url),
            ("soujianzhu_url", soujianzhu_url),
            ("source_updated_at", source_updated_at),
        ):
            if value is not None:
                setattr(existing, field, value)
        if normalized_status != StandardStatus.UNKNOWN or existing.status == StandardStatus.UNKNOWN.value:
            existing.status = normalized_status.value
        if verification_level:
            existing.verification_level = VerificationLevel(verification_level).value
        existing.last_seen_at = now
        existing.record_updated_at = now
        existing.updated_at = now
        existing.year = existing.revision_year
        existing.publishing_department = existing.issuing_authority
        existing.implementation_date = existing.implement_date
        existing.url = existing.canonical_url
        existing.last_updated = now
        if mark_verified:
            existing.last_verified_at = now
        db.flush()
        return existing, False

    @staticmethod
    def count_by_status(db: Session) -> dict[str, int]:
        counts = {status.value: 0 for status in StandardStatus}
        rows = db.query(StandardModel.status, func.count(StandardModel.id)).group_by(StandardModel.status).all()
        for status, count in rows:
            counts[normalize_status(status).value] += int(count)
        return counts

    @staticmethod
    def sources_for(db: Session, standard_id: int) -> list[StandardSourceModel]:
        return (
            db.query(StandardSourceModel)
            .filter(StandardSourceModel.standard_id == standard_id)
            .order_by(StandardSourceModel.source_name)
            .all()
        )

    @staticmethod
    def create_or_update(db: Session, data, year: str | None = None):
        """Compatibility shim for old one-off scripts; unknown stays unknown."""

        standard, _ = StandardRepo.upsert(
            db,
            code=data.code,
            name=data.name or "",
            revision_year=year,
            status=getattr(data, "status", StandardStatus.UNKNOWN),
            canonical_url=getattr(data, "url", None),
            verification_level=VerificationLevel.UNVERIFIED,
        )
        db.commit()
        db.refresh(standard)
        return standard
