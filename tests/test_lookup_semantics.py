"""Regression tests for the 2026-11-10 lookup issue list: source failure vs miss,
year-less codes, name-only version claims and ambiguous candidates."""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import endpoints
from app.models.base import Base
from app.models.enums import StandardStatus
from app.models.models import LiveLookupAttemptModel, StandardV2Model, StandardV2RelationModel
from app.models.schemas import VerifyRequest
from app.repositories.standard_v2_repo import StandardV2Repo
from app.services.live_verification import (
    LookupTrace,
    attempt_outcome,
    discover_live,
    record_attempt,
    recent_attempt,
    verify_live,
)
from app.sources.base import NotFound, RateLimited, SourceNotConfigured, SourceRecord, SourceUnavailable
from app.timeutil import utc_now


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _v2(code: str, name: str, **overrides) -> StandardV2Model:
    prefix, _, rest = code.partition(" ")
    number, _, year = rest.partition("-")
    values = dict(
        code=code, normalized_code=code, base_code=code, standard_prefix=prefix,
        standard_number=number, standard_year=year or None, name=name, normalized_name=name,
        status="current", verification_level="single_source", revision_status="original",
        mandatory_clause_status="unknown", data_quality_status="publishable",
        last_verified_at=utc_now(),
    )
    values.update(overrides)
    return StandardV2Model(**values)


class Source:
    def __init__(self, records=None, error=None):
        self.records = records or []
        self.error = error
        self.queries: list[str] = []

    def search(self, query):
        self.queries.append(query)
        if self.error is not None:
            raise self.error
        return list(self.records)

    def fetch_detail(self, _url):
        if self.error is not None:
            raise self.error
        return self.records[0] if self.records else None

    def normalize(self, record):
        return record


def _factory(**sources):
    """Official adapters default to "not configured", like production."""

    def build(name):
        if name in sources:
            return sources[name]
        return Source(error=SourceNotConfigured(f"{name} not configured", source=name))

    return build


def _record(code, name, status="现行", source="csres"):
    return SourceRecord(source_name=source, code=code, name=name, source_status=status)


@pytest.fixture
def live(monkeypatch):
    monkeypatch.setenv("ENABLE_LIVE_STANDARD_REFRESH", "true")
    monkeypatch.setenv("STANDARDS_DATASET", "v2")
    monkeypatch.setenv("LIVE_LOOKUP_RETRY_HOURS", "24")
    monkeypatch.setenv("LIVE_LOOKUP_FAILURE_RETRY_MINUTES", "30")


# --- P0: a source failure is not "no such standard" -------------------------


@pytest.mark.parametrize(
    "error",
    [
        SourceUnavailable("verification page", source="csres"),
        RateLimited("rate limited", source="csres"),
    ],
)
def test_source_failure_is_reported_separately_from_a_miss(error):
    trace = LookupTrace()
    result = discover_live(code="GB 55033-2022", name=None, factory=_factory(csres=Source(error=error)), trace=trace)
    assert result is None
    assert trace.failures == [f"csres:{error.category}"]
    assert attempt_outcome(result, None, trace) == "source_unavailable"


def test_unconfigured_adapters_and_empty_results_are_a_real_miss():
    trace = LookupTrace()
    result = discover_live(code="GB 59999-2020", name=None, factory=_factory(csres=Source(records=[])), trace=trace)
    assert result is None and trace.failures == []
    assert attempt_outcome(result, None, trace) == "miss"


def test_missing_detail_page_is_not_a_source_failure():
    trace = LookupTrace()
    standard = _v2("GB 50016-2014", "建筑设计防火规范")
    verify_live(
        standard,
        source_urls={"csres": "http://www.csres.com/detail/1.html"},
        factory=_factory(csres=Source(error=NotFound("gone", source="csres"))),
        trace=trace,
    )
    assert trace.failures == []


def test_failed_lookup_is_held_back_briefly_but_a_miss_for_a_day():
    db = _db()
    now = utc_now()
    record_attempt(db, "code:A", "source_unavailable", now=now)
    record_attempt(db, "code:B", "budget_exhausted", now=now)
    record_attempt(db, "code:C", "miss", now=now)
    assert recent_attempt(db, "code:A", now=now + timedelta(minutes=29)) == "source_unavailable"
    assert recent_attempt(db, "code:A", now=now + timedelta(minutes=31)) is None
    assert recent_attempt(db, "code:B", now=now + timedelta(minutes=31)) is None
    assert recent_attempt(db, "code:C", now=now + timedelta(hours=23)) == "miss"


def test_cleanup_keeps_rows_any_window_still_needs(monkeypatch):
    monkeypatch.setenv("LIVE_LOOKUP_RETRY_HOURS", "0.1")  # 6 minutes
    monkeypatch.setenv("LIVE_LOOKUP_FAILURE_RETRY_MINUTES", "30")
    db = _db()
    now = utc_now()
    record_attempt(db, "code:FAIL", "source_unavailable", now=now - timedelta(minutes=20))
    record_attempt(db, "code:NEW", "miss", now=now)
    assert db.query(LiveLookupAttemptModel).filter_by(lookup_key="code:FAIL").count() == 1


