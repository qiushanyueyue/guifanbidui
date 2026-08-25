from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.endpoints import _result_v2
from app.models.base import Base
from app.models.models import StandardV2Model, StandardV2SourceModel


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _standard() -> StandardV2Model:
    return StandardV2Model(
        code="GB 50013-2018",
        normalized_code="GB 50013-2018",
        base_code="GB 50013-2018",
        standard_prefix="GB",
        standard_number="50013",
        standard_year="2018",
        name="室外给水设计标准",
        normalized_name="室外给水设计标准",
        status="current",
        verification_level="single_source",
        revision_status="original",
        mandatory_clause_status="unknown",
        data_quality_status="publishable",
    )


def test_v2_result_reports_only_the_actual_single_source():
    db = _db()
    standard = _standard()
    db.add(standard)
    db.flush()
    db.add(
        StandardV2SourceModel(
            standard_id=standard.id,
            staging_id=1,
            source_name="csres",
            source_url="http://www.csres.com/detail/1",
        )
    )
    db.commit()

    result = _result_v2(db, standard)

    assert result.canonical_source == "csres"


def test_v2_result_preserves_excel_catalog_source_name():
    db = _db()
    standard = _standard()
    db.add(standard)
    db.flush()
    db.add(
        StandardV2SourceModel(
            standard_id=standard.id,
            staging_id=1,
            source_name="excel_catalog_20251011",
            source_url=None,
        )
    )
    db.commit()

    result = _result_v2(db, standard)

    assert result.canonical_source == "excel_catalog_20251011"


def test_v2_result_combines_actual_sources_in_stable_order():
    db = _db()
    standard = _standard()
    db.add(standard)
    db.flush()
    db.add_all(
        [
            StandardV2SourceModel(
                standard_id=standard.id,
                staging_id=1,
                source_name="soujianzhu",
                source_url="https://www.soujianzhu.cn/detail/1",
            ),
            StandardV2SourceModel(
                standard_id=standard.id,
                staging_id=2,
                source_name="csres",
                source_url="http://www.csres.com/detail/2",
            ),
        ]
    )
    db.commit()

    result = _result_v2(db, standard)

    assert result.canonical_source == "csres+soujianzhu"
