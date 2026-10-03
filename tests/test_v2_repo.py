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


def test_v2_code_lookup_follows_gb_to_gbt_type_change():
    db = _db()
    standard = StandardV2Model(
        code="GB/T 50010-2010", normalized_code="GB/T 50010-2010", base_code="GB/T 50010-2010",
        standard_prefix="GB/T", standard_number="50010", standard_year="2010", name="混凝土结构设计标准",
        normalized_name="混凝土结构设计标准", edition="2024年版", revision_year="2024",
        status="current", verification_level="single_source", revision_status="amended",
        mandatory_clause_status="unknown", data_quality_status="publishable",
    )
    db.add(standard)
    db.commit()

    assert StandardV2Repo.get_by_code(db, "GB 50010-2010") == standard


def test_v2_lookup_ignores_an_impossible_pre_code_edition():
    db = _db()
    original = StandardV2Model(
        code="GB 50009-2012", normalized_code="GB 50009-2012", base_code="GB 50009-2012",
        standard_prefix="GB", standard_number="50009", standard_year="2012", name="建筑结构荷载规范",
        normalized_name="建筑结构荷载规范", status="current", verification_level="single_source",
        revision_status="original", mandatory_clause_status="unknown", data_quality_status="publishable",
    )
    impossible = StandardV2Model(
        code="GB 50009-2012", normalized_code="GB 50009-2012", base_code="GB 50009-2012",
        standard_prefix="GB", standard_number="50009", standard_year="2012", name="建筑结构荷载规范",
        normalized_name="建筑结构荷载规范", edition="2006年版", revision_year="2006",
        status="current", verification_level="single_source", revision_status="amended",
        mandatory_clause_status="unknown", data_quality_status="publishable",
    )
    db.add_all([original, impossible])
    db.commit()

    assert StandardV2Repo.get_by_code(db, "GB 50009-2012") == original
    assert StandardV2Repo.count_by_status(db)["current"] == 1


def _alias_standard(prefix='GB/T', edition='2024年版', year='2010', quality='publishable'):
    code = f'{prefix} 50010-{year}'
    return StandardV2Model(
        code=code, normalized_code=code, base_code=code, standard_prefix=prefix,
        standard_number='50010', standard_year=year, name='混凝土结构设计标准',
        normalized_name='混凝土结构设计标准', edition=edition,
        revision_year=edition[:4] if edition else None, status='current',
        verification_level='single_source', revision_status='amended',
        mandatory_clause_status='unknown', data_quality_status=quality,
    )


def test_v2_search_and_lookup_share_bidirectional_gb_alias_and_edition_preference():
    for prefix, requested in [('GB/T','GB'), ('GB','GB/T')]:
        db = _db()
        latest = _alias_standard(prefix)
        older = _alias_standard(prefix, '2015年版')
        db.add_all([latest,older,_alias_standard(prefix,year='2011'),
                    _alias_standard(prefix,'2025年版',quality='quarantined')]); db.commit()
        assert StandardV2Repo.search(db,f'{requested} 50010-2010') == [latest,older]
        assert StandardV2Repo.search(db,f'{requested} 50010-2010（2015年版）') == [older]
        assert StandardV2Repo.get_by_code(db,f'{requested} 50010-2010（2015年版）') == older


def test_v2_alias_keeps_exact_identity_first_and_does_not_guess_other_prefixes():
    db=_db(); exact=_alias_standard('GB'); alias=_alias_standard()
    db.add_all([exact,alias,_alias_standard('JGJ/T')]); db.commit()
    assert StandardV2Repo.search(db,'GB 50010-2010') == [exact]
    assert StandardV2Repo.search(db,'JGJ 50010-2010') == []
    assert StandardV2Repo.get_by_code(db,'JGJ 50010-2010') is None


def test_v2_requested_alias_edition_precedes_exact_identity_without_that_edition():
    db = _db()
    exact = _alias_standard('GB', edition=None)
    alias = _alias_standard('GB/T', edition='2015年版')
    db.add_all([exact, alias])
    db.commit()
    assert StandardV2Repo.search(db, 'GB 50010-2010（2015年版）') == [alias]
    assert StandardV2Repo.get_by_code(db, 'GB 50010-2010（2015年版）') == alias