def test_verify_reports_source_unavailable_and_retries_after_short_window(monkeypatch, live):
    db = _db()
    db.add(_v2("GB 50016-2014", "建筑设计防火规范"))
    db.commit()
    csres = Source(error=SourceUnavailable("您无权访问", source="csres"))
    monkeypatch.setattr(
        endpoints, "discover_live",
        lambda **kwargs: discover_live(factory=_factory(csres=csres), **kwargs),
    )
    request = VerifyRequest(code="GB 55033-2022")

    first = endpoints.verify_standard(request, db)
    second = endpoints.verify_standard(request, db)

    assert first.match_type == second.match_type == "source_unavailable"
    assert first.status == StandardStatus.UNKNOWN
    assert len(csres.queries) == 1  # held back inside the short window
    attempt = db.query(LiveLookupAttemptModel).one()
    assert attempt.outcome == "source_unavailable"
    attempt.attempted_at = utc_now() - timedelta(minutes=31)
    db.commit()
    endpoints.verify_standard(request, db)
    assert len(csres.queries) == 2


# --- P1: year-less codes ------------------------------------------------------


def test_year_less_code_resolves_a_unique_series_member(live, monkeypatch):
    monkeypatch.setenv("ENABLE_LIVE_STANDARD_REFRESH", "false")
    db = _db()
    db.add(_v2("GB 55015-2021", "建筑节能与可再生能源利用通用规范"))
    db.commit()
    assert StandardV2Repo.get_by_code(db, "GB 55015").normalized_code == "GB 55015-2021"
    response = endpoints.verify_standard(VerifyRequest(code="GB 55015"), db)
    assert response.match_type == "code_incomplete"
    assert response.status == StandardStatus.CURRENT
    assert response.recommended_citation == "《建筑节能与可再生能源利用通用规范》GB 55015-2021"


def test_year_less_code_with_several_versions_is_ambiguous(live, monkeypatch):
    db = _db()
    db.add_all([
        _v2("GB 50016-2006", "建筑设计防火规范", status="abolished"),
        _v2("GB 50016-2014", "建筑设计防火规范"),
    ])
    db.commit()
    monkeypatch.setattr(endpoints, "discover_live", lambda **_kwargs: pytest.fail("no live lookup expected"))
    assert StandardV2Repo.get_by_code(db, "GB 50016") is None
    response = endpoints.verify_standard(VerifyRequest(code="GB 50016"), db)
    assert response.match_type == "ambiguous"
    assert response.status == StandardStatus.UNKNOWN
    assert [item.code for item in response.candidates] == ["GB 50016-2014", "GB 50016-2006"]
    assert "GB 50016-2014（现行）" in response.message


def test_name_picks_one_member_of_an_ambiguous_series(live, monkeypatch):
    monkeypatch.setenv("ENABLE_LIVE_STANDARD_REFRESH", "false")
    db = _db()
    db.add_all([
        _v2("GB 50010-2002", "混凝土结构设计规范", status="abolished"),
        _v2("GB/T 50010-2010", "混凝土结构设计标准", standard_prefix="GB/T", base_code="GB/T 50010-2010"),
    ])
    db.commit()
    response = endpoints.verify_standard(VerifyRequest(code="GB 50010", name="混凝土结构设计标准"), db)
    assert response.canonical_code == "GB/T 50010-2010"
    assert response.match_type == "code_incomplete"


def test_year_less_live_discovery_accepts_only_a_unique_series_member():
    unique = discover_live(
        code="GB 55033", name=None,
        factory=_factory(csres=Source(records=[_record("GB 55033-2022", "城市轨道交通工程项目规范")])),
    )
    assert unique.records[0].normalized_code == "GB 55033-2022"
    several = discover_live(
        code="GB 50016", name=None,
        factory=_factory(csres=Source(records=[
            _record("GB 50016-2006", "建筑设计防火规范", "废止"),
            _record("GB 50016-2014", "建筑设计防火规范"),
        ])),
    )
    assert several is None


def test_several_versions_at_the_source_are_ambiguous_not_missing(live, monkeypatch):
    db = _db()
    db.add(_v2("GB 50016-2014", "建筑设计防火规范"))
    db.commit()
    csres = Source(records=[
        _record("TB 10001-2005", "铁路路基设计规范", "废止"),
        _record("TB 10001-2016", "铁路路基设计规范"),
    ])
    monkeypatch.setattr(
        endpoints, "discover_live",
        lambda **kwargs: discover_live(factory=_factory(csres=csres), **kwargs),
    )
    response = endpoints.verify_standard(VerifyRequest(code="TB 10001"), db)
    assert response.match_type == "ambiguous"
    assert response.status == StandardStatus.UNKNOWN
    assert "TB 10001-2005" in response.message and "TB 10001-2016" in response.message
    assert db.query(LiveLookupAttemptModel).one().outcome == "ambiguous"
    assert endpoints.verify_standard(VerifyRequest(code="TB 10001"), db).match_type == "ambiguous"
    assert len(csres.queries) == 1


