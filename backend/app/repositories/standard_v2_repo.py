"""Read-only repository for the published V2 standards dataset."""

from __future__ import annotations

from difflib import SequenceMatcher

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.enums import StandardStatus, normalize_status
from app.models.models import StandardV2Model, StandardV2SourceModel
from app.services.standard_normalizer import normalize_standard_code, normalized_name, parse_edition


class StandardV2Repo:
    @staticmethod
    def _published(db: Session):
        return db.query(StandardV2Model).filter(
            StandardV2Model.data_quality_status != "quarantined"
        )

    @classmethod
    def get_by_id(cls, db: Session, standard_id: int) -> StandardV2Model | None:
        return cls._published(db).filter(StandardV2Model.id == standard_id).first()

    @classmethod
    def get_by_code(cls, db: Session, code: str) -> StandardV2Model | None:
        normalized = normalize_standard_code(code)
        query = cls._published(db).filter(StandardV2Model.normalized_code == normalized)
        edition = parse_edition(code)
        if edition.revision_year:
            requested = query.filter(
                or_(
                    StandardV2Model.edition == edition.edition,
                    StandardV2Model.revision_year == edition.revision_year,
                )
            ).first()
            if requested is not None:
                return requested
        return (
            query
            .order_by(
                StandardV2Model.last_verified_at.desc().nullslast(),
                StandardV2Model.edition.desc().nullslast(),
                StandardV2Model.id,
            )
            .first()
        )

    @classmethod
    def get_by_source_url(cls, db: Session, source_url: str) -> StandardV2Model | None:
        return (
            cls._published(db)
            .join(StandardV2SourceModel, StandardV2SourceModel.standard_id == StandardV2Model.id)
            .filter(StandardV2SourceModel.source_url == source_url)
            .first()
        )

    @classmethod
    def search(cls, db: Session, keyword: str, limit: int = 20) -> list[StandardV2Model]:
        code = normalize_standard_code(keyword)
        exact_query = cls._published(db).filter(StandardV2Model.normalized_code == code)
        edition = parse_edition(keyword)
        if edition.revision_year:
            edition_matches = exact_query.filter(
                or_(
                    StandardV2Model.edition == edition.edition,
                    StandardV2Model.revision_year == edition.revision_year,
                )
            ).limit(limit).all()
            if edition_matches:
                return edition_matches
        exact = (
            exact_query
            .order_by(StandardV2Model.last_verified_at.desc().nullslast(), StandardV2Model.id)
            .limit(limit)
            .all()
        )
        if exact:
            return exact
        wanted_name = normalized_name(keyword)
        exact_name = (
            cls._published(db)
            .filter(StandardV2Model.normalized_name == wanted_name)
            .order_by(StandardV2Model.last_verified_at.desc().nullslast(), StandardV2Model.id)
            .limit(limit)
            .all()
        )
        if exact_name:
            return exact_name
        candidates = (
            cls._published(db)
            .filter(
                or_(
                    StandardV2Model.name.ilike(f"%{keyword.strip()}%"),
                    StandardV2Model.normalized_name.ilike(f"%{wanted_name}%"),
                )
            )
            .limit(max(limit * 5, 50))
            .all()
        )
        scored = [
            (SequenceMatcher(None, wanted_name, item.normalized_name).ratio(), item)
            for item in candidates
            if item.normalized_name
        ]
        return [item for score, item in sorted(scored, key=lambda row: (-row[0], row[1].id)) if score >= 0.86][:limit]

    @staticmethod
    def sources_for(db: Session, standard_id: int) -> list[StandardV2SourceModel]:
        return (
            db.query(StandardV2SourceModel)
            .filter(StandardV2SourceModel.standard_id == standard_id)
            .order_by(StandardV2SourceModel.source_name)
            .all()
        )

    @classmethod
    def count_by_status(cls, db: Session) -> dict[str, int]:
        counts = {status.value: 0 for status in StandardStatus}
        rows = cls._published(db).with_entities(
            StandardV2Model.status, func.count(StandardV2Model.id)
        ).group_by(StandardV2Model.status).all()
        for status, count in rows:
            counts[normalize_status(status).value] += int(count)
        return counts

    @staticmethod
    def has_data(db: Session) -> bool:
        return db.query(StandardV2Model.id).limit(1).first() is not None
