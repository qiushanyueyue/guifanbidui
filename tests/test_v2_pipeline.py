from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.models import (
    NormativeDocumentModel,
    QuarantinedStandardModel,
    StagingStandardModel,
    StandardV2Model,
)
from app.sync.v2_pipeline import publish_staging, stage_record


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _record(**overrides):
    record = {
        "source_name": "soujianzhu",
        "source_url": "https://example.test/id=323",
        "raw_code": "GB50016-2014",
        "raw_name": "《建筑设计防火规范》",
        "raw_edition": "2018年版",
        "raw_status": None,
        "raw_text": "公开目录元数据",
    }
    record.update(overrides)
    return record


def test_staging_is_idempotent_by_source_content_hash():
    db = _db()
    first, inserted_first = stage_record(db, **_record())
    second, inserted_second = stage_record(db, **_record())
    assert first.id == second.id
    assert inserted_first is True
    assert inserted_second is False
    assert db.query(StagingStandardModel).count() == 1


def test_publish_normalizes_code_and_revision_without_claiming_current():
    db = _db()
    stage_record(db, **_record())
    report = publish_staging(db)
    row = db.query(StandardV2Model).one()
    assert row.normalized_code == "GB 50016-2014"
    assert row.edition == "2018年版"
    assert row.revision_status == "amended"
    assert row.status == "unknown"
    assert report.published == 1


def test_invalid_code_is_quarantined_not_published():
    db = _db()
    stage_record(db, **_record(raw_code="这不是规范号"))
    report = publish_staging(db)
    assert report.quarantined == 1
    assert db.query(StandardV2Model).count() == 0
    assert db.query(QuarantinedStandardModel).one().reason_code == "invalid_code"


def test_two_agreeing_sources_are_cross_verified():
    db = _db()
    stage_record(db, **_record(raw_status="现行"))
    stage_record(db, **_record(source_name="csres", source_url="https://example.test/csres/1", raw_status="现行"))
    publish_staging(db)
    row = db.query(StandardV2Model).one()
    assert row.status == "current"
    assert row.verification_level == "cross_verified"


def test_identity_agreement_plus_one_usable_status_is_cross_verified():
    db = _db()
    stage_record(db, **_record(raw_status=None))
    stage_record(
        db,
        **_record(
            source_name="csres",
            source_url="https://example.test/csres/1",
            raw_status="现行",
        ),
    )
    publish_staging(db)
    row = db.query(StandardV2Model).one()
    assert row.status == "current"
    assert row.verification_level == "cross_verified"


def test_conflicting_third_party_statuses_are_visible():
    db = _db()
    stage_record(db, **_record(raw_status="现行"))
    stage_record(db, **_record(source_name="csres", source_url="https://example.test/csres/1", raw_status="废止"))
    publish_staging(db)
    row = db.query(StandardV2Model).one()
    assert row.status == "conflict"
    assert row.source_conflict is True
    assert row.data_quality_status == "needs_review"


def test_same_code_different_editions_remain_separate():
    db = _db()
    stage_record(db, **_record())
    stage_record(db, **_record(source_url="https://example.test/id=older", raw_edition=None))
    publish_staging(db)
    assert db.query(StandardV2Model).count() == 2


def test_numberless_method_is_published_as_normative_document():
    db = _db()
    stage_record(
        db,
        **_record(
            raw_code=None,
            raw_name="公路工程基本建设项目设计文件编制办法",
            source_url="https://example.test/method/1",
        ),
    )
    report = publish_staging(db)
    row = db.query(NormativeDocumentModel).one()
    assert row.title.endswith("编制办法")
    assert row.status == "unknown"
    assert report.normative_documents == 1


def test_recovered_code_removes_stale_derived_normative_document():
    db = _db()
    staged, _ = stage_record(
        db,
        **_record(
            raw_code=None,
            raw_name="住宅项目规范",
            raw_text='{"title": "住宅项目规范"}',
        ),
    )
    publish_staging(db)
    assert db.query(NormativeDocumentModel).count() == 1

    staged.raw_text = '{"title": "《住宅项目规范》GB 55038-2025"}'
    staged.parse_status = "pending"
    publish_staging(db)

    assert db.query(StandardV2Model).one().base_code == "GB 55038-2025"
    assert db.query(NormativeDocumentModel).count() == 0


def test_replacement_prose_builds_two_directional_edges_without_cross_record_text():
    from app.models.models import StandardV2RelationModel

    db = _db()
    for code, name in [
        ("GB 50157-1992", "地下铁道设计规范"),
        ("GB 50157-2003", "地铁设计规范"),
        ("GB 50157-2013", "地铁设计规范"),
    ]:
        stage_record(db, **_record(raw_code=code, raw_name=name, source_url=f"https://example.test/{code}"))
    stage_record(
        db,
        **_record(
            source_name="csres",
            raw_code="GB 50157-2003",
            raw_name="地铁设计规范",
            source_url="https://example.test/csres/62113",
            raw_relation_text="GB 50157-1992 ;被 GB 50157-2013 代替并废止",
        ),
    )
    publish_staging(db)
    rows = db.query(StandardV2RelationModel).all()
    assert {(row.relation_type, row.source_standard_id, row.target_standard_id) for row in rows}
    assert {row.relation_type for row in rows} == {"replaces", "replaced_by"}


def test_replacement_relation_resolves_two_digit_year_alias():
    from app.models.models import StandardV2RelationModel

    db = _db()
    stage_record(db, **_record(raw_code="GB 50157-92", raw_name="地下铁道设计规范"))
    stage_record(db, **_record(raw_code="GB 50157-2003", raw_name="地铁设计规范"))
    stage_record(
        db,
        **_record(
            source_name="csres",
            raw_code="GB 50157-2003",
            raw_name="地铁设计规范",
            raw_status="作废",
            raw_relation_text="GB 50157-1992",
        ),
    )
    publish_staging(db)
    relation = db.query(StandardV2RelationModel).one()
    assert relation.relation_type == "replaces"