def test_year_less_code_on_an_inactive_version_is_unconfirmed(live, monkeypatch):
    monkeypatch.setenv("ENABLE_LIVE_STANDARD_REFRESH", "false")
    db = _db()
    db.add(_v2("CECS 53-1993", "某技术规程", status="abolished"))
    db.commit()
    response = endpoints.verify_standard(VerifyRequest(code="CECS 53"), db)
    assert response.match_type == "version_unconfirmed"
    assert response.status == StandardStatus.UNKNOWN


# --- P1: name-only hits must not claim an old version's status ----------------


def test_name_only_hit_on_old_version_is_not_reported_as_abolished(live, monkeypatch):
    monkeypatch.setenv("ENABLE_LIVE_STANDARD_REFRESH", "false")
    db = _db()
    db.add(_v2("GB/T 14684-2001", "建筑用砂", status="abolished", standard_prefix="GB/T", base_code="GB/T 14684-2001"))
    db.commit()
    name_only = endpoints.verify_standard(VerifyRequest(code="", name="建筑用砂"), db)
    assert name_only.match_type == "version_unconfirmed"
    assert name_only.status == StandardStatus.UNKNOWN
    with_code = endpoints.verify_standard(VerifyRequest(code="GB/T 14684-2011", name="建筑用砂"), db)
    assert with_code.match_type == "code_mismatch"
    assert with_code.status == StandardStatus.UNKNOWN
    assert with_code.result.status == StandardStatus.ABOLISHED  # the record itself is unchanged


def test_name_only_hit_with_known_successor_still_reports_replacement(live, monkeypatch):
    monkeypatch.setenv("ENABLE_LIVE_STANDARD_REFRESH", "false")
    db = _db()
    old = _v2("GB 50045-1995", "高层民用建筑设计防火规范", status="abolished")
    new = _v2("GB 50016-2014", "建筑设计防火规范")
    db.add_all([old, new])
    db.flush()
    db.add(StandardV2RelationModel(source_standard_id=old.id, target_standard_id=new.id, relation_type="replaced_by"))
    db.commit()
    response = endpoints.verify_standard(VerifyRequest(code="", name="高层民用建筑设计防火规范"), db)
    assert response.match_type == "obsolete"
    assert response.replaced_by == "GB 50016-2014"


def test_name_only_with_several_different_standards_is_ambiguous(live, monkeypatch):
    monkeypatch.setenv("ENABLE_LIVE_STANDARD_REFRESH", "false")
    db = _db()
    db.add_all([
        _v2("CECS 53-1993", "某技术规程", status="abolished"),
        _v2("CECS 53-2020", "某技术规程"),
    ])
    db.commit()
    response = endpoints.verify_standard(VerifyRequest(code="", name="某技术规程"), db)
    assert response.match_type == "ambiguous"
    assert len(response.candidates) == 2


# --- code first, name only as a fallback ---------------------------------------


def _old_sand_db():
    db = _db()
    db.add(_v2("GB/T 14684-2001", "建筑用砂", status="abolished", standard_prefix="GB/T", base_code="GB/T 14684-2001"))
    db.commit()
    return db


def test_cited_code_is_looked_up_before_using_a_name_hit_on_another_version(live, monkeypatch):
    db = _old_sand_db()
    csres = Source(records=[_record("GB/T 14684-2011", "建设用砂", "废止")])
    monkeypatch.setattr(
        endpoints, "discover_live",
        lambda **kwargs: discover_live(factory=_factory(csres=csres), **kwargs),
    )
    response = endpoints.verify_standard(VerifyRequest(code="GB/T 14684-2011", name="建筑用砂"), db)
    assert response.canonical_code == "GB/T 14684-2011"
    assert csres.queries[0] == "GB/T 14684-2011"


def test_name_hit_is_still_reported_when_the_cited_code_is_not_found(live, monkeypatch):
    db = _old_sand_db()
    monkeypatch.setattr(
        endpoints, "discover_live",
        lambda **kwargs: discover_live(factory=_factory(csres=Source(records=[])), **kwargs),
    )
    response = endpoints.verify_standard(VerifyRequest(code="GB/T 14684-2011", name="建筑用砂"), db)
    assert response.match_type == "code_mismatch"
    assert response.status == StandardStatus.UNKNOWN
    assert response.canonical_code == "GB/T 14684-2001"


def test_name_fallback_notes_when_sources_could_not_check_the_code(live, monkeypatch):
    db = _old_sand_db()
    csres = Source(error=SourceUnavailable("您无权访问", source="csres"))
    monkeypatch.setattr(
        endpoints, "discover_live",
        lambda **kwargs: discover_live(factory=_factory(csres=csres), **kwargs),
    )
    response = endpoints.verify_standard(VerifyRequest(code="GB/T 14684-2011", name="建筑用砂"), db)
    assert response.match_type == "code_mismatch"
    assert "来源暂不可用" in response.message
