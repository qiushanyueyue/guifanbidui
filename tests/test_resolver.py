from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.models import StandardModel, StandardSourceModel
from app.sync.resolver import resolve_canonical_standard, resolve_status


def test_official_status_wins_but_conflict_is_preserved():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    standard = StandardModel(code="GB 55001-2021", normalized_code="GB 55001-2021", name="工程结构通用规范", normalized_name="工程结构通用规范", status="unknown", verification_level="unverified")
    db.add(standard)
    db.flush()
    db.add_all([
        StandardSourceModel(standard_id=standard.id, source_name="samr", source_code=standard.code, source_status="废止", parse_status="ok"),
        StandardSourceModel(standard_id=standard.id, source_name="csres", source_code=standard.code, source_status="现行", parse_status="ok"),
    ])
    db.flush()
    decision = resolve_status(standard and db.query(StandardSourceModel).all())
    assert decision["status"].value == "abolished"
    assert decision["source_conflict"] is True
    resolve_canonical_standard(db, standard)
    assert standard.status == "abolished"
    assert standard.source_conflict is True


def test_same_priority_official_conflict_uses_conflict_status():
    decision = resolve_status([
        StandardSourceModel(source_name="samr", source_status="现行", parse_status="ok"),
        StandardSourceModel(source_name="mohurd", source_status="废止", parse_status="ok"),
    ])
    assert decision["status"].value == "conflict"
    assert decision["verification_level"].value == "conflict"


def test_third_party_status_conflict_is_not_silently_prioritized():
    decision = resolve_status([
        StandardSourceModel(source_name="soujianzhu", source_status="现行", parse_status="ok"),
        StandardSourceModel(source_name="csres", source_status="废止", parse_status="ok"),
    ])
    assert decision["status"].value == "conflict"
    assert decision["verification_level"].value == "conflict"
