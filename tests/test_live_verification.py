from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.enums import StandardStatus, VerificationLevel
from app.models.models import StandardModel, StandardV2Model
from app.services.live_verification import (
    cache_is_fresh,
    discover_live,
    persist_discovered_standard,
    verify_live,
)
from app.sources.base import SourceRecord, SourceUnavailable


def _standard(**overrides):
    values = dict(
        code="GB 50016-2014",
        normalized_code="GB 50016-2014",
        name="建筑设计防火规范",
        normalized_name="建筑设计防火规范",
        status="unknown",
        verification_level="unverified",
    )
    values.update(overrides)
    return StandardModel(**values)


class FakeSource:
    def __init__(self, record=None):
        self.record = record

    def search(self, _query):
        if self.record is None:
            raise SourceUnavailable("unavailable", source="test")
        return [self.record]

    def fetch_detail(self, _url):
        return self.search("")[0]

    def normalize(self, record):
        return record


def _factory(records):
    return lambda name: FakeSource(records.get(name))


def _record(source_name, status="现行", **overrides):
    values = dict(source_name=source_name, code="GB 50016-2014", name="建筑设计防火规范", source_status=status)
    values.update(overrides)
    return SourceRecord(**values)


def test_fresh_definitive_cache_skips_refresh_window(monkeypatch):
    monkeypatch.setenv("STANDARD_CACHE_FRESH_DAYS", "30")
    now = datetime.now(UTC).replace(tzinfo=None)
    assert cache_is_fresh(_standard(status="current", last_verified_at=now - timedelta(days=2)), now=now) is True
    assert cache_is_fresh(_standard(status="current", last_verified_at=now - timedelta(days=31)), now=now) is False
    assert cache_is_fresh(_standard(status="unknown", last_verified_at=now), now=now) is False


def test_official_status_is_immediately_final():
    outcome = verify_live(
        _standard(),
        factory=_factory({"mohurd": _record("mohurd", "废止"), "csres": _record("csres", "现行")}),
    )
    assert outcome.status == StandardStatus.ABOLISHED
    assert outcome.verification_level == VerificationLevel.OFFICIAL


def test_two_matching_third_party_sources_are_cross_verified():
    outcome = verify_live(
        _standard(),
        factory=_factory({"csres": _record("csres"), "soujianzhu": _record("soujianzhu")}),
    )
    assert outcome.status == StandardStatus.CURRENT
    assert outcome.verification_level == VerificationLevel.CROSS_VERIFIED


def test_one_matching_third_party_source_is_a_definitive_single_source_result():
    outcome = verify_live(
        _standard(),
        factory=_factory({"csres": _record("csres", "现行")}),
    )
    assert outcome.status == StandardStatus.CURRENT
    assert outcome.verification_level == VerificationLevel.SINGLE_SOURCE


def test_missing_code_can_be_discovered_with_gb_t_correction():
    outcome = discover_live(
        code="GB 50308-2017",
        name="城市轨道交通工程测量规范",
        factory=_factory({
            "csres": _record(
                "csres",
                code="GB/T 50308-2017",
                name="城市轨道交通工程测量规范",
                source_url="http://www.csres.com/detail/300264.html",
            )
        }),
    )
    assert outcome is not None
    assert outcome.status == StandardStatus.CURRENT
    assert outcome.verification_level == VerificationLevel.SINGLE_SOURCE
    assert outcome.records[0].normalized_code == "GB/T 50308-2017"


def test_missing_code_discovery_rejects_a_name_mismatch():
    outcome = discover_live(
        code="GB 50308-2017",
        name="另一规范",
        factory=_factory({
            "csres": _record(
                "csres",
                code="GB/T 50308-2017",
                name="城市轨道交通工程测量规范",
            )
        }),
    )
    assert outcome is None


def test_discovered_record_is_published_into_v2_dataset():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    outcome = discover_live(
        code="GB/T 50308-2017",
        name="城市轨道交通工程测量规范",
        factory=_factory({
            "csres": _record(
                "csres",
                code="GB/T 50308-2017",
                name="城市轨道交通工程测量规范",
                source_url="http://www.csres.com/detail/300264.html",
            )
        }),
    )
    standard = persist_discovered_standard(db, outcome, use_v2=True)
    assert isinstance(standard, StandardV2Model)
    assert standard.normalized_code == "GB/T 50308-2017"
    assert standard.status == "current"
    assert standard.verification_level == "single_source"
    assert standard.data_quality_status == "publishable"


def test_repeated_discovery_reuses_existing_v2_record():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    outcome = discover_live(
        code="GB 50308-2017",
        name=None,
        factory=_factory({
            "csres": _record(
                "csres",
                code="GB/T 50308-2017",
                name="城市轨道交通工程测量规范",
                source_url="http://www.csres.com/detail/300264.html",
            )
        }),
    )
    first = persist_discovered_standard(db, outcome, use_v2=True)
    second = persist_discovered_standard(db, outcome, use_v2=True)
    assert second.id == first.id
    assert db.query(StandardV2Model).count() == 1


def test_status_or_replacement_disagreement_is_temporarily_unconfirmed():
    status_conflict = verify_live(
        _standard(),
        factory=_factory({"csres": _record("csres", "现行"), "soujianzhu": _record("soujianzhu", "废止")}),
    )
    relation_conflict = verify_live(
        _standard(),
        factory=_factory({
            "csres": _record("csres", replaced_by="GB 55037-2022"),
            "soujianzhu": _record("soujianzhu", replaced_by="GB 55036-2022"),
        }),
    )
    assert status_conflict.status == StandardStatus.CONFLICT
    assert relation_conflict.status == StandardStatus.CONFLICT


def test_two_third_party_sources_must_also_agree_on_name():
    outcome = verify_live(
        _standard(name="", normalized_name=""),
        factory=_factory({
            "csres": _record("csres", name="建筑设计防火规范"),
            "soujianzhu": _record("soujianzhu", name="建筑防火设计规范"),
        }),
    )
    assert outcome.status == StandardStatus.CONFLICT
