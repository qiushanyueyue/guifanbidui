from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.endpoints import get_stats
from app.models.base import Base
from app.models.models import StandardV2Model


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _standard(*, code: str, verified_at: datetime | None, published_at: datetime) -> StandardV2Model:
    number, year = code.removeprefix("GB ").split("-")
    return StandardV2Model(
        code=code,
        normalized_code=code,
        base_code=code,
        standard_prefix="GB",
        standard_number=number,
        standard_year=year,
        name=f"测试规范 {number}",
        normalized_name=f"测试规范{number}",
        status="unknown",
        verification_level="unverified",
        revision_status="original",
        mandatory_clause_status="unknown",
        data_quality_status="publishable",
        last_verified_at=verified_at,
        published_at=published_at,
    )


def test_v2_stats_reports_dataset_publication_time_not_stale_verification(monkeypatch):
    monkeypatch.setenv("STANDARDS_DATASET", "v2")
    db = _db()
    db.add_all(
        [
            _standard(
                code="GB 1-2020",
                verified_at=datetime(2026, 1, 30, 8, 0),
                published_at=datetime(2026, 8, 24, 9, 0),
            ),
            _standard(
                code="GB 2-2021",
                verified_at=None,
                published_at=datetime(2026, 8, 25, 12, 30),
            ),
        ]
    )
    db.commit()

    stats = get_stats(db)

    assert stats.last_updated == datetime(2026, 8, 25, 12, 30, tzinfo=timezone.utc)
