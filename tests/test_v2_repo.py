from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.models import StandardV2Model, StandardV2SourceModel, StagingStandardModel
from app.repositories.standard_v2_repo import StandardV2Repo
from app.sync.v2_pipeline import stage_record


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_v2_search_is_database_only_and_exposes_exact_soujianzhu_evidence():
    db = _db()
    staging, _ = stage_record(
        db,
        source_name="soujianzhu",
        source_url="https://www.soujianzhu.cn/NormAndRules/gfnr.aspx?id=323",
        raw_code="GB50016-2014",
        raw_name="建筑设计防火规范",
    )
    standard = StandardV2Model(
        code="GB 50016-2014",
        normalized_code="GB 50016-2014",
        base_code="GB 50016-2014",
        standard_prefix="GB",
        standard_number="50016",
        standard_year="2014",
        name="建筑设计防火规范",
        normalized_name="建筑设计防火规范",
        status="unknown",
        verification_level="unverified",
        revision_status="original",
        mandatory_clause_status="unknown",
        data_quality_status="publishable",
    )
    db.add(standard)
    db.flush()
    db.add(
        StandardV2SourceModel(
            standard_id=standard.id,
            staging_id=staging.id,
            source_name="soujianzhu",
            source_url=staging.source_url,
        )
    )
    db.commit()

    found = StandardV2Repo.search(db, "GB50016-2014")
    sources = StandardV2Repo.sources_for(db, found[0].id)
    assert found == [standard]
    assert sources[0].source_url.endswith("gfnr.aspx?id=323")


def test_v2_search_excludes_quarantined_quality_rows():
    db = _db()
    db.add(
        StandardV2Model(
            code="GB 1-2020",
            normalized_code="GB 1-2020",
            base_code="GB 1-2020",
            standard_prefix="GB",
            standard_number="1",
            standard_year="2020",
            name="测试标准",
            normalized_name="测试标准",
            status="unknown",
            verification_level="unverified",
            revision_status="original",
            mandatory_clause_status="unknown",
            data_quality_status="quarantined",
        )
    )
    db.commit()
    assert StandardV2Repo.search(db, "GB 1-2020") == []


def test_v2_code_search_prefers_requested_edition():
    db = _db()
    for edition in (None, "2018年版"):
        db.add(
            StandardV2Model(
                code="GB 50016-2014", normalized_code="GB 50016-2014", base_code="GB 50016-2014",
                standard_prefix="GB", standard_number="50016", standard_year="2014", name="建筑设计防火规范",
                normalized_name="建筑设计防火规范", edition=edition, revision_year="2018" if edition else None,
                status="current", verification_level="single_source", revision_status="amended" if edition else "original",
                mandatory_clause_status="unknown", data_quality_status="publishable",
            )
        )
    db.commit()
    assert StandardV2Repo.get_by_code(db, "GB 50016-2014（2018年版）").edition == "2018年版"
